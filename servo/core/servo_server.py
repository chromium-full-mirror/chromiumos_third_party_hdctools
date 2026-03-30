# Copyright 2012 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Servo Server."""

import collections
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

from servo.common import servo_dev_templates
from servo.common import sversion_util
from servo.common.exceptions import HwDriverError
from servo.common.utils import json_utils
from servo.common.utils import servo_logging
from servo.core import recovery
from servo.utils import diagnose
from servo.utils import scratch
from servo.utils import usb_hierarchy


class ServodError(Exception):
    """Exception class for servod."""


class Servod:
    """Main class for Servo debug/controller Daemon."""

    # Separator for control strings between servo device prefix and control name
    PREFIX_DELIMITER = "."
    # Constant for flex Control
    _IS_FLEX_CTRL = "is_flex_board"
    # Message header from gRPC
    GRPC_EXC_MSG = "Exception calling application: "

    # Exceptions that are expected during normal operation and should not be
    # treated as internal bugs.
    KNOWN_EXCEPTIONS = (AttributeError, NameError, HwDriverError)

    def __init__(self, usbkm232: Optional[str] = None) -> None:
        """Servod constructor.

        Args:
          usbkm232: String. Optional. Path to USB-KM232 device which allow for
              sending keyboard commands to DUTs that do not have built in
              keyboards. Used in FAFT tests. Use None for on board AVR MCU.
              e.g. '/dev/ttyUSB0' or None.

        Raises:
          ServodError: if unable to locate init method for particular interface
        """
        self._logger = logging.getLogger("Servod")
        self._usbkm232 = usbkm232
        self._keyboard = None
        self._usb_keyboard = None
        # A map of device serialname strings keyed by the device's name/prefix.
        self._serialnames: Dict[str, Optional[str]] = collections.defaultdict(
            lambda: None
        )
        # A map of ServoDevices keyed by their name/prefix.
        # A ServoDevice can have multiple name/prefix (e.g. 'main', '')
        self._devices: Dict[str, Any] = collections.defaultdict(lambda: None)
        # A map of ServoDevices keyed by their id (vid, pid, serial)
        # Each ServoDevice has a unique id
        self._unique_devices: Dict[Tuple[int, int, str], Any] = collections.defaultdict(
            lambda: None
        )
        # All known controls of this servod instance
        self._controls: List[str] = []
        # Store state for select_control drivers
        self.selected_controls: Dict[str, Any] = {}
        self._watchdog_thread = None

    def set_watchdog(self, watchdog):
        """Set the watchdog thread."""
        self._watchdog_thread = watchdog

    def clear(self):
        """Clear all devices and serialnames."""
        self._devices.clear()
        self._unique_devices.clear()
        self._serialnames.clear()
        self._controls = []

    def add_device(self, device: Any, prefix: str) -> None:
        """Add a ServoDevice to Servod.

        Args:
          device: a ServoDevice that can interact with Servod, dut, and other
                  ServoDevices
          prefix: prefix of the ServoDevice recognized by Servod
        """
        self._logger.debug("Adding ServoDevice %s to instance.", device)
        if prefix in self._devices:
            if device.get_id() != self._devices[prefix].get_id():
                raise ServodError(
                    (
                        "ServoDevice prefix %s already represents device %s and "
                        "cannot be added as %s."
                    )
                    % (prefix, self._devices[prefix], device)
                )
            self._logger.debug(
                "ServoDevice prefix %s is already added as %s.",
                prefix,
                self._devices[prefix],
            )
            # Update the device object in case it has changed (e.g. during retry)
            self._devices[prefix] = device
            self._unique_devices[device.get_id()] = device
            return

        self._unique_devices[device.get_id()] = device
        self._devices[prefix] = device
        self.add_serial_number(prefix, device._serial)
        # ensure the device records all its alias prefixes
        device.add_prefix(prefix)
        if prefix == servo_dev_templates.MAIN_DEV_PREFIX:
            # This is the main device as the prefix is empty. Add prefix alias here
            # for the main device.
            self._devices[servo_dev_templates.MAIN_DEV_PREFIX_ALIAS] = device
            self.add_serial_number(
                servo_dev_templates.MAIN_DEV_PREFIX_ALIAS, device._serial
            )

    def reinitialize(self):
        """Reinitialize all devices that support reinitialization"""
        for device in self.get_devices():
            try:
                device.reinitialize()
            except usb_hierarchy.HierarchyError as e:
                if not device.disconnect_is_ok():
                    raise
                self._logger.info(
                    "Ignoring failed re-initialization of device that "
                    "is ok to be disconnected. %s error(%s).",
                    device,
                    e,
                )

    def close(self):
        """Servod turn down logic."""
        for dev in self.get_devices():
            dev.close()

    def get_devices(self) -> List[Any]:
        """Get all devices connected to this servod instance."""
        return list(self._unique_devices.values())

    @staticmethod
    def _get_control_prefix_and_name(name):
        """Return (prefix, name) tuple from name passed into servod.

        Args:
          name: name passed into any of the RPCs

        Returns:
          (prefix, name) tuple, where
            prefix is anything before the '.'
            name anything after it
            If there is no '.' in |name| return ('', name)
        Raises:
          ServodError: if there are more than one PREFIX_DELIMITER in |name|922gg
        """
        if Servod.PREFIX_DELIMITER not in name:
            return ("", name)
        parts = name.split(Servod.PREFIX_DELIMITER)
        if len(parts) > 2:
            # Returned early if no |PREFIX_DELIMITER| in name, therefore after the
            # split there have to be at least 2 parts here.
            raise ServodError(
                "Name %r is malformed: at most one %r is allowed."
                % (name, Servod.PREFIX_DELIMITER)
            )
        return tuple(parts)

    def _is_main_dev_prefix(self, prefix):
        """Return whether |prefix| is the main device prefix.

        Args:
          prefix: prefix to query

        Returns:
          True, if the prefix has a main device prefix
        """
        return prefix in servo_dev_templates.MAIN_DEV_PREFIXES

    def _get_dev_and_name(self, name):
        """Return (dev, name) tuple after processing the name's prefix.

        Args:
          name: control name to get dev for

        Returns:
          (dev, name) tuple where
            dev is the ServoDevice instance to handle |name|
            name is the name after removing the prefix, if there was one
        Raises:
          ServodError: if no ServoDev can be found to handle |name|
          NameError: if |name| not a known control on its servo dev.
        """
        prefix, processed_name = Servod._get_control_prefix_and_name(name)
        if prefix not in self._devices:
            error_msg = (
                "No control named '%s' registered. "
                "No servo device registered for prefix %s."
            ) % (name, prefix)
            raise ServodError(error_msg)
        dev = self._devices[prefix]

        # Controls routed to main that are not covered by main are covered by their
        # root hub device.
        if not dev.is_control(processed_name):
            if self._is_main_dev_prefix(prefix) and self.get_root_device() is not None:
                dev = self.get_root_device()

        if not dev.is_control(processed_name):
            error_msg = (
                f"No control named '{name}' registered "
                f"with any connected servo device.\n"
                f"Servo device {dev} (prefix: {dev.get_prefixes()}) "
                f"is picked as the target device for the control.\n"
            )
            candidates = [ctrl for ctrl in self._controls if name in ctrl]
            if candidates:
                # Wrap candidates slightly or just print comma separated
                error_msg += f"Did you mean: {', '.join(candidates)}?\n"
            error_msg += (
                "You can check all servod controls with 'dut-control all_controls'."
            )
            raise ServodError(error_msg)

        # Watchdog controls query the device states. Don't wait for the device.
        if "watchdog" not in name:
            # Wait until the device is connected. CCD is the only device that's ok
            # to disconnect. This will wait for CCD devices to reconnect before
            # trying to get/set the control.
            dev.wait()
        self._logger.debug(
            "Using servo device %s for control %s (device %sconnected)",
            dev,
            name,
            "" if dev.is_connected() else "dis",
        )
        return (dev, processed_name)

    def hwinit(self, verbose=True, step_init=False):
        """Initialize controls for servo devices."""
        with scratch.ConcurrencyGuard(max_concurrency=3, name="hwinit"):
            for servo_device in self.get_devices():
                skip_controls = set()
                for dev in servo_device.get_child_devices():
                    skip_controls.update(
                        set(
                            control_name
                            for control_name, _unused in dev.get_hwinit_controls()
                        )
                    )
                servo_device.hwinit(
                    verbose=verbose, skip_controls=skip_controls, step_init=step_init
                )

            # Autotest directly uses this method, so we have to return True
            return True

    def get(self, name):
        """Get control value.

        Args:
          name: name string of control

        Returns:
          Response from calling drv get method.  Value is reformatted based on
          control's dictionary parameters

        Raises:
          HwDriverError: Error occurred while using drv
          ServodError: if interfaces are not available within timeout period
        """
        if name.endswith("_serialname"):
            # This route is to retrieve serialnames on servo v4, which
            # connects to multiple servo-micros or CCD, like the controls,
            # 'ccd_serialname', 'servo_micro_serialname', etc.
            with servo_logging.WrapGetCall(
                name, known_exceptions=self.KNOWN_EXCEPTIONS
            ) as wrapper:
                val = self.get_legacy_serial_number(name)
                wrapper.got_result(val)
                return val

        if name == "config_files":
            with servo_logging.WrapGetCall(
                name, known_exceptions=self.KNOWN_EXCEPTIONS
            ) as wrapper:
                val = json_utils.dumps(
                    self.get_config_files(), sort_keys=True, indent=4
                )
                wrapper.got_result(val)
                return val
        if name == "devices":
            with servo_logging.WrapGetCall(
                name, known_exceptions=self.KNOWN_EXCEPTIONS
            ) as wrapper:
                devices_json = []
                for device in self.get_devices():
                    devices_json.append(json.loads(device.to_json()))
                val = json_utils.dumps(devices_json, indent=4)
                wrapper.got_result(val)
                return val
        if name == "servo_type":
            with servo_logging.WrapGetCall(
                name, known_exceptions=self.KNOWN_EXCEPTIONS
            ) as wrapper:
                val = self._get_version()
                wrapper.got_result(val)
                return val
        if name == "servod_pid":
            with servo_logging.WrapGetCall(
                name, known_exceptions=self.KNOWN_EXCEPTIONS
            ) as wrapper:
                val = os.getpid()
                wrapper.got_result(val)
                return val
        if name == "serialname":
            with servo_logging.WrapGetCall(
                name, known_exceptions=self.KNOWN_EXCEPTIONS
            ) as wrapper:
                root_dev = self.get_root_device()
                if root_dev is not None:
                    val = root_dev._serial
                else:
                    val = self.get_main_device()._serial
                wrapper.got_result(val)
                return val
        if name == "serialnames":
            with servo_logging.WrapGetCall(
                name, known_exceptions=self.KNOWN_EXCEPTIONS
            ) as wrapper:
                val = json_utils.dumps(
                    self.get_servo_serials(), sort_keys=True, indent=4
                )
                wrapper.got_result(val)
                return val

        dev, name = self._get_dev_and_name(name)
        try:
            return dev.get(name)
        except Exception as e:
            if hasattr(e, "details"):
                msg = e.details()
                if msg.startswith(self.GRPC_EXC_MSG):
                    # pylint: disable=broad-exception-raised
                    raise Exception(msg[len(self.GRPC_EXC_MSG) :]) from e
            raise

    def get_legacy_serial_number(self, control_name):
        """Returns the desired serial number of a device.

        This is a method to support the legacy controls of <...>_serialname.
        Consider removing it if all clients move away from this pattern.

        Args:
          control_name: Name of the control.

        Returns:
           A string containing the serial number or "unknown".
        """
        # Remove the prefix from the serialname control. Serialnames are
        # universal. It doesn't matter what the prefix is.
        control_name = control_name.split(".", 1)[-1]

        suffix = "_serialname"
        dev_type = control_name[: -len(suffix)]
        board_model = ""
        main_dev = self.get_main_device()

        if not dev_type:
            return main_dev._serial

        if "_for_" in control_name:
            board_model = dev_type.split("_for_")[1]
            dev_type = dev_type.split("_for_")[0]

        candidates = set()
        for _unused, dev in self._unique_devices.items():
            if dev_type not in dev.template.TYPE:
                continue
            if not board_model:
                candidates.add(dev)
            elif board_model in [dev.board, dev.model, main_dev.board, main_dev.model]:
                candidates.add(dev)

        if len(candidates) == 0:
            self._logger.info("'%s' not found!", control_name)
            return "unknown"
        if len(candidates) == 1:
            return candidates.pop()._serial
        self._logger.info(
            "'%s' is ambiguous as there are multiple matching devices %s",
            control_name,
            candidates,
        )
        return "unknown"

    def set(self, name, wr_val_str):
        """Set control on servo device.

        Args:
          name: name string of control
          wr_val_str: value string to write.  Can be integer, float or a
              alpha-numerical that is mapped to a integer or float.

        Returns:
          True, coming from the device's set call, to appease xmlrpc

        Raises:
          HwDriverError: Error occurred while using driver
          ServodError: if interfaces are not available within timeout period
        """
        dev, name = self._get_dev_and_name(name)
        try:
            return dev.set(name, wr_val_str)
        except Exception as e:
            if hasattr(e, "details"):
                msg = e.details()
                if msg.startswith(self.GRPC_EXC_MSG):
                    # pylint: disable=broad-exception-raised
                    raise Exception(msg[len(self.GRPC_EXC_MSG) :]) from e
            raise

    def update_known_ctrls(self):
        """Helper to generate a list of all accessible controls in servod."""
        known_ctrls = set()
        for prefix, dev in self._devices.items():
            dev_ctrls = dev.get_all_controls()
            # controls for root and main dev does not need to have prefixes
            new_ctrls = (
                set("%s.%s" % (prefix, ctrl) for ctrl in dev_ctrls)
                if prefix
                else dev_ctrls
            )
            if prefix == servo_dev_templates.ROOT_DEV_PREFIX:
                new_ctrls |= dev_ctrls
            known_ctrls |= new_ctrls
        self._controls = sorted(list(known_ctrls))

    def has_control(self, control):
        """Returns True if control is available in servod."""
        return control in self._controls

    def doc_all(self):
        """Return all documentation for controls.

        Returns:
          string of <doc> text in config file (xml) and the params dictionary for
          all controls.

          For example:
          warm_reset             :: Reset the device warmly
          ------------------------> {'interface': '1', 'map': 'onoff_i', ... }
        """
        self.update_known_ctrls()
        rsp = []
        for name in self._controls:
            dev, control = self._get_dev_and_name(name)
            rsp.append(dev.get_control_str(control))
        self._logger.debug("rsp %s", rsp)
        return "\n".join(rsp)

    def doc(self, name):
        """Retrieve doc string in system config file for given control name.

        Args:
          name: name string of control to get doc string

        Returns:
          doc string of name

        Raises:
          NameError: if fails to locate control
        """
        with servo_logging.WrapGetCall(
            name, known_exceptions=self.KNOWN_EXCEPTIONS
        ) as wrapper:
            dev, control = self._get_dev_and_name(name)
            val = dev.doc(control)
            wrapper.got_result(val)
            return val

    def set_get_all(self, cmds):
        """Set &| get one or more control values.

        Args:
          cmds: list of control[:value] to get or set.

        Returns:
          rv: list of responses from calling get or set methods.
        """
        rv = []
        for cmd in cmds:
            if ":" in cmd:
                (control, value) = cmd.split(":", 1)
                rv.append(self.set(control, value))
            else:
                rv.append(self.get(cmd))
        return rv

    def get_all(self, verbose):
        """Get all controls values.

        Args:
          verbose: Boolean on whether to return doc info as well

        Returns:
          string creating from trying to get all values of all controls.  In case of
          error attempting access to control, response is 'ERR'.
        """
        self.update_known_ctrls()
        rsp = []
        for name in self._controls:
            # avoid repeating the controls starting with 'main.' and 'root.'
            if name.startswith(
                "%s." % servo_dev_templates.MAIN_DEV_PREFIX
            ) or name.startswith("%s." % servo_dev_templates.ROOT_DEV_PREFIX):
                continue
            self._logger.debug("name = %s", name)
            try:
                value = self.get(name)
            except Exception:
                value = "ERR"
            if verbose:
                rsp.append("GET %s = %s :: %s" % (name, value, self.doc(name)))
            else:
                rsp.append("%s:%s" % (name, value))
        return "\n".join(sorted(rsp))

    def echo(self, echo):
        """Mock echo function for testing/examples.

        Args:
          echo: string to echo back to client
        """
        self._logger.debug("echo(%s)", echo)
        return "ECH0ING: %s" % (echo)

    def get_board(self):
        """Returns the board specified for the main device.

        Returns:
          A string of the board name, or '' if not present.
        """
        return self.get_main_device().board

    def get_base_board(self):
        """Returns the board probed from EC in case the main device is a dut controller.

        Returns:
          A string of the board name, or '' if not present.
        """
        return self.get_main_device().base_board

    def get_servo_serials(self):
        """Return all the serials associated with this process.

        This gets passed directly to the xml rpc response to xmlrpc client request
        get_servo_serials(). It needs to be in a basic type for Python to
        correctly marshal.  See b/279006079

        Returns:
          {str: str} - Dict of control prefix mapped to servo serial number.
          Multiple prefixes may be mapped to the same serial number.

        Each call to this function returns a new dict.  The returned dict may be
        mutated without affecting any other state.
        """
        return dict(self._serialnames)

    def add_serial_number(self, key, serial_number):
        """Adds the serial number to the _serialnames dictionary.

        Args:
          key: A string which is the key into the _serialnames dictionary.
          serial_number: A string which is the key into the _serialnames dictionary.
        """
        self._serialnames[key] = serial_number
        self._logger.debug("Added %s %s to serialnames.", key, serial_number)

    def get_main_device(self):
        """Gets the main servo device."""
        return self._devices[servo_dev_templates.MAIN_DEV_PREFIX]

    def get_root_device(self):
        """Gets the root servo device."""
        if servo_dev_templates.ROOT_DEV_PREFIX not in self._devices:
            return None
        return self._devices[servo_dev_templates.ROOT_DEV_PREFIX]

    def get_controls_for_tag(self, tag):
        """Get list of controls for a given tag.

        Args:
          tag: str, tag to query

        Returns:
          list of controls with that tag, or an empty list if no such tag, or
          controls under that tag
        """
        controls = set()
        no_prefix_devs = [self.get_main_device(), self.get_root_device()]
        for prefix, dev in self._devices.items():
            # controls for root and main dev does not need to have prefixes
            no_prefix = dev in no_prefix_devs
            for dev_ctrl in dev.get_controls_for_tag(tag):
                controls.add(dev_ctrl if no_prefix else "%s.%s" % (prefix, dev_ctrl))
        return sorted(list(controls))

    def get_config_files(self):
        """Gets the configuration files used for this servo server invocation"""
        config_files = {}
        for prefix, dev in self._devices.items():
            xml_files = dev.get_config_files()
            config_files[prefix] = list(xml_files)
        return config_files

    def get_interface_list(self):
        interfaces = []
        for dev in self.get_devices():
            for interface in dev.get_interface_list():
                interfaces += [(str(dev), interface)]
        return interfaces

    def is_flex_board(self):
        """Returns true if servod is run with a flex board"""
        if not self.has_control(self._IS_FLEX_CTRL):
            return False
        is_flex_board = self.get(self._IS_FLEX_CTRL)
        if is_flex_board == "no":
            return False
        if is_flex_board == "yes":
            return True
        raise ServodError(
            "Control %r has invalid value %r." % (self._IS_FLEX_CTRL, is_flex_board)
        )

    def validate_dut_controller(self):
        """Validate the servod instance has at least 1 dut controller."""
        for dev in self.get_devices():
            if dev.template.DUT_CONTROLLER:
                return

        if self.is_flex_board():
            self._logger.info("Flex board doesn't use DUT controller, skip check.")
            return

        # Start diagnosing why servod does not have DUT controller.
        # Fail if we requested board control but don't have an interface for this.
        if self.get_board():
            if self.get("dut_connection_type") == "type-c":
                faults = diagnose.diagnose_ccd(self.get_main_device())
                if diagnose.SBU_VOLTAGE_FLOAT in faults:
                    self.set("dut_sbu_voltage_float_fault", "on")
            # No need to check for the LOW voltage signal here as the fault
            # is valid for both ccd and for servo micro: a controller is missing
            self.set("dut_controller_missing_fault", "on")

            board_name = self.get_board()
            model_name = getattr(self.get_main_device(), "model", None)
            if model_name and board_name.endswith("_" + model_name):
                board_name = board_name[: -len(model_name) - 1]
                description = "board %s model %s" % (board_name, model_name)
            else:
                description = "board %s" % board_name

            self._logger.error(
                "No Servo Micro, C2D2, or CCD detected for %s", description
            )
            self._logger.error(
                "Try flipping the USB type C cable if you were using "
                "servo v4 type C."
            )
            self._logger.error(
                "If flipping the cable allows CCD, please file a bug "
                "against the DUT platform with reproducing details."
            )

            dut_controller_tolerant = recovery.is_recovery_active()
            if dut_controller_tolerant:
                self._logger.info(
                    "Will continue startup as recovery mode has been requested"
                )
            else:
                self._logger.fatal(
                    "No device interface (Servo Micro, C2D2, or CCD) connected."
                )
                sys.exit(-1)

    def get_version(self):
        """Gets the type of the servo device setups.

        DEPRECATED. External clients (e.g. autotest) should not directly call this
        method of servo_server as it is an implementation detail. They should migrate
        to using 'servo_type' control.

        TODO(konmari): remove this public method after all clients move away from
        directly calling methods.
        """
        return self._get_version()

    def _get_version(self):
        """Gets the type of the servo device setups.

        NOTE: please avoid assuming the format of servo type string and parsing it.
        Use 'devices' control to fetch all servo devices of this servod instance
        instead.
        """
        main_device = self.get_main_device()
        root_device = self.get_root_device()
        type_ = main_device.template.TYPE
        if root_device and root_device is not main_device:
            type_ = root_device.template.TYPE + "_with_" + type_
            for dev in root_device.get_child_devices():
                if dev.template.DUT_CONTROLLER and dev != main_device:
                    type_ += "_and_" + dev.template.TYPE
        return type_

    def servod_version(self):
        return sversion_util.extended_version()
