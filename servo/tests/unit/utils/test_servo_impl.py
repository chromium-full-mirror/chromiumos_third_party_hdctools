# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import argparse
import json
import unittest
import unittest.mock
from unittest.mock import patch

from google.protobuf import empty_pb2

from servo import servo_dev
from servo import servo_dev_templates as tmpl
from servo import servo_server
from servo.common.config import system_config
from servo.common.proto.servo_dev_pb2 import BoolRequest
from servo.common.proto.servo_dev_pb2 import GetRequest
from servo.common.proto.servo_dev_pb2 import IssueCmdRequest
from servo.common.proto.servo_dev_pb2 import KeyboardRequest
from servo.common.proto.servo_dev_pb2 import KeyRequest
from servo.common.proto.servo_dev_pb2 import ListRequest
from servo.common.proto.servo_dev_pb2 import ServiceRequest
from servo.common.proto.servo_dev_pb2 import SetKeyboard
from servo.common.proto.servo_dev_pb2 import SetRequest
from servo.common.proto.servo_dev_pb2 import SetServoRequest
from servo.common.proto.servo_dev_pb2 import SetUsbRequest
from servo.common.proto.servo_dev_pb2 import V4DeviceRequest
from servo.common.proto.servo_dev_pb2 import WatchdogRequest
from servo.grpc_server.impl.servo_impl import ServoImpl
from servo.utils import servo_dev_hierarchy


class TestServoImpl(unittest.TestCase):
    def setUp(self):
        self._servod = servo_server.Servod()
        micro_entry = servo_dev_hierarchy.ServoDeviceEntry(
            tmpl.GetVID("servo_micro"),
            tmpl.GetPID("servo_micro"),
            "servo_micro_serial",
            "/sys/bus/usb/devices/-2-1.2.3",
        )
        micro_entry.devopts = argparse.Namespace()
        micro_entry.devopts.prefix = ["micro"]
        micro_entry.devopts.board = "atlas"
        micro_entry.devopts.model = "default"
        self._micro_dev = servo_dev.ServoDevice(
            micro_entry, system_config.SystemConfig(), None, self._servod
        )
        v4_entry = servo_dev_hierarchy.ServoDeviceEntry(
            tmpl.GetVID("servo_v4"),
            tmpl.GetPID("servo_v4"),
            "servo_v4_serial",
            "/sys/bus/usb/devices/-2-1.2",
        )
        v4_entry.devopts = argparse.Namespace()
        v4_entry.devopts.prefix = ["v4"]
        v4_entry.devopts.board = "brya"
        v4_entry.devopts.model = "default"
        self._v4_dev = servo_dev.ServoDevice(
            v4_entry, system_config.SystemConfig(), None, self._servod
        )

        ccd_cr50 = servo_dev_hierarchy.ServoDeviceEntry(
            tmpl.GetVID("ccd_cr50"),
            tmpl.GetPID("ccd_cr50"),
            "ccd_cr50_serial",
            "/sys/bus/usb/devices/-2-1.4",
        )
        ccd_cr50.devopts = argparse.Namespace()
        ccd_cr50.devopts.prefix = ["ccd"]
        ccd_cr50.devopts.board = "brya"
        ccd_cr50.devopts.model = "default"
        self.ccd_cr50 = servo_dev.ServoDevice(
            ccd_cr50, system_config.SystemConfig(), None, self._servod
        )

    def test_GetServo(self):
        """Test GetServo()."""
        self._servod.get = unittest.mock.MagicMock(return_value="servo_type")
        servo_impl = ServoImpl(servod=self._servod)
        request = GetRequest(control_name="servo_type")
        servo_impl.GetServo(request, None)
        self._servod.get.assert_called_once_with("servo_type")

    def test_SetServo(self):
        """Test GetServo()."""
        self._servod.set = unittest.mock.MagicMock()
        servo_impl = ServoImpl(servod=self._servod)
        request = SetServoRequest(control_name="set_test", value="test")
        servo_impl.SetServo(request, None)
        self._servod.set.assert_called_once_with("set_test", "test")

    def test_GetVersion_same_root_and_main_devices(self):
        """Test GetVersion_same_root_and_main_devices()."""
        self._servod.get_main_device = unittest.mock.MagicMock(
            return_value=self._micro_dev
        )
        self._servod.get_root_device = unittest.mock.MagicMock(
            return_value=self._micro_dev
        )
        servo_impl = ServoImpl(servod=self._servod)
        service = servo_impl.GetVersion(empty_pb2.Empty(), None)
        self.assertEqual(service.response, self._micro_dev.template.TYPE)

    def test_GetVersion_different_root_and_main_devices(self):
        """Test GetVersion_different_root_and_main_devices()"""
        self._servod.get_main_device = unittest.mock.MagicMock(
            return_value=self._micro_dev
        )
        self._servod.get_root_device = unittest.mock.MagicMock(
            return_value=self._v4_dev
        )
        servo_impl = ServoImpl(servod=self._servod)
        service = servo_impl.GetVersion(empty_pb2.Empty(), None)
        self.assertEqual(
            service.response,
            "{}_with_{}".format(
                self._v4_dev.template.TYPE, self._micro_dev.template.TYPE
            ),
        )

    def test_InitSelectedControls(self):
        """Test InitSelectedControls()"""
        self.assertFalse(hasattr(self._servod, "selected_controls"))
        servo_impl = ServoImpl(servod=self._servod)
        servo_impl.InitSelectedControls(empty_pb2.Empty(), None)
        self.assertTrue(hasattr(self._servod, "selected_controls"))

    def test_GetSelectedControls(self):
        """Test GetSelectedControls()"""
        self._servod.selected_controls = [["control_name", "value"]]
        servo_impl = ServoImpl(servod=self._servod)
        selected_controls = json.loads(
            servo_impl.GetSelectedControls(empty_pb2.Empty(), None).response
        )
        self.assertEqual(selected_controls, self._servod.selected_controls)

    def test_SetSelectedControls(self):
        """Test SetSelectedControls()"""
        self._servod.selected_controls = {}
        servo_impl = ServoImpl(servod=self._servod)
        request = SetRequest(control_name="power", control_value="on")
        servo_impl.SetSelectedControls(request, None)
        selected_controls = json.loads(
            servo_impl.GetSelectedControls(empty_pb2.Empty(), None).response
        )
        self.assertIn("power", selected_controls)
        self.assertEqual(selected_controls["power"], "on")

    def test_GetInitKeyboard(self):
        """Test GetInitKeyboard()"""
        self._servod._keyboard = unittest.mock.MagicMock()
        self._servod._keyboard.is_open = unittest.mock.MagicMock(return_value=True)
        request = KeyboardRequest(type="test_type")
        servo_impl = ServoImpl(servod=self._servod)
        result = servo_impl.GetInitKeyboard(request, None)
        self._servod._keyboard.is_open.assert_called_once()
        self.assertEqual(result.open, 1)

    def test_SetInitKeyboard(self):
        """Test SetInitKeyboard()"""
        self._servod._keyboard = unittest.mock.MagicMock()
        self._servod._keyboard.open = unittest.mock.MagicMock()
        self._servod._keyboard.close = unittest.mock.MagicMock()
        request = SetKeyboard(handler_type="usb", value="")
        servo_impl = ServoImpl(servod=self._servod)
        servo_impl.SetInitKeyboard(request, None)
        self._servod._keyboard.close.assert_called_once()
        request = SetKeyboard(handler_type="usb", value="on")
        servo_impl = ServoImpl(servod=self._servod)
        servo_impl.SetInitKeyboard(request, None)
        self._servod._keyboard.open.assert_called_once()

    def test_GetInitV4Device(self):
        """Test test_GetInitV4Device()"""
        V4_DEVICES = {
            "ccd_cr50": False,
            "ccd_ti50": False,
            "ccd_gsc": False,
            "servo_micro": True,
            "servo_v4": True,
        }
        self.assertFalse(hasattr(self._servod, "v4_device_info"))
        servo_impl = ServoImpl(servod=self._servod)
        servo_type = "{}_with_{}_and_{}".format(
            self._v4_dev.template.TYPE,
            self._micro_dev.template.TYPE,
            self._v4_dev.template.TYPE,
        )
        request = V4DeviceRequest(
            servo_type=servo_type, devices_keys=V4_DEVICES.keys(), info_type="default"
        )
        servo_impl.GetInitV4Device(request, None)
        self.assertTrue(hasattr(self._servod, "v4_device_info"))
        self.assertEqual(
            self._servod.v4_device_info["default"], self._micro_dev.template.TYPE
        )
        self.assertIn(
            self._micro_dev.template.TYPE, self._servod.v4_device_info["usable_devices"]
        )
        self.assertIn(
            self._v4_dev.template.TYPE, self._servod.v4_device_info["usable_devices"]
        )

    def test_IsServoHasAttr(self):
        """Test IsServoHasAttr()"""
        servo_impl = ServoImpl(servod=self._servod)
        request = ServiceRequest(name="_keyboard")
        is_servo_has_keyboard = servo_impl.IsServoHasAttr(request, None).value
        self.assertEqual(is_servo_has_keyboard, False)

    def test_GetSerial(self):
        """Test GetSerial"""
        self._servod.add_device(self._v4_dev, "main")
        servo_impl = ServoImpl(servod=self._servod)
        serial = servo_impl.GetSerial(empty_pb2.Empty(), None).get_value
        self.assertEqual(serial, "servo_v4_serial")

    def test_GetSerials(self):
        """Test GetSerials"""
        self._servod.add_device(self._v4_dev, "main")
        self._servod.add_device(self._micro_dev, "dev")
        servo_impl = ServoImpl(servod=self._servod)
        serial = json.loads(servo_impl.GetSerials(empty_pb2.Empty(), None).get_value)
        self.assertEqual(
            serial,
            {
                "main": "servo_v4_serial",
                "": "servo_v4_serial",
                "dev": "servo_micro_serial",
            },
        )

    def test_GetAllControls(self):
        """Test GetAllControls"""
        self._servod._controls = [
            "main.cold_reset",
            "root.cold_reset",
            "ccd_cr50.cold_reset",
        ]
        servo_impl = ServoImpl(servod=self._servod)
        controls = json.loads(
            servo_impl.GetAllControls(empty_pb2.Empty(), None).get_value
        )
        self.assertEqual(controls, self._servod._controls)

    def test_HasControl(self):
        """Test HasControl"""
        self._servod._controls = [
            "main.cold_reset",
            "root.cold_reset",
            "ccd_cr50.cold_reset",
        ]
        servo_impl = ServoImpl(servod=self._servod)
        self.assertFalse(
            servo_impl.HasControl(GetRequest(control_name="test"), None).value
        )
        self.assertTrue(
            servo_impl.HasControl(
                GetRequest(control_name="main.cold_reset"), None
            ).value
        )

    def test_GetInitUsbKeyboard(self):
        """Test GetInitKeyboard()"""
        self._servod._controls = ["atmega_rst"]
        servo_impl = ServoImpl(servod=self._servod)

        def init_servo_usb_keyboard(
            val, keyboard_type
        ):  # pylint: disable=unused-argument
            self._servod._usb_keyboard = unittest.mock.MagicMock()
            self._servod._usb_keyboard.is_open = unittest.mock.MagicMock(
                return_value=True
            )

        servo_impl.set_init_usb_keyboard = unittest.mock.MagicMock(
            side_effect=init_servo_usb_keyboard
        )
        request = BoolRequest(value=False)
        is_open = servo_impl.GetInitUsbKeyboard(request, None).open
        servo_impl.set_init_usb_keyboard.assert_called_once()
        self.assertEqual(is_open, True)

    def test_SetInitUsbKeyboard(self):
        """Test SetInitUsbKeyboard()"""
        servo_impl = ServoImpl(servod=self._servod)
        servo_impl.set_init_usb_keyboard = unittest.mock.MagicMock()
        request = SetUsbRequest(is_legacy=False, value=1)
        servo_impl.SetInitUsbKeyboard(request, None)
        servo_impl.set_init_usb_keyboard.assert_called_once_with(1, False)

    def test_GetFileConfig(self):
        """Test GetFileConfig()"""
        self._servod.get_config_files = unittest.mock.MagicMock(return_value={})
        servo_impl = ServoImpl(servod=self._servod)
        servo_impl.GetFileConfig(empty_pb2.Empty(), None)
        self._servod.get_config_files.assert_called_once()

    def test_GetDevices(self):
        """Test GetDevices()"""
        self._servod.get_devices = unittest.mock.MagicMock(return_value={})
        servo_impl = ServoImpl(servod=self._servod)
        servo_impl.GetDevices(empty_pb2.Empty(), None)
        self._servod.get_devices.assert_called_once()

    def test_GetTaggedControls(self):
        """Test GetTaggedControls()"""
        self._servod.get_controls_for_tag = unittest.mock.MagicMock(return_value={})
        servo_impl = ServoImpl(servod=self._servod)
        request = ServiceRequest(name='{"tag": "test"}')
        servo_impl.GetTaggedControls(request, None)
        self._servod.get_controls_for_tag.assert_called_once_with("test")

    def test_GetBaseBoard(self):
        """Test GetBaseBoard()"""
        self._servod.get_base_board = unittest.mock.MagicMock(return_value="board")
        servo_impl = ServoImpl(servod=self._servod)
        servo_impl.GetBaseBoard(empty_pb2.Empty(), None)
        self._servod.get_base_board.assert_called_once()

    def test_SetGetAll(self):
        """Test SetGetAll()"""
        self._servod.set_get_all = unittest.mock.MagicMock()
        servo_impl = ServoImpl(servod=self._servod)
        servo_impl.SetGetAll(ListRequest(request_list=["power:on", "test:value"]), None)
        self._servod.set_get_all.assert_called_once()

    @patch("servo.common.utils.keyboard_handlers.ChromeECHandler")
    def test_SetArbKeyConfig(self, mocked_handler_template):
        """Test SetArbKeyConfig()"""
        self._servod._keyboard = mocked_handler_template()
        self._servod._keyboard.arb_key_config = mocked_handler_template()
        servo_impl = ServoImpl(servod=self._servod)
        request = KeyRequest(key="enter", handler="test")
        servo_impl.SetArbKeyConfig(request, None)
        self._servod._keyboard.arb_key_config.assert_called_once_with("enter")

    @patch("servo.common.utils.keyboard_handlers.ChromeECHandler")
    def test_SetArbKeysConfig(self, mocked_handler_template):
        """Test SetArbKeysConfig()"""
        self._servod._keyboard = mocked_handler_template()
        self._servod._keyboard.arb_keys_config = mocked_handler_template()
        servo_impl = ServoImpl(servod=self._servod)
        request = KeyRequest(key="enter", handler="['test', 'test2']")
        servo_impl.SetArbKeysConfig(request, None)
        self._servod._keyboard.arb_keys_config.assert_called_once_with("enter")

    def test_LimitEcDriverChannel(self):
        """Test LimitEcDriverChannel()"""
        self._servod.get_main_device = unittest.mock.MagicMock(
            return_value=self._v4_dev
        )
        drv = unittest.mock.MagicMock()
        drv._limit_channel = unittest.mock.MagicMock()
        self._v4_dev._get_param_drv = unittest.mock.MagicMock(
            return_value=("", drv, "")
        )
        servo_impl = ServoImpl(servod=self._servod)
        servo_impl.LimitEcDriverChannel(empty_pb2.Empty(), None)
        drv._limit_channel.assert_called_once()

    def test_IssueCmdGetResult(self):
        """Test IssueCmdGetResult()"""
        self._servod.get_main_device = unittest.mock.MagicMock(
            return_value=self._v4_dev
        )
        drv = unittest.mock.MagicMock()
        drv._issue_cmd_get_results = unittest.mock.MagicMock()
        self._v4_dev._get_param_drv = unittest.mock.MagicMock(
            return_value=("", drv, "")
        )
        servo_impl = ServoImpl(servod=self._servod)
        request = IssueCmdRequest(cmds="test", flush=True, regex_list="", time_out=5)
        servo_impl.IssueCmdGetResult(request, None)
        drv._issue_cmd_get_results.assert_called_once_with(
            "test", [], flush=True, timeout=5
        )

    def test_RestoreEcDriverChannel(self):
        """Test RestoreEcDriverChannel()"""
        self._servod.get_main_device = unittest.mock.MagicMock(
            return_value=self._v4_dev
        )
        drv = unittest.mock.MagicMock()
        drv._restore_channel = unittest.mock.MagicMock()
        self._v4_dev._get_param_drv = unittest.mock.MagicMock(
            return_value=("", drv, "")
        )
        servo_impl = ServoImpl(servod=self._servod)
        servo_impl.RestoreEcDriverChannel(empty_pb2.Empty(), None)
        drv._restore_channel.assert_called_once()

    def test_GetWatchdog(self):
        """Test GetWatchdog()"""
        self._servod.add_device(self._v4_dev, "main")
        self._servod.add_device(self._micro_dev, "dev")
        servo_impl = ServoImpl(servod=self._servod)
        devices = servo_impl.GetWatchdog(empty_pb2.Empty(), None).response
        self.assertEqual("\nv4, main: disconnected\nmicro, dev: disconnected", devices)

    def test_UpdateDeviceDisconnectOk(self):
        """Test UpdateDeviceDisconnectOk()"""
        self._servod.add_device(self._v4_dev, "main")
        self._servod.add_device(self._micro_dev, "dev")
        servo_impl = ServoImpl(servod=self._servod)
        request = WatchdogRequest(name="servo_v4", disconnect_ok=False)
        servo_impl.UpdateDeviceDisconnectOk(request, None)
        devices = servo_impl.GetWatchdog(request, None).response
        self.assertEqual("\nv4, main: disconnected\nmicro, dev: disconnected", devices)
        request = WatchdogRequest(name="servo_v4", disconnect_ok=True)
        servo_impl.UpdateDeviceDisconnectOk(request, None)
        devices = servo_impl.GetWatchdog(request, None).response
        self.assertEqual(
            "\nv4, main: disconnected (disconnect ok)\nmicro, dev: disconnected",
            devices,
        )

    def test_GetCcdState(self):
        """Test GetCcdState()"""
        self.ccd_cr50.is_connected = unittest.mock.MagicMock(return_value=True)
        self.ccd_cr50.template.TYPE = "ccd"
        self._servod.add_device(self.ccd_cr50, "main")
        servo_impl = ServoImpl(servod=self._servod)
        ccd_state = servo_impl.GetCcdState(empty_pb2.Empty(), None).state
        self.assertEqual(ccd_state, True)

    def test_GetCrosChip(self):
        """Test GetCrosChip()"""
        params = {"chip": "main"}
        self._servod.add_device(self._v4_dev, "main")
        servo_impl = ServoImpl(servod=self._servod)
        request = ServiceRequest(name=json.dumps(params))
        chip = servo_impl.GetCrosChip(request, None).response
        self.assertEqual(chip, "main")
