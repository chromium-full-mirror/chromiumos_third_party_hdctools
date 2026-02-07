# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import argparse
import unittest
import unittest.mock
from unittest.mock import patch

from google.protobuf import empty_pb2

from servo.common.config import system_config
from servo.common.proto.servo_dev_pb2 import BoolRequest
from servo.common.proto.servo_dev_pb2 import IssueCmdOnMainDevRequest
from servo.common.proto.servo_dev_pb2 import KeyboardRequest
from servo.common.proto.servo_dev_pb2 import KeyRequest
from servo.common.proto.servo_dev_pb2 import ListRequest
from servo.common.proto.servo_dev_pb2 import SetKeyboard
from servo.common.proto.servo_dev_pb2 import SetRequest
from servo.common.proto.servo_dev_pb2 import SetServoRequest
from servo.common.proto.servo_dev_pb2 import SetUsbRequest
from servo.common.proto.servo_dev_pb2 import V4DeviceRequest
from servo.common.proto.servo_dev_pb2 import WatchdogRequest
from servo.core import servo_dev
from servo.core import servo_dev_templates as tmpl
from servo.core import servo_server
from servo.core.grpc_server.impl.servo_impl import ServoImpl
from servo.utils import servo_dev_hierarchy


class TestServoImpl(unittest.TestCase):
    def setUp(self):
        # Patch GrpcClient and other grpc modules to avoid network calls
        patcher = patch("servo.core.servo_dev.GrpcClient")
        self.mock_grpc_client = patcher.start()
        self.addCleanup(patcher.stop)

        patcher_driver = patch("servo.core.servo_dev.driver_grpc")
        self.mock_driver_grpc = patcher_driver.start()
        self.addCleanup(patcher_driver.stop)

        patcher_syscfg = patch("servo.core.servo_dev.system_config_grpc")
        self.mock_syscfg_grpc = patcher_syscfg.start()
        self.addCleanup(patcher_syscfg.stop)

        self.grpc_core_addr = ("localhost", 9999)
        self._servod = servo_server.Servod()
        micro_entry = servo_dev_hierarchy.ServoDeviceEntry(
            tmpl.get_vid("servo_micro"),
            tmpl.get_pid("servo_micro"),
            "servo_micro_serial",
            "/sys/bus/usb/devices/-2-1.2.3",
        )
        micro_entry.devopts = argparse.Namespace()
        micro_entry.devopts.prefix = ["micro"]
        micro_entry.devopts.board = "atlas"
        micro_entry.devopts.model = "default"
        micro_entry.devopts.token_db = "default"
        self._micro_dev = servo_dev.ServoDevice(
            micro_entry,
            system_config.SystemConfig(),
            ("localhost", 9999),
            None,
            self._servod,
        )
        v4_entry = servo_dev_hierarchy.ServoDeviceEntry(
            tmpl.get_vid("servo_v4"),
            tmpl.get_pid("servo_v4"),
            "servo_v4_serial",
            "/sys/bus/usb/devices/-2-1.2",
        )
        v4_entry.devopts = argparse.Namespace()
        v4_entry.devopts.prefix = ["v4"]
        v4_entry.devopts.board = "brya"
        v4_entry.devopts.model = "default"
        v4_entry.devopts.token_db = "default"
        self._v4_dev = servo_dev.ServoDevice(
            v4_entry,
            system_config.SystemConfig(),
            ("localhost", 9999),
            None,
            self._servod,
        )

        ccd_cr50 = servo_dev_hierarchy.ServoDeviceEntry(
            tmpl.get_vid("ccd_cr50"),
            tmpl.get_pid("ccd_cr50"),
            "ccd_cr50_serial",
            "/sys/bus/usb/devices/-2-1.4",
        )
        ccd_cr50.devopts = argparse.Namespace()
        ccd_cr50.devopts.prefix = ["ccd"]
        ccd_cr50.devopts.board = "brya"
        ccd_cr50.devopts.model = "default"
        ccd_cr50.devopts.token_db = "default"
        self.ccd_cr50 = servo_dev.ServoDevice(
            ccd_cr50,
            system_config.SystemConfig(),
            ("localhost", 9999),
            None,
            self._servod,
        )

    def test_get_servo(self):
        """Test GetServo."""
        request = empty_pb2.Empty()
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.GetServo(request, None)
        self.assertEqual(response.servo_v4, "v4_serial")
        self.assertEqual(response.servo_micro, "micro_serial")
        self.assertEqual(response.ccd_serial, "ccd_serial")

    def test_set_servo(self):
        """Test SetServo."""
        request = SetServoRequest(
            servo_v4="v4_serial", servo_micro="micro_serial", ccd_serial="ccd_serial"
        )
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        servo_impl.SetServo(request, None)
        self.assertEqual(self._servod.servo_v4, "v4_serial")
        self.assertEqual(self._servod.servo_micro, "micro_serial")
        self.assertEqual(self._servod.ccd_serial, "ccd_serial")

    def test_get_version_same_root_and_main_devices(self):
        """Test GetVersion when root and main devices are the same."""
        request = empty_pb2.Empty()
        self._servod.get_root_device = unittest.mock.MagicMock(
            return_value=self._micro_dev
        )
        self._servod.get_main_device = unittest.mock.MagicMock(
            return_value=self._micro_dev
        )
        self._micro_dev.get_version = unittest.mock.MagicMock(return_value="version")
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.GetVersion(request, None)
        self.assertEqual(response.value, "version")

    def test_get_version_different_root_and_main_devices(self):
        """Test GetVersion when root and main devices are different."""
        request = empty_pb2.Empty()
        self._servod.get_root_device = unittest.mock.MagicMock(
            return_value=self._v4_dev
        )
        self._servod.get_main_device = unittest.mock.MagicMock(
            return_value=self._micro_dev
        )
        self._v4_dev.get_version = unittest.mock.MagicMock(return_value="v4_version")
        self._micro_dev.get_version = unittest.mock.MagicMock(
            return_value="micro_version"
        )
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.GetVersion(request, None)
        self.assertEqual(response.value, "v4_version\nmicro_version")

    def test_init_selected_controls(self):
        """Test InitSelectedControls."""
        request = ListRequest(list=["control1", "control2"])
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        servo_impl.InitSelectedControls(request, None)
        self.assertEqual(servo_impl._controls, ["control1", "control2"])

    def test_get_selected_controls(self):
        """Test GetSelectedControls."""
        request = empty_pb2.Empty()
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        servo_impl._controls = ["control1", "control2"]
        self._servod.get = unittest.mock.MagicMock(side_effect=["val1", "val2"])
        response_stream = servo_impl.GetSelectedControls(request, None)
        responses = list(response_stream)
        self.assertEqual(len(responses), 2)
        self.assertEqual(responses[0].cmd, "control1")
        self.assertEqual(responses[0].val, "val1")
        self.assertEqual(responses[1].cmd, "control2")
        self.assertEqual(responses[1].val, "val2")

    def test_set_selected_controls(self):
        """Test SetSelectedControls."""
        request_stream = [
            SetRequest(cmd="control1", val="val1"),
            SetRequest(cmd="control2", val="val2"),
        ]
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        self._servod.set = unittest.mock.MagicMock(return_value=True)
        response = servo_impl.SetSelectedControls(iter(request_stream), None)
        self.assertTrue(response.value)
        self._servod.set.assert_has_calls(
            [
                unittest.mock.call("control1", "val1"),
                unittest.mock.call("control2", "val2"),
            ]
        )

    def test_get_init_keyboard(self):
        """Test GetInitKeyboard."""
        request = empty_pb2.Empty()
        self._servod._keyboard = unittest.mock.MagicMock()
        self._servod._keyboard.handler = "handler"
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.GetInitKeyboard(request, None)
        self.assertEqual(response.value, "handler")

    def test_set_init_keyboard(self):
        """Test SetInitKeyboard."""
        request = SetKeyboard(value="handler")
        self._servod.set_keyboard = unittest.mock.MagicMock()
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.SetInitKeyboard(request, None)
        self.assertTrue(response.value)
        self._servod.set_keyboard.assert_called_once_with("handler")

    def test_get_init_v4_device(self):
        """Test GetInitV4Device."""
        request = V4DeviceRequest(device="default")
        v4_devices = {"v4_serial": self._v4_dev}
        self._servod.get_devices = unittest.mock.MagicMock(return_value=v4_devices)
        self._v4_dev.syscfg = unittest.mock.MagicMock()
        self._v4_dev.syscfg.get_v4_device_info = unittest.mock.MagicMock(
            return_value="v4_device"
        )
        self._servod.get_root_device = unittest.mock.MagicMock(
            return_value=self._v4_dev
        )
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.GetInitV4Device(request, None)
        self.assertEqual(response.value, "v4_device")
        self._v4_dev.syscfg.get_v4_device_info.assert_called_once_with("default")

        # Test when no v4 device is present
        self._servod.get_devices = unittest.mock.MagicMock(return_value={})
        self._servod.get_root_device = unittest.mock.MagicMock(return_value=None)
        response = servo_impl.GetInitV4Device(request, None)
        self.assertEqual(response.value, "No servo v4 present")

    def test_is_servo_has_attr(self):
        """Test IsServoHasAttr."""
        request = KeyRequest(key="attr")
        self._servod.has_attr = unittest.mock.MagicMock(return_value=True)
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.IsServoHasAttr(request, None)
        self.assertTrue(response.value)
        self._servod.has_attr.assert_called_once_with("attr")

    def test_get_serial(self):
        """Test GetSerial."""
        request = empty_pb2.Empty()
        self._servod.get_serial_number = unittest.mock.MagicMock(return_value="serial")
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.GetSerial(request, None)
        self.assertEqual(response.value, "serial")

    def test_get_serials(self):
        """Test GetSerials."""
        request = empty_pb2.Empty()
        self._servod.get_servo_serials = unittest.mock.MagicMock(
            return_value={"main": "serial"}
        )
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.GetSerials(request, None)
        self.assertEqual(response.value, '{"main": "serial"}')

    def test_get_all_controls(self):
        """Test GetAllControls."""
        request = empty_pb2.Empty()
        self._servod.get_controls = unittest.mock.MagicMock(
            return_value=["control1", "control2"]
        )
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response_stream = servo_impl.GetAllControls(request, None)
        responses = list(response_stream)
        self.assertEqual(len(responses), 2)
        self.assertEqual(responses[0].value, "control1")
        self.assertEqual(responses[1].value, "control2")

    def test_has_control(self):
        """Test HasControl."""
        request = KeyRequest(key="control")
        self._servod.has_control = unittest.mock.MagicMock(return_value=True)
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.HasControl(request, None)
        self.assertTrue(response.value)
        self._servod.has_control.assert_called_once_with("control")

        request = KeyRequest(key="param_control")
        self._servod.has_control.return_value = False
        self._servod.is_param_control = unittest.mock.MagicMock(return_value=True)
        response = servo_impl.HasControl(request, None)
        self.assertTrue(response.value)
        self._servod.is_param_control.assert_called_once_with("param_control")

    def test_get_init_usb_keyboard(self):
        """Test GetInitUsbKeyboard."""
        request = empty_pb2.Empty()
        self._servod._usbkm232 = "usbkm232"
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.GetInitUsbKeyboard(request, None)
        self.assertTrue(response.value)

        self._servod._usbkm232 = None
        response = servo_impl.GetInitUsbKeyboard(request, None)
        self.assertFalse(response.value)

    def test_set_init_usb_keyboard(self):
        """Test SetInitUsbKeyboard."""
        request = SetUsbRequest(value="usbkm232")
        self._servod.set_usbkm232 = unittest.mock.MagicMock(return_value=True)
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.SetInitUsbKeyboard(request, None)
        self.assertTrue(response.value)
        self._servod.set_usbkm232.assert_called_once_with("usbkm232")

    def test_get_file_config(self):
        """Test GetFileConfig."""
        request = empty_pb2.Empty()
        self._servod.get_display_config = unittest.mock.MagicMock(return_value="config")
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.GetFileConfig(request, None)
        self.assertEqual(response.value, "config")

    def test_get_devices(self):
        """Test GetDevices."""
        request = empty_pb2.Empty()
        devices = [self._micro_dev, self._v4_dev]
        self._servod.get_devices = unittest.mock.MagicMock(return_value=devices)
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response_stream = servo_impl.GetDevices(request, None)
        responses = list(response_stream)
        self.assertEqual(len(responses), 2)
        self.assertEqual(responses[0].vid, tmpl.get_vid("servo_micro"))
        self.assertEqual(responses[1].vid, tmpl.get_vid("servo_v4"))

    def test_get_tagged_controls(self):
        """Test GetTaggedControls."""
        request = KeyRequest(key="tag")
        self._servod.get_controls_for_tag = unittest.mock.MagicMock(
            return_value=["control1", "control2"]
        )
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response_stream = servo_impl.GetTaggedControls(request, None)
        responses = list(response_stream)
        self.assertEqual(len(responses), 2)
        self.assertEqual(responses[0].value, "control1")
        self.assertEqual(responses[1].value, "control2")

    def test_get_base_board(self):
        """Test GetBaseBoard."""
        request = empty_pb2.Empty()
        self._servod.get_base_board = unittest.mock.MagicMock(return_value="board")
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.GetBaseBoard(request, None)
        self.assertEqual(response.value, "board")

    def test_set_get_all(self):
        """Test SetGetAll."""
        request = SetRequest(cmd="control", val="val")
        self._servod.set_get_all = unittest.mock.MagicMock(return_value="result")
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.SetGetAll(request, None)
        self.assertEqual(response.value, "result")
        self._servod.set_get_all.assert_called_once_with("control", "val")

    def test_set_arb_key_config(self):
        """Test SetArbKeyConfig."""
        request = KeyboardRequest(key=1, press=True, duration=2)
        self._servod._keyboard = unittest.mock.MagicMock()
        self._servod._keyboard.set_id_key = unittest.mock.MagicMock()
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.SetArbKeyConfig(request, None)
        self.assertTrue(response.value)
        self._servod._keyboard.set_id_key.assert_called_once_with(1, True, 2)

    def test_set_arb_keys_config(self):
        """Test SetArbKeysConfig."""
        request = ListRequest(list=["1", "2"])
        self._servod._keyboard = unittest.mock.MagicMock()
        self._servod._keyboard.set_id_multi_key = unittest.mock.MagicMock()
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.SetArbKeysConfig(request, None)
        self.assertTrue(response.value)
        self._servod._keyboard.set_id_multi_key.assert_called_once_with(["1", "2"])

    def test_limit_ec_driver_channel(self):
        """Test LimitEcDriverChannel."""
        request = BoolRequest(value=True)
        self._servod._ec3po_driver = unittest.mock.MagicMock()
        self._servod._ec3po_driver.limit_channel = unittest.mock.MagicMock(
            return_value=True
        )
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.LimitEcDriverChannel(request, None)
        self.assertTrue(response.value)
        self._servod._ec3po_driver.limit_channel.assert_called_once_with(True)

    def test_issue_cmd_get_result(self):
        """Test IssueCmdGetResult."""
        request = IssueCmdOnMainDevRequest(command="cmd")
        self._servod.get_main_device = unittest.mock.MagicMock(
            return_value=self._micro_dev
        )
        self._micro_dev.drv = {"ec3po_driver": unittest.mock.MagicMock()}
        self._micro_dev.drv["ec3po_driver"].issue_cmd_get_results = (
            unittest.mock.MagicMock(return_value="result")
        )
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.IssueCmdGetResult(request, None)
        self.assertEqual(response.value, "result")
        self._micro_dev.drv[
            "ec3po_driver"
        ].issue_cmd_get_results.assert_called_once_with("cmd", [])

    def test_restore_ec_driver_channel(self):
        """Test RestoreEcDriverChannel."""
        request = empty_pb2.Empty()
        self._servod._ec3po_driver = unittest.mock.MagicMock()
        self._servod._ec3po_driver.restore_channel = unittest.mock.MagicMock(
            return_value=True
        )
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.RestoreEcDriverChannel(request, None)
        self.assertTrue(response.value)
        self._servod._ec3po_driver.restore_channel.assert_called_once()

    def test_get_watchdog(self):
        """Test GetWatchdog."""
        request = empty_pb2.Empty()
        self._servod.get_device_watchdog = unittest.mock.MagicMock(
            return_value=unittest.mock.MagicMock()
        )
        self._servod.get_device_watchdog.return_value.is_connected = (
            unittest.mock.MagicMock(return_value=True)
        )
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.GetWatchdog(request, None)
        self.assertTrue(response.value)

    def test_update_device_disconnect_ok(self):
        """Test UpdateDeviceDisconnectOk."""
        request = WatchdogRequest(value=True)
        self._servod.get_device_watchdog = unittest.mock.MagicMock(
            return_value=unittest.mock.MagicMock()
        )
        self._servod.get_device_watchdog.return_value.update_disconnect_ok = (
            unittest.mock.MagicMock()
        )
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.UpdateDeviceDisconnectOk(request, None)
        self.assertTrue(response.value)
        watchdog = self._servod.get_device_watchdog.return_value
        watchdog.update_disconnect_ok.assert_called_once_with(True)

    def test_get_ccd_state(self):
        """Test GetCcdState."""
        request = empty_pb2.Empty()
        self._servod.get_ccd_state = unittest.mock.MagicMock(return_value={})
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.GetCcdState(request, None)
        self.assertEqual(response.value, "{}")

    def test_get_cros_chip(self):
        """Test GetCrosChip."""
        request = empty_pb2.Empty()
        self._servod.get_cros_chip = unittest.mock.MagicMock(return_value="chip")
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.GetCrosChip(request, None)
        self.assertEqual(response.value, "chip")
