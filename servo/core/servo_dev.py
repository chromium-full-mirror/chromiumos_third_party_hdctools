# Copyright 2019 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Servod device used by the server and watchdog."""

import json
import logging
import sys
import termios
import threading
import time
import tty
from typing import Any, Dict, List, Optional, Tuple

from google.protobuf import empty_pb2
import grpc

from servo.common import servo_dev_templates
from servo.common.exceptions import HwDriverError
from servo.common.grpc_client import GrpcClient
from servo.common.proto import driver_grpc  # type: ignore
from servo.common.proto import system_config_grpc  # type: ignore
from servo.common.utils import json_utils
from servo.common.utils import servo_logging
import servo.utils.usb_hierarchy as usb_hierarchy


def _yes_no_input(message):
    """Prompt for y/n character input.

    The y/n question will be repeated after any character input that is not
    y/Y/n/N, until one of those characters is received.

    Args:
        message: str or bytes - The prompt message to print, usually with a
            trailing whitespace character.  "[y/n] " will be appended
            automatically.

    Returns: bool - True if user typed  y or Y, False if they typed  n or N.
    """
    sys.stdout.write(message)
    while True:
        stdin_fd = sys.stdin.fileno()
        stdin_termios = termios.tcgetattr(stdin_fd)
        try:
            # If stdin is a terminal (which it should be when this function is
            # used) it is almost certainly line buffered. Temporarily set it to
            # the "raw" mode termios settings so any character the user types is
            # sent immediately.
            #
            # This way we can respond to Y and N keys without making the user
            # type Y/N + Enter for each prompt.
            #
            tty.setraw(stdin_fd)
            sys.stdout.write("[y/n] ")
            sys.stdout.flush()
            onechar = sys.stdin.read(1).lower()
            if onechar and onechar.isprintable():
                sys.stdout.write(onechar)
                sys.stdout.write("\n")
                sys.stdout.flush()
                if onechar in ("y", "Y"):
                    return True
                if onechar in ("n", "N"):
                    return False
        finally:
            termios.tcsetattr(stdin_fd, termios.TCSADRAIN, stdin_termios)
        if not (onechar and onechar.isprintable()):
            # Make sure that if the user is mashing ctrl+c or ctrl+\ it gets
            # through before the next loop iteration.
            time.sleep(0.5)


class ServoDeviceError(Exception):
    """General servo device error class."""


class ServoDevice:
    """Device class that each corresponds to a physical servo device."""

    # Reinit capable devices.
    REINIT_CAPABLE = {
        servo_dev_templates.get_id("ccd_cr50"),
        servo_dev_templates.get_id("ccd_gsc"),
        servo_dev_templates.get_id("ccd_gsc_nt"),
    }

    # Available attempts to reconnect a device
    REINIT_ATTEMPTS = 200

    # Exceptions to count as known or ordinary.  Any errors that aren't instances
    # of these (or their subclasses) will be logged with "Please take a look."
    KNOWN_EXCEPTIONS = (AttributeError, NameError, HwDriverError)

    # Timeout to wait for interfaces to become available again if reinitialization
    # is taking place. In seconds. This is supposed to recover from brief resets.
    # If the interface disappears for more than 5 seconds, then someone probably
    # intentionally disconnected the device. Servod shouldn't be responsible for
    # waiting for the device during an intentional disconnect.
    INTERFACE_AVAILABILITY_TIMEOUT = 5

    def __init__(
        self,
        dev_entry: Any,
        grpc_data_addr: Tuple[str, int],
        interfaces: Optional[List[str]] = None,
        servod: Optional[Any] = None,
    ) -> None:
        """ServoDevice constructor.

        Args:
          dev_entry: ServoDeviceEntry that holds USB, device hierarchy, and devopts
                     information for this servo device.
          grpc_data_addr: tuple of host and port of data grpc service
          interfaces: list of strings of interface types the server will instantiate
          servod: a pointer to access servod to invoke controls targeted at the servod
                  daemon and other devices.

        Raises:
          ServoDeviceError: if unable to locate init method for particular interface
        """
        self.template = dev_entry.dev_template
        self.prefixes = dev_entry.devopts.prefix
        logger_prefix = self.prefixes[-1] if self.prefixes else ""
        self._logger = logging.getLogger(
            "ServoDevice %s - %s" % (self.template.TYPE, logger_prefix)
        )
        vendor = self.template.VID
        product = self.template.PID
        self._serial = dev_entry.serial
        board = dev_entry.devopts.board
        self.board = board
        self.base_board = ""
        self.model = dev_entry.devopts.model
        if self.model:
            self.board += "_" + self.model
        self._ifaces_available = threading.Event()
        self.connect()
        self._reinit_capable = (vendor, product) in self.REINIT_CAPABLE
        self._disconnect_ok = False
        self._sysfs_path = dev_entry.dev_path
        # Associate the dev entry with a device
        self.dev_entry = dev_entry
        dev_entry.servo_device = self

        # Dict of Dict to map control name, function name to to tuple (params, drv)
        # Ex) _drv_dict[name]['get'] = (params, drv)
        self._drv_dict: Dict[str, Dict[str, Tuple[Any, Any]]] = {}

        # Create a gRPC channel to the specified host and port
        grpc_data_host, grpc_data_port = grpc_data_addr
        channel = GrpcClient.create_grpc_channel(grpc_data_host, grpc_data_port)
        self._logger.debug("Connect to grpc server of data.....")
        self._driver_client = driver_grpc.DriverService(channel)
        self._system_config_client = system_config_grpc.SystemConfig(channel)

        if interfaces:
            self._manual_interfaces = True
            self._interfaces = interfaces
        else:
            self._manual_interfaces = False
            self._interfaces = self.get_servo_interfaces(
                self.template.VID, self.template.PID, ""
            )

        # list of objects (Fi2c, Fgpio) to physical interfaces (gpio, i2c) that ftdi
        # interfaces are mapped to
        self._interface_list: List[Any] = []
        # Whether an interface has initialized to be the proper interface
        self._interface_init: List[Any] = []
        self._servod = servod
        self._token_db = dev_entry.devopts.token_db

    def __repr__(self):
        return str(self)

    def __str__(self):
        return "%s (%04x:%04x) %s" % (
            self.template.TYPE,
            self.template.VID,
            self.template.PID,
            self._serial,
        )

    def wait(self, wait_time=INTERFACE_AVAILABILITY_TIMEOUT):
        """Wait for the device to reconnect and the interfaces to become available.

        Args:
            wait_time: time to wait in seconds

        Raises:
          ServoDeviceError: if the interfaces aren't available within timeout period
        """
        if not self._ifaces_available.wait(wait_time):
            raise ServoDeviceError(
                "Timed out waiting for interfaces to become available."
            )

    def connect(self) -> None:
        """The device connected."""
        # Mark that the interfaces are available.
        self._ifaces_available.set()
        self._reinit_attempts = self.REINIT_ATTEMPTS

    def disconnect(self):
        """The device disconnected."""
        # Mark that the interfaces are unavailable.
        self._ifaces_available.clear()

        # If it's ok for the device to disconnect, allow it to stay disconnected
        # indefinitely.
        if self._disconnect_ok:
            return

        self._reinit_attempts -= 1
        self._logger.debug("%d reinit attempts remaining.", self._reinit_attempts)

    def reinit_ok(self):
        """Check whether reinit is okay."""
        return self._reinit_capable and (self._reinit_attempts > 0)

    def get_id(self):
        """Return a tuple of the device information."""
        return self.template.VID, self.template.PID, self._serial

    def is_connected(self):
        """Returns True if the device is connected."""
        try:
            return self._driver_client.CheckDevice(sysfs_path=self._sysfs_path).value
        except grpc.RpcError:
            self._logger.debug(
                "Failed to ping data service for connection state. "
                "Assuming disconnected."
            )
            return False

    def get_prefixes(self):
        """Get all prefixes of the device."""
        return self.prefixes

    def add_prefix(self, alias):
        """Add a prefix for the device."""
        if alias not in self.prefixes:
            self.prefixes += [alias]

    def set_disconnect_ok(self, disconnect_ok):
        """Set if it's ok for the device to disconnect.

        Don't decrease the reinit_attempts count if this is True. The device can
        be disconnected forever as long as disconnect is ok.

        Args:
          disconnect_ok: True if it's ok for the device to disconnect.
        """
        self._disconnect_ok = disconnect_ok
        self._reinit_attempts = self.REINIT_ATTEMPTS

    def disconnect_is_ok(self):
        """Returns True if it's ok for the device to disconnect."""
        return self._disconnect_ok

    def usb_devnum(self):
        """Return the current usb devnum."""
        return usb_hierarchy.Hierarchy.dev_num_from_sysfs(self._sysfs_path)

    def get_interface_list(self):
        """Return interface_list."""
        return self._interface_list

    def init_servo_interfaces(self, fault_tolerant=False):
        """
        Init interfaces for servo device
        """
        response = self._driver_client.InitInterface(
            vid=self.template.VID,
            pid=self.template.PID,
            serial=self._serial,
            interface_template=json.dumps(self._interfaces),
            fault_tolerant=fault_tolerant,
            token_db=self._token_db,
        )
        for line in response.loglines:
            self._logger.info(line.strip())

        if not response.success and not fault_tolerant:
            error_hint = ""
            for line in response.loglines:
                if "Resource busy" in line:
                    error_hint = " Resource busy. Is another servod instance running?"
                    break
                if "No such device" in line:
                    error_hint = " No such device. Is the device still connected?"
                    break
                if (
                    "Access denied" in line
                    or "insufficient permissions" in line.lower()
                ):
                    error_hint = (
                        " Access denied. Do you have proper permissions (udev rules)?"
                    )
                    break
                if "run out of endpoints" in line:
                    error_hint = " Run out of USB endpoints. See crbug.com/652373."
                    break

            raise ServoDeviceError(
                "Failed to initialize interfaces for %s.%s "
                "Check the logs for details." % (self, error_hint)
            )

    def set_board_and_model(self, board, model=None):
        """Set the board and model (if applicable) for this servo device.

        (1) check if interfaces need to change due to board
        (2) set board/model attributes
        (3) pull in board/model config file

        Args:
          board: board name
          model: model name

        Returns:
          True if configuration file found for board/model False otherwise
        """
        if not self._manual_interfaces:
            # Only if interfaces were determined, and not set manually, try to
            # get new interfaces from the board, otherwise, leave them be.
            interfaces = self.get_servo_interfaces(
                self.template.VID, self.template.PID, board
            )
            if interfaces != self._interfaces:
                for i, interface_data in enumerate(interfaces):
                    if self._interfaces[i] != interface_data:
                        # If an interface is overwritten ensure that it's marked as not
                        # initialized regardless of previous status.
                        self._driver_client.ResetInterface(
                            vid=self.template.VID,
                            pid=self.template.PID,
                            serial=self._serial,
                            interface_index=i,
                        )
                    self._interfaces[i] = interface_data
                self._sync_interface_lists()

        response = self._system_config_client.GetBoardModelConfig(
            vid=self.template.VID,
            pid=self.template.PID,
            serial=self._serial,
            board=board,
            model=model if model else "",
        )
        cfg = response.board_config
        board_id = response.board_id

        # |board_id| might include the |model| or not depending on whether it was used
        # to determine the board config.
        self.board = board_id
        if model and board_id and board_id.endswith(model):
            self.model = model
        if cfg:
            try:
                # Load systemConfig using the gRPC server
                cfg_response = self._system_config_client.AddCfgFile(
                    prefix=self.prefixes[0],
                    filename=cfg,
                    vid=self.template.VID,
                    pid=self.template.PID,
                    serial=self._serial,
                )
                for line in cfg_response.loglines:
                    self._logger.info(line.strip())
            except grpc.RpcError as e:
                # Handle gRPC errors, such as network issues and exit system
                self._logger.error("gRPC error in: %s", e)
            return True
        return False

    def _sync_interface_lists(self):
        """Ensure when interfaces are changed, bookkeeping is kept in sync."""
        self._driver_client.SyncInterfaceList(
            vid=self.template.VID,
            pid=self.template.PID,
            serial=self._serial,
            interface_template=json.dumps(self._interfaces),
            fault_tolerant=False,
        )

    def set_base_board(self, board):
        """Set the board probed from ec.

        Args:
          board: the board probed from ec (assuming this device is a dut controller)
        """
        self.base_board = board

    def reinitialize(self):
        """Reinitialize all interfaces that support reinitialization"""
        self._driver_client.ReinitializeInterfaces(
            vid=self.template.VID, pid=self.template.PID, serial=self._serial
        )
        # Indicate interfaces are safe to use again.
        self.connect()

    def close(self):
        """Servo device turn down logic."""
        try:
            self._driver_client.CloseInterface(
                vid=self.template.VID,
                pid=self.template.PID,
                serial=self._serial,
                timeout=0.5,
            )
        except grpc.RpcError as e:
            self._logger.debug("Failed to close interface via grpc: %s", e)

    def get(self, name):
        """Get control value.

        Args:
          name: name string of control

        Returns:
          Response from calling drv get method.  Value is reformatted based on
          control's dictionary parameters

        Raises:
          HwDriverError: Error occurred while using drv
          ServoDeviceError: if interfaces are not available within timeout period
        """
        with servo_logging.WrapGetCall(
            name, known_exceptions=self.KNOWN_EXCEPTIONS
        ) as wrapper:
            drv = self._get_param_drv(name)
            params = json.loads(drv.value)
            rd_val = params["response"]
            wrapper.got_result(rd_val)
            return rd_val

    def set(self, name, wr_val_str):
        """Set control.

        Args:
          name: name string of control
          wr_val_str: value string to write.  Can be integer, float or a
              alpha-numerical that is mapped to a integer or float.

        Raises:
          HwDriverError: Error occurred while using driver
          ServoDeviceError: if interfaces are not available within timeout period
        """
        with servo_logging.WrapSetCall(
            name, wr_val_str, known_exceptions=self.KNOWN_EXCEPTIONS
        ):
            self._get_param_drv(name, wr_val_str)

        return True

    def _get_param_drv(self, control_name, set_value=None):
        """Get access to driver for a given control.

        Note, some controls have different parameter dictionaries for 'getting' the
        control's value versus 'setting' it.  Boolean set_value distinguishes which is
        being requested.

        Args:
          control_name: string name of control
          set_value: string set value for set controls.

        Returns:
          tuple (params, drv, device_info) where:
            params: param dictionary for control
            drv: instance object of driver for particular control
            device_info: servo device information
        """
        val_pb = None
        if set_value is not None:
            val_pb = json_utils.wrap_value(set_value)

        return self._driver_client.CallDriver(
            vid=self.template.VID,
            pid=self.template.PID,
            serial=self._serial,
            interface_template=str(self._interfaces),
            control_name=control_name,
            device_type=self.template.TYPE,
            value=val_pb,
            set_empty_value=None if val_pb else empty_pb2.Empty(),
        )

    def clear_cached_drv(self):
        """Clear the cached drivers.

        The drivers are cached in the Dict _drv_dict when a control is got or set.
        When the servo interfaces are relocated, the cached values may become wrong.
        Should call this method to clear the cached values.
        """
        self._drv_dict = {}

    def doc_all(self):
        """Return all documentations for controls.

        Returns:
          string of <doc> text in config file (xml) and the params dictionary for
          all controls.

          For example:
          warm_reset             :: Reset the device warmly
          ------------------------> {'interface': '1', 'map': 'onoff_i', ... }
        """
        return self._system_config_client.GetDisplayConfig(
            vid=self.template.VID, pid=self.template.PID, serial=self._serial
        ).display_config

    def doc(self, name):
        """Retrieve doc string in system config file for given control name.

        Args:
          name: name string of control to get doc string

        Returns:
          doc string of name

        Raises:
          NameError: if fails to locate control
        """
        self._logger.debug("name(%s)", name)
        if self._system_config_client.IsControl(
            vid=self.template.VID,
            pid=self.template.PID,
            serial=self._serial,
            control_name=name,
        ).value:
            return self._system_config_client.GetControlDoc(
                vid=self.template.VID,
                pid=self.template.PID,
                serial=self._serial,
                name=name,
            ).doc
        raise NameError("No control %s" % name)

    def dump_to_xml(self, filename):
        """Dump the parsed system configuration to an XML file.

        Args:
          filename: string of the file to save to.
        """
        self._system_config_client.DumpToXml(
            vid=self.template.VID,
            pid=self.template.PID,
            serial=self._serial,
            filename=filename,
        )

    def hwinit(self, verbose, skip_controls, step_init=False):
        """Initialize all controls.

        These values are part of the system config XML files of the form
        init=<value>.  This command should be used by clients wishing to return the
        servo and DUT its connected to a known good/safe state.

        Note that initialization errors are ignored (as in some cases they could
        be caused by DUT firmware deficiencies). This might need to be fine tuned
        later.

        Args:
          verbose: boolean, if True prints info about control initialized.
            Otherwise prints nothing.
          skip_controls: a list of controls not to hwinit. For a root hub device,
            if a control is already initialized for its children, do not initialized
            the control for this device.
          step_init: bool - if True, interactively prompt y/n whether to
            initialize this control

        Returns:
          This function is called across RPC and as such is expected to return
          something unless transferring 'none' across is allowed. Hence adding a
          mock return value to make things simpler.
        """
        hwinit_list = json.loads(
            self._system_config_client.GetInitControls(
                vid=self.template.VID, pid=self.template.PID, serial=self._serial
            ).hwinit_json
        )
        for control_name, value in hwinit_list:
            if control_name in skip_controls:
                self._logger.debug(
                    "Skip initializing control %r because it is already initialized "
                    "for a child device.",
                    control_name,
                )
                continue
            if step_init and not _yes_no_input(
                "Initialize control {!r} to value {!r}? ".format(control_name, value)
            ):
                self._logger.debug(
                    "Skip initializing control %r because step_init is enabled and "
                    "the user requested to not initialize this control.",
                    control_name,
                )
                continue
            if verbose:
                self._logger.info("Initializing %s to %s", control_name, value)
            try:
                # Workaround for bug chrome-os-partner:42349. Without this check, the
                # gpio will briefly pulse low if we set it from high to high.
                if self.get(control_name) != value:
                    self.set(control_name, value)
                if verbose:
                    self._logger.debug(
                        "Successfully initialized %s to %s", control_name, value
                    )
            except Exception as error:
                self._logger.error("Problem initializing %s -> %s", control_name, value)
                self._logger.error(str(error))
                self._logger.error(
                    "Please consider verifying the logs and if the "
                    "error is not just a setup issue, consider filing "
                    "a bug. Also checkout go/servo-ki."
                )

        # If there is the control of 'active_dut_controller',
        # set active_dut_controller to the default device as initialization.
        try:
            if self._system_config_client.IsControl(
                vid=self.template.VID,
                pid=self.template.PID,
                serial=self._serial,
                control_name="active_dut_controller",
            ).value:
                self.set("active_dut_controller", "default")
        except Exception as error:
            self._logger.error("Problem setting active_dut_controller: %s", error)

        return True

    def get_hwinit_controls(self):
        """Get controls to be initialized."""
        return json.loads(
            self._system_config_client.GetInitControls(
                vid=self.template.VID, pid=self.template.PID, serial=self._serial
            ).hwinit_json
        )

    def get_all_controls(self):
        """Get all controls."""
        return set(
            json.loads(
                self._system_config_client.GetAllControls(
                    vid=self.template.VID, pid=self.template.PID, serial=self._serial
                ).controls_json
            )
        )

    def get_control_str(self, name):
        """Get doc string for a control."""
        return self._system_config_client.GetControlStr(
            vid=self.template.VID,
            pid=self.template.PID,
            serial=self._serial,
            name=name,
        ).doc

    def get_controls_for_tag(self, tag):
        """Get controls for a tag."""
        return json.loads(
            self._system_config_client.GetControlsForTag(
                vid=self.template.VID,
                pid=self.template.PID,
                serial=self._serial,
                tag=tag,
            ).controls_json
        )

    def is_control(self, name):
        """Check if control exists."""
        return self._system_config_client.IsControl(
            vid=self.template.VID,
            pid=self.template.PID,
            serial=self._serial,
            control_name=name,
        ).value

    def get_config_files(self):
        """Get loaded config files."""
        return self._system_config_client.GetConfigFiles(
            vid=self.template.VID, pid=self.template.PID, serial=self._serial
        ).files

    def get_servo_interfaces(self, vid, pid, board):
        """Get servo interfaces."""
        return json.loads(
            self._system_config_client.GetServoInterfaces(
                vid=vid, pid=pid, board=board
            ).interface_list_json
        )

    def get_root_hub_device(self):
        """Get the root hub device of this device, if it has one.

        This device might hang on another hub device.

        Returns:
          The root hub device of this device, or None if it does not have one.
        """
        root_entry = self.dev_entry.cluster_root
        if root_entry is None:
            return None
        return root_entry.servo_device

    def is_root_hub_device(self):
        """Check whether this device is a root hub device.

        Returns:
          True if this device is a root hub device, false otherwise.
        """
        return self.dev_entry.is_cluster_root()

    def get_child_devices(self):
        """Get the devices hanging on this device (directly or indirectly).

        Returns:
          A list of ServoDevice that hangs on this device directly or indirectly.
          If this device is not a root hub device, return an empty list.
        """
        child_devices: List[Any] = []
        if not self.is_root_hub_device():
            return child_devices
        for member in self.dev_entry.cluster_members:
            if member != self.dev_entry and member.servo_device is not None:
                child_devices.append(member.servo_device)
        return child_devices

    def to_json(self):
        """Serialize this device to a json string."""
        root_hub_device = self.get_root_hub_device()
        data = {
            "prefix": self.prefixes,
            "type": self.template.TYPE,
            "vendor_id": self.template.VID,
            "product_id": self.template.PID,
            "serial": self._serial,
            "sysfs_path": self._sysfs_path,
            "root_hub_device": str(root_hub_device) if root_hub_device else None,
            "child_devices": [str(dev) for dev in self.get_child_devices()],
        }
        return json_utils.dumps(data, indent=4)

    def limit_ec_driver_channel(self, control_name):
        return self._driver_client.LimitEcDriverChannel(
            vid=self.template.VID,
            pid=self.template.PID,
            serial=self._serial,
            device_type=self.template.TYPE,
            control_name=control_name,
        )

    def restore_ec_driver_channel(self, control_name):
        return self._driver_client.RestoreEcDriverChannel(
            vid=self.template.VID,
            pid=self.template.PID,
            serial=self._serial,
            device_type=self.template.TYPE,
            control_name=control_name,
        )

    def issue_cmd_get_results(self, cmds, regex_list, flush, timeout):
        return self._driver_client.IssueCmdGetResults(
            vid=self.template.VID,
            pid=self.template.PID,
            serial=self._serial,
            device_type=self.template.TYPE,
            cmds=cmds,
            regex_list=regex_list,
            flush=flush,
            time_out=timeout,
        )
