# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import json
import logging

from google.protobuf import empty_pb2
from google.protobuf import json_format

from servo.common.proto import servo_dev_grpc
from servo.common.proto import servo_dev_pb2
from servo.common.utils import json_utils
from servo.utils.keyboard import get_keyboard
from servo.utils.keyboard import set_keyboard
from servo.utils.keyboard import set_usb_keyboard
from servo.utils.watchdog_util import get_device_from_type
from servo.utils.watchdog_util import get_device_state


class ServoImplError(Exception):
    """Exception class for Servo Impl."""


class ServoImpl(servo_dev_grpc.ServoServiceServicer):
    # pylint: disable=invalid-name
    def __init__(self, grpc_core_addr, servod):
        self.grpc_core_addr = grpc_core_addr
        self.servod = servod
        self.logger = logging.getLogger("ServoService")

    def GetServo(self, request, context):
        """
        Get Value from servo core
        """
        self.logger.debug("Handle request for %s, in context %s", request, context)
        service = servo_dev_pb2.ServiceResponse()
        service.response = self.servod.get(request.control_name)
        return service

    def SetServo(self, request, context):
        """
        Set value on servo core
        """
        self.logger.debug("Handle request for %s, in context %s", request, context)
        value = json_format.MessageToDict(request.value)
        self.servod.set(request.control_name, value)
        return empty_pb2.Empty()

    def GetVersion(self, request, context):
        """
        Get servo version
        """
        self.logger.debug("Handle request for %s, in context %s", request, context)
        service = servo_dev_pb2.ServiceResponse()
        service.response = self.servod._get_version()
        return service

    def InitSelectedControls(self, request, context):
        """
        Init Servo selected controls
        """
        self.logger.debug("Handle request for %s, in context %s", request, context)
        if not hasattr(self.servod, "selected_controls"):
            self.servod.selected_controls = {}
        return empty_pb2.Empty()

    def GetSelectedControls(self, request, context):
        """
        Get servo selected controls
        """
        self.logger.debug("Handle request for %s, in context %s", request, context)
        if hasattr(self.servod, "selected_controls"):
            selected_controls = self.servod.selected_controls
        else:
            selected_controls = []
        response = servo_dev_pb2.ServiceResponse(
            response=json_utils.dumps(selected_controls)
        )
        return response

    def SetSelectedControls(self, request, context):
        """
        Set servo selected controls
        """
        self.logger.debug("Handle request for %s, in context %s", request, context)
        value = json_format.MessageToDict(request.control_value)
        self.servod.selected_controls[request.control_name] = value
        return empty_pb2.Empty()

    def GetInitKeyboard(self, request, context):
        """
        Init default keyboard
        """
        self.logger.debug(context)
        if not self.servod._keyboard:
            # Setup the keyboard handler and turn it off.
            set_keyboard(self.grpc_core_addr, self.servod, request.type, "off")
        response = servo_dev_pb2.OpenResponse()
        response.open = int(self.servod._keyboard.is_open())
        return response

    def SetInitKeyboard(self, request, context):
        """Initialize the default keyboard on the servo instance."""
        self.logger.debug("Handle request for %s, in context %s", request, context)
        value = json_format.MessageToDict(request.value)
        set_keyboard(self.grpc_core_addr, self.servod, request.handler_type, value)
        return empty_pb2.Empty()

    def InitV4Device(self, servo_type, devices_keys):
        """Init the V4 activate servo"""
        devices = servo_type.split("_with_")[-1].split("_and_")
        usable_devices = set(devices).intersection(devices_keys)

        self.servod.v4_device_info = {}
        self.servod.v4_device_info["default"] = devices[0]
        self.servod.v4_device_info["usable_devices"] = list(usable_devices)

        self.servod._can_control_cr50 = self.servod.has_control("cr50_servo")
        self.servod._can_control_servo = ("servo_micro" in devices) or (
            "c2d2" in devices
        )
        # setup a ccd alias, so tests don't have to distinguish between
        # ccd_gsc and ccd_cr50
        for device in usable_devices:
            if "ccd" in device:
                self.servod.v4_device_info["ccd"] = device
                break
        return empty_pb2.Empty()

    def GetInitV4Device(self, request, context):
        """
        Get device info for V4 servo
        """
        self.logger.debug("Handle request for %s, in context %s", request, context)
        if not hasattr(self.servod, "v4_device_info"):
            self.InitV4Device(request.servo_type, request.devices_keys)
        devices = self.servod.v4_device_info.get(request.info_type)
        service = servo_dev_pb2.V4DeviceResponse()
        if isinstance(devices, list):
            service.device_list.list.extend(devices)
        else:
            service.value = devices
        return service

    def IsServoHasAttr(self, request, context):
        """Check if servo instance has attribute"""
        self.logger.debug("Handle request for %s, in context %s", request, context)
        has_attr = hasattr(self.servod, request.name) and getattr(
            self.servod, request.name
        )
        return servo_dev_pb2.BoolResponse(value=bool(has_attr))

    def GetSerial(self, request, context):
        self.logger.debug("Handle request for %s, in context %s", request, context)
        response = servo_dev_pb2.GetResponse()
        root_dev = self.servod.get_root_device()
        if root_dev is not None:
            response.get_value = root_dev._serial
        else:
            response.get_value = self.servod.get_main_device()._serial
        return response

    def HasControl(self, request, context):
        self.logger.debug("Handle request for %s, in context %s", request, context)
        response = servo_dev_pb2.BoolResponse()
        response.value = self.servod.has_control(request.control_name)
        return response

    def GetSerials(self, request, context):
        self.logger.debug("Handle request for %s, in context %s", request, context)
        response = servo_dev_pb2.GetResponse()
        response.get_value = json_utils.dumps(self.servod.get_servo_serials())
        return response

    def GetAllControls(self, request, context):
        self.logger.debug("Handle request for %s, in context %s", request, context)
        response = servo_dev_pb2.GetResponse()
        response.get_value = json_utils.dumps(list(self.servod._controls))
        return response

    def GetInitUsbKeyboard(self, request, context):
        """
        Init usb keyboard
        """
        self.logger.debug("Handle request for %s, in context %s", request, context)
        if not self.servod._usb_keyboard:
            # Setup the keyboard handler and turn it off.
            self.set_init_usb_keyboard("off", request.value)
        response = servo_dev_pb2.OpenResponse()
        response.open = int(self.servod._usb_keyboard.is_open())
        return response

    def set_init_usb_keyboard(self, value, legacy_atmega):
        """init usb keyboard"""
        if not self.servod._usb_keyboard:
            # Setup the keyboard always, and then turn on/off as needed.
            set_usb_keyboard(self.grpc_core_addr, self.servod, legacy_atmega)

        # Robustly handle boolean-like values from JSON/gRPC
        if value in ["on", "yes", True, 1, "1"]:
            self.servod._usb_keyboard.open()
        else:
            self.servod._usb_keyboard.close()

    def SetInitUsbKeyboard(self, request, context):
        """Initialize the default keyboard on the servo instance."""
        self.logger.debug("Handle request for %s, in context %s", request, context)
        value = json_format.MessageToDict(request.value)
        self.set_init_usb_keyboard(value, request.is_legacy)
        return empty_pb2.Empty()

    def GetFileConfig(self, request, context):
        """Get servo files configs"""
        self.logger.debug("Handle request for %s, in context %s", request, context)
        file_config = json_utils.dumps(
            self.servod.get_config_files(), sort_keys=True, indent=4
        )
        return servo_dev_pb2.ServiceResponse(response=file_config)

    def GetDevices(self, request, context):
        """get servo devices"""
        self.logger.debug("Handle request for %s, in context %s", request, context)
        devices_json = []
        for device in self.servod.get_devices():
            devices_json.append(json.loads(device.to_json()))
        devices = json_utils.dumps(devices_json, indent=4)
        return servo_dev_pb2.ServiceResponse(response=devices)

    def GetTaggedControls(self, request, context):
        """Retrieve all controls under a certain tag."""
        self.logger.debug("Handle request for %s, in context %s", request, context)
        params = json.loads(request.name)
        if "tag" not in params:
            raise ServoImplError("tag needs to be specified in params.")
        controls = self.servod.get_controls_for_tag(params["tag"])
        return servo_dev_pb2.ServiceResponse(response=json_utils.dumps(controls))

    def GetBaseBoard(self, request, context):
        """Get Base board name"""
        self.logger.debug("Handle request for %s, in context %s", request, context)
        base_board = self.servod.get_base_board()
        return servo_dev_pb2.ServiceResponse(response=base_board)

    def SetGetAll(self, request, context):
        """get/set commands"""
        self.logger.debug("Handle request for %s, in context %s", request, context)
        response = self.servod.set_get_all(request.request_list)
        # Ensure all elements in the response are strings, as required by the proto.
        response_list = [str(val) for val in response]
        return servo_dev_pb2.ListResponse(response_list=response_list)

    def SetKeyboardKey(self, request, context):
        """Set keyboard key duration"""
        self.logger.debug("Handle request for %s, in context %s", request, context)
        turn_off_needed = False
        keyboard = get_keyboard(servod=self.servod, handler=request.handler)
        if not keyboard.is_open():
            turn_off_needed = True
            self.logger.info(
                "Keyboard %s handler not setup. Turning on now.", request.handler
            )
            keyboard.open()
        func = getattr(keyboard, request.key, None)
        if func is None:
            raise ServoImplError("Key %r not found." % (request.key,))

        duration = json_format.MessageToDict(request.duration)
        duration_val = 0.0
        if isinstance(duration, str):
            try:
                duration_val = float(duration)
            except ValueError:
                # If it's a string like "press", we must resolve it.
                # We attempt to resolve the string alias to a float duration
                # by querying the map associated with the specific key being pressed.
                duration_val = self.servod.get(request.key)
        else:
            duration_val = float(duration)

        func(press_secs=duration_val)
        if turn_off_needed:
            self.logger.error("Keyboard was not on for call. Turning it off again.")
            keyboard.close()
        return empty_pb2.Empty()

    def SetArbKeyConfig(self, request, context):
        """Set arb_key"""
        self.logger.debug("Handle request for %s, in context %s", request, context)
        get_keyboard(self.servod, request.handler).arb_key_config(request.key)
        return empty_pb2.Empty()

    def SetArbKeysConfig(self, request, context):
        """Set arb_key"""
        self.logger.debug("Handle request for %s, in context %s", request, context)
        get_keyboard(self.servod, request.handler).arb_keys_config(request.key)
        return empty_pb2.Empty()

    def LimitEcDriverChannel(self, request, context):
        """limit channel for ec driver on specific servod device"""
        self.logger.debug("Handle request for %s, in context %s", request, context)

        prefix = getattr(request, "prefix", "")
        if prefix and prefix in self.servod._devices:
            dev = self.servod._devices[prefix]
        else:
            dev = self.servod.get_main_device()
        dev.limit_ec_driver_channel("ec_gpio")
        return empty_pb2.Empty()

    def RestoreEcDriverChannel(self, request, context):
        """restore channel for ec driver on specific servod device"""
        self.logger.debug("Handle request for %s, in context %s", request, context)

        prefix = getattr(request, "prefix", "")
        if prefix and prefix in self.servod._devices:
            dev = self.servod._devices[prefix]
        else:
            dev = self.servod.get_main_device()
        dev.restore_ec_driver_channel("ec_gpio")
        return empty_pb2.Empty()

    def IssueCmdGetResult(self, request, context):
        self.logger.debug("Handle request for %s, in context %s", request, context)

        prefix = getattr(request, "prefix", "")
        if prefix and prefix in self.servod._devices:
            dev = self.servod._devices[prefix]
        else:
            dev = self.servod.get_main_device()
        dev.issue_cmd_get_results(
            request.cmds,
            request.regex_list,
            flush=request.flush,
            timeout=request.time_out,
        )
        return empty_pb2.Empty()

    def GetWatchdog(self, request, context):
        """Get watchdog devices"""
        self.logger.debug("Handle request for %s, in context %s", request, context)
        states = [""]
        for device in self.servod.get_devices():
            states.append(get_device_state(device))

        state_devices = "\n".join(states)
        return servo_dev_pb2.ServiceResponse(response=state_devices)

    def UpdateDeviceDisconnectOk(self, request, context):
        """
        Update if it's ok for the device to disconnect.
        If it's not ok for the device to disconnect, the watchdog may kill servod.
        If you know you're going to disconnect a device, you should update let servo
        know.
        """
        self.logger.debug("Handle request for %s, in context %s", request, context)
        serialnames = self.servod.get_servo_serials()
        devices_dict = self.servod._devices
        unique_devices = self.servod.get_devices()

        device = None
        # 1. Exact match on prefix (e.g. 'root', 'main', 'ccd_cr50', 'ccd_gsc')
        if request.name in devices_dict:
            device = devices_dict[request.name]
        # 2. Exact match on serialname
        elif request.name in serialnames.values():
            for dev in unique_devices:
                if request.name in dev.get_id():
                    device = dev
                    break
        # 3. Match on template TYPE
        else:
            device = get_device_from_type(self.servod, request.name)

        if device is None:
            raise ServoImplError("Invalid device %s" % request.name)

        device.set_disconnect_ok(request.disconnect_ok)
        return empty_pb2.Empty()

    def GetWatchdogReconnectTimeout(self, unused_request, unused_context):
        """Get the current reconnect timeout from the active watchdog thread."""
        timeout = -1.0
        if self.servod._watchdog_thread:
            timeout = self.servod._watchdog_thread.reconnect_timeout
        return servo_dev_pb2.ReconnectTimeoutResponse(timeout_sec=timeout)

    def SetWatchdogReconnectTimeout(self, request, unused_context):
        """Set the reconnect timeout on the active watchdog thread."""
        if self.servod._watchdog_thread:
            self.servod._watchdog_thread.reconnect_timeout = request.timeout_sec
        return empty_pb2.Empty()

    def GetCcdState(self, request, context):
        """
        Get ccd_state
        """
        self.logger.debug("Handle request for %s, in context %s", request, context)
        ccd_device = get_device_from_type(self.servod, "ccd")
        state = int(ccd_device.is_connected()) if ccd_device else 0
        return servo_dev_pb2.CcdStateResponse(state=state)

    def GetCrosChip(self, request, context):
        """
        Get chip of main device
        """
        self.logger.debug("Handle request for %s, in context %s", request, context)
        params = json.loads(request.name)
        default_chip = params.get("chip", "unknown")
        devices = self.servod.get_devices()
        default_device = self.servod.get_main_device()

        _chips = {}
        for device in devices:
            _chips[device] = params.get(
                "chip_for_" + device.template.TYPE, default_chip
            )
        _chip = _chips[default_device]
        return servo_dev_pb2.ServiceResponse(response=_chip)

    def GetUSBHubAddress(self, unused_request, unused_context):
        hub_device = self.servod.get_root_device()
        if not hub_device.template.HUB_SERVO:
            raise ServoImplError("There is no USB hub device connected.")

        hub_on_servo = hub_device.dev_entry.hub_stub
        return servo_dev_pb2.ServiceResponse(response=hub_on_servo)
