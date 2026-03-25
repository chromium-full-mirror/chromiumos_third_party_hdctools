# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import argparse
import json
import unittest
import unittest.mock
from unittest.mock import patch

from google.protobuf import empty_pb2
from google.protobuf import json_format
from google.protobuf import struct_pb2

from servo.common import servo_dev_templates as tmpl
from servo.common.proto.servo_dev_pb2 import BoolRequest
from servo.common.proto.servo_dev_pb2 import GetRequest
from servo.common.proto.servo_dev_pb2 import IssueCmdOnMainDevRequest
from servo.common.proto.servo_dev_pb2 import KeyboardRequest
from servo.common.proto.servo_dev_pb2 import KeyRequest
from servo.common.proto.servo_dev_pb2 import ListRequest
from servo.common.proto.servo_dev_pb2 import PrefixDeviceRequest
from servo.common.proto.servo_dev_pb2 import ServiceRequest
from servo.common.proto.servo_dev_pb2 import SetKeyboard
from servo.common.proto.servo_dev_pb2 import SetRequest
from servo.common.proto.servo_dev_pb2 import SetServoRequest
from servo.common.proto.servo_dev_pb2 import SetUsbRequest
from servo.common.proto.servo_dev_pb2 import V4DeviceRequest
from servo.common.proto.servo_dev_pb2 import WatchdogRequest
from servo.core import servo_dev
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

        # Mock GetServoInterfaces return value
        mock_client = self.mock_syscfg_grpc.SystemConfig.return_value
        mock_interfaces = unittest.mock.MagicMock()
        mock_interfaces.interface_list_json = json.dumps(["ftdi_gpio", "ftdi_i2c"])
        mock_client.GetServoInterfaces.return_value = mock_interfaces

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
            ("localhost", 9999),
            None,
            self._servod,
        )

    def test_get_servo(self):
        """Test GetServo."""
        request = GetRequest(control_name="control")
        self._servod.get = unittest.mock.MagicMock(return_value="val")
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.GetServo(request, None)
        self.assertEqual(response.response, "val")
        self._servod.get.assert_called_once_with("control")

    def test_set_servo(self):
        """Test SetServo."""
        val_pb = struct_pb2.Value()
        json_format.ParseDict("val", val_pb)
        request = SetServoRequest(control_name="control", value=val_pb)
        self._servod.set = unittest.mock.MagicMock()
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        servo_impl.SetServo(request, None)
        self._servod.set.assert_called_once_with("control", "val")

    def test_get_version_same_root_and_main_devices(self):
        """Test GetVersion when root and main devices are the same."""
        request = empty_pb2.Empty()
        self._servod._get_version = unittest.mock.MagicMock(return_value="version")
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.GetVersion(request, None)
        self.assertEqual(response.response, "version")

    def test_get_version_different_root_and_main_devices(self):
        """Test GetVersion when root and main devices are different."""
        request = empty_pb2.Empty()
        self._servod._get_version = unittest.mock.MagicMock(
            return_value="v4_version\nmicro_version"
        )
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.GetVersion(request, None)
        self.assertEqual(response.response, "v4_version\nmicro_version")

    def test_init_selected_controls(self):
        """Test InitSelectedControls."""
        request = empty_pb2.Empty()
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        servo_impl.InitSelectedControls(request, None)
        self.assertEqual(self._servod.selected_controls, {})

    def test_get_selected_controls(self):
        """Test GetSelectedControls."""
        request = empty_pb2.Empty()
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        self._servod.selected_controls = ["control1", "control2"]
        response = servo_impl.GetSelectedControls(request, None)
        self.assertEqual(response.response, json.dumps(["control1", "control2"]))

    def test_set_selected_controls(self):
        """Test SetSelectedControls."""
        val_pb = struct_pb2.Value()
        json_format.ParseDict("val1", val_pb)
        request = SetRequest(control_name="control1", control_value=val_pb)
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        self._servod.selected_controls = {}
        servo_impl.SetSelectedControls(request, None)
        self.assertEqual(self._servod.selected_controls["control1"], "val1")

    def test_get_init_keyboard(self):
        """Test GetInitKeyboard."""
        request = KeyboardRequest(type="handler")
        self._servod._keyboard = unittest.mock.MagicMock()
        self._servod._keyboard.is_open = unittest.mock.MagicMock(return_value=True)
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.GetInitKeyboard(request, None)
        self.assertEqual(response.open, 1)

    def test_set_init_keyboard(self):
        """Test SetInitKeyboard."""
        val_pb = struct_pb2.Value()
        json_format.ParseDict("handler", val_pb)
        request = SetKeyboard(handler_type="type", value=val_pb)
        with patch("servo.core.grpc_server.impl.servo_impl.set_keyboard") as mock_set:
            servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
            servo_impl.SetInitKeyboard(request, None)
            mock_set.assert_called_once_with(
                self.grpc_core_addr, self._servod, "type", "handler"
            )

    def test_get_init_v4_device(self):
        """Test GetInitV4Device."""
        request = V4DeviceRequest(info_type="default")
        self._servod.v4_device_info = {"default": "v4_device"}
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.GetInitV4Device(request, None)
        self.assertEqual(response.value, "v4_device")

    def test_is_servo_has_attr(self):
        """Test IsServoHasAttr."""
        request = ServiceRequest(name="attr")
        self._servod.attr = True
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.IsServoHasAttr(request, None)
        self.assertTrue(response.value)

    def test_get_serial(self):
        """Test GetSerial."""
        request = empty_pb2.Empty()
        self._servod.get_root_device = unittest.mock.MagicMock(
            return_value=self._micro_dev
        )
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.GetSerial(request, None)
        self.assertEqual(response.get_value, "servo_micro_serial")

    def test_get_serials(self):
        """Test GetSerials."""
        request = empty_pb2.Empty()
        self._servod.get_servo_serials = unittest.mock.MagicMock(
            return_value={"main": "serial"}
        )
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.GetSerials(request, None)
        self.assertEqual(response.get_value, '{"main": "serial"}')

    def test_get_all_controls(self):
        """Test GetAllControls."""
        request = empty_pb2.Empty()
        self._servod._controls = ["control1", "control2"]
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.GetAllControls(request, None)
        controls = json.loads(response.get_value)
        self.assertEqual(len(controls), 2)
        self.assertIn("control1", controls)
        self.assertIn("control2", controls)

    def test_has_control(self):
        """Test HasControl."""
        request = GetRequest(control_name="control")
        self._servod.has_control = unittest.mock.MagicMock(return_value=True)
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.HasControl(request, None)
        self.assertTrue(response.value)
        self._servod.has_control.assert_called_once_with("control")

    def test_get_init_usb_keyboard(self):
        """Test GetInitUsbKeyboard."""
        request = BoolRequest(value=True)
        self._servod._usb_keyboard = unittest.mock.MagicMock()
        self._servod._usb_keyboard.is_open = unittest.mock.MagicMock(return_value=True)
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.GetInitUsbKeyboard(request, None)
        self.assertEqual(response.open, 1)

    def test_set_init_usb_keyboard(self):
        """Test SetInitUsbKeyboard."""
        val_pb = struct_pb2.Value()
        json_format.ParseDict(1, val_pb)
        request = SetUsbRequest(is_legacy=True, value=val_pb)
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        servo_impl.set_init_usb_keyboard = unittest.mock.MagicMock()
        servo_impl.SetInitUsbKeyboard(request, None)
        servo_impl.set_init_usb_keyboard.assert_called_once_with(1, True)

    def test_get_file_config(self):
        """Test GetFileConfig."""
        request = empty_pb2.Empty()
        self._servod.get_config_files = unittest.mock.MagicMock(return_value=["config"])
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.GetFileConfig(request, None)
        self.assertEqual(
            response.response, json.dumps(["config"], sort_keys=True, indent=4)
        )

    def test_get_devices(self):
        """Test GetDevices."""
        request = empty_pb2.Empty()
        self._micro_dev.to_json = unittest.mock.MagicMock(return_value='{"vid": 1}')
        devices = [self._micro_dev]
        self._servod.get_devices = unittest.mock.MagicMock(return_value=devices)
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.GetDevices(request, None)
        self.assertEqual(response.response, json.dumps([{"vid": 1}], indent=4))

    def test_get_tagged_controls(self):
        """Test GetTaggedControls."""
        request = ServiceRequest(name=json.dumps({"tag": "tag"}))
        self._servod.get_controls_for_tag = unittest.mock.MagicMock(
            return_value=["control1", "control2"]
        )
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.GetTaggedControls(request, None)
        self.assertEqual(response.response, json.dumps(["control1", "control2"]))

    def test_get_base_board(self):
        """Test GetBaseBoard."""
        request = empty_pb2.Empty()
        self._servod.get_base_board = unittest.mock.MagicMock(return_value="board")
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.GetBaseBoard(request, None)
        self.assertEqual(response.response, "board")

    def test_set_get_all(self):
        """Test SetGetAll."""
        request = ListRequest(request_list=["control"])
        self._servod.set_get_all = unittest.mock.MagicMock(return_value=["result"])
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.SetGetAll(request, None)
        self.assertEqual(response.response_list, ["result"])
        self._servod.set_get_all.assert_called_once_with(["control"])

    def test_set_arb_key_config(self):
        """Test SetArbKeyConfig."""
        request = KeyRequest(key="1", handler="handler")
        mock_kb = unittest.mock.MagicMock()
        with patch(
            "servo.core.grpc_server.impl.servo_impl.get_keyboard", return_value=mock_kb
        ):
            servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
            servo_impl.SetArbKeyConfig(request, None)
            mock_kb.arb_key_config.assert_called_once_with("1")

    def test_set_arb_keys_config(self):
        """Test SetArbKeysConfig."""
        request = KeyRequest(key="1 2", handler="handler")
        mock_kb = unittest.mock.MagicMock()
        with patch(
            "servo.core.grpc_server.impl.servo_impl.get_keyboard", return_value=mock_kb
        ):
            servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
            servo_impl.SetArbKeysConfig(request, None)
            mock_kb.arb_keys_config.assert_called_once_with("1 2")

    def test_limit_ec_driver_channel(self):
        """Test LimitEcDriverChannel."""
        # Test fallback to main device
        request = PrefixDeviceRequest(prefix="")
        self._servod.get_main_device = unittest.mock.MagicMock(
            return_value=self._micro_dev
        )
        self._micro_dev.limit_ec_driver_channel = unittest.mock.MagicMock()
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        servo_impl.LimitEcDriverChannel(request, None)
        self._micro_dev.limit_ec_driver_channel.assert_called_once_with("ec_gpio")

        # Test explicit prefix routing
        request_with_prefix = PrefixDeviceRequest(prefix="my_dev")
        mock_specific_dev = unittest.mock.MagicMock()
        self._servod._devices = {"my_dev": mock_specific_dev}
        servo_impl.LimitEcDriverChannel(request_with_prefix, None)
        mock_specific_dev.limit_ec_driver_channel.assert_called_once_with("ec_gpio")

    def test_issue_cmd_get_result(self):
        """Test IssueCmdGetResult."""
        # Test fallback to main device
        request = IssueCmdOnMainDevRequest(
            cmds="cmd", regex_list=[], flush=True, time_out=10, prefix=""
        )
        self._servod.get_main_device = unittest.mock.MagicMock(
            return_value=self._micro_dev
        )
        self._micro_dev.issue_cmd_get_results = unittest.mock.MagicMock()
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        servo_impl.IssueCmdGetResult(request, None)
        self._micro_dev.issue_cmd_get_results.assert_called_once_with(
            "cmd", [], flush=True, timeout=10
        )

        # Test explicit prefix routing
        request_with_prefix = IssueCmdOnMainDevRequest(
            cmds="cmd2", regex_list=["ok"], flush=False, time_out=5, prefix="my_dev"
        )
        mock_specific_dev = unittest.mock.MagicMock()
        self._servod._devices = {"my_dev": mock_specific_dev}
        servo_impl.IssueCmdGetResult(request_with_prefix, None)
        mock_specific_dev.issue_cmd_get_results.assert_called_once_with(
            "cmd2", ["ok"], flush=False, timeout=5
        )

    def test_restore_ec_driver_channel(self):
        """Test RestoreEcDriverChannel."""
        # Test fallback to main device
        request = PrefixDeviceRequest(prefix="")
        self._servod.get_main_device = unittest.mock.MagicMock(
            return_value=self._micro_dev
        )
        self._micro_dev.restore_ec_driver_channel = unittest.mock.MagicMock()
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        servo_impl.RestoreEcDriverChannel(request, None)
        self._micro_dev.restore_ec_driver_channel.assert_called_once_with("ec_gpio")

        # Test explicit prefix routing
        request_with_prefix = PrefixDeviceRequest(prefix="my_dev")
        mock_specific_dev = unittest.mock.MagicMock()
        self._servod._devices = {"my_dev": mock_specific_dev}
        servo_impl.RestoreEcDriverChannel(request_with_prefix, None)
        mock_specific_dev.restore_ec_driver_channel.assert_called_once_with("ec_gpio")

    def test_get_watchdog(self):
        """Test GetWatchdog."""
        request = empty_pb2.Empty()
        self._servod.get_devices = unittest.mock.MagicMock(
            return_value=[self._micro_dev]
        )
        with patch(
            "servo.core.grpc_server.impl.servo_impl.get_device_state",
            return_value="state",
        ):
            servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
            response = servo_impl.GetWatchdog(request, None)
            self.assertEqual(response.response, "\nstate")

    def test_update_device_disconnect_ok(self):
        """Test UpdateDeviceDisconnectOk."""
        request = WatchdogRequest(name="micro", disconnect_ok=True)
        self._servod.get_servo_serials = unittest.mock.MagicMock(return_value={})
        self._servod.get_devices = unittest.mock.MagicMock(
            return_value=[self._micro_dev]
        )
        self._servod._devices = {"micro": self._micro_dev}
        self._micro_dev.set_disconnect_ok = unittest.mock.MagicMock()
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        servo_impl.UpdateDeviceDisconnectOk(request, None)
        self._micro_dev.set_disconnect_ok.assert_called_once_with(True)

    def test_update_device_disconnect_ok_by_type(self):
        """Test UpdateDeviceDisconnectOk by type (alias like 'ccd')."""
        request = WatchdogRequest(name="ccd", disconnect_ok=True)
        self._servod.get_servo_serials = unittest.mock.MagicMock(return_value={})
        self._servod.get_devices = unittest.mock.MagicMock(return_value=[self.ccd_cr50])
        self._servod.get_main_device = unittest.mock.MagicMock(
            return_value=self._v4_dev
        )
        self.ccd_cr50.template = unittest.mock.MagicMock()
        self.ccd_cr50.template.TYPE = "ccd_cr50"
        self._v4_dev.template = unittest.mock.MagicMock()
        self._v4_dev.template.TYPE = "servo_v4"
        self._servod._devices = {}
        self.ccd_cr50.set_disconnect_ok = unittest.mock.MagicMock()
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        servo_impl.UpdateDeviceDisconnectOk(request, None)
        self.ccd_cr50.set_disconnect_ok.assert_called_once_with(True)

    def test_get_ccd_state(self):
        """Test GetCcdState."""
        request = empty_pb2.Empty()
        mock_ccd = unittest.mock.MagicMock()
        mock_ccd.is_connected = unittest.mock.MagicMock(return_value=True)
        with patch(
            "servo.core.grpc_server.impl.servo_impl.get_device_from_type",
            return_value=mock_ccd,
        ):
            servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
            response = servo_impl.GetCcdState(request, None)
            self.assertEqual(response.state, 1)

    def test_get_cros_chip(self):
        """Test GetCrosChip."""
        request = ServiceRequest(name=json.dumps({"chip": "chip"}))
        self._servod.get_devices = unittest.mock.MagicMock(
            return_value=[self._micro_dev]
        )
        self._servod.get_main_device = unittest.mock.MagicMock(
            return_value=self._micro_dev
        )
        self._micro_dev.template = unittest.mock.MagicMock()
        self._micro_dev.template.TYPE = "micro"
        servo_impl = ServoImpl(self.grpc_core_addr, self._servod)
        response = servo_impl.GetCrosChip(request, None)
        self.assertEqual(response.response, "chip")
