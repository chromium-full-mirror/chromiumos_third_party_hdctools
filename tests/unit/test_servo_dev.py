# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import json
import unittest
import unittest.mock
from unittest.mock import patch

from servo.common import interface as _interface
from servo.common import servo_dev_templates as tmpl
from servo.core import servo_dev
from servo.core import servo_server
from servo.utils import servo_dev_hierarchy


class TestServoDevice(unittest.TestCase):
    """Test ServoDevice."""

    def setUp(self):
        """Set up for each test case."""
        unittest.TestCase.setUp(self)

        # Patch GrpcClient to avoid network calls and Side effects
        patcher = patch("servo.core.servo_dev.GrpcClient")
        self.mock_grpc_client = patcher.start()
        self.addCleanup(patcher.stop)

        # Also patch driver_grpc and system_config_grpc to avoid real client creation
        patcher_driver = patch("servo.core.servo_dev.driver_grpc")
        self.mock_driver_grpc = patcher_driver.start()
        # pylint: disable=line-too-long
        self.mock_driver_grpc.DriverService.return_value.CheckDevice.return_value.value = (
            False
        )
        self.addCleanup(patcher_driver.stop)

        patcher_syscfg = patch("servo.core.servo_dev.system_config_grpc")
        self.mock_syscfg_grpc = patcher_syscfg.start()
        self.addCleanup(patcher_syscfg.stop)

        # Mock GetServoInterfaces return value
        mock_interfaces_resp = unittest.mock.MagicMock()
        mock_interfaces_resp.interface_list_json = json.dumps(["ftdi_gpio", "ftdi_i2c"])
        get_servo_interfaces = (
            self.mock_syscfg_grpc.SystemConfig.return_value.GetServoInterfaces
        )
        get_servo_interfaces.return_value = mock_interfaces_resp

        self.servod = servo_server.Servod()

        self.micro_entry = servo_dev_hierarchy.ServoDeviceEntry(
            tmpl.get_vid("servo_micro"),
            tmpl.get_pid("servo_micro"),
            "servo_micro_serial",
            "/sys/bus/usb/devices/-2-1.2.3",
        )
        self.micro_entry.devopts = argparse.Namespace()
        self.micro_entry.devopts.prefix = ["micro"]
        self.micro_entry.devopts.board = "atlas"
        self.micro_entry.devopts.model = "default"
        self.micro_entry.devopts.token_db = "default"
        self.micro_dev = servo_dev.ServoDevice(
            self.micro_entry,
            ("localhost", 9999),
            None,
            self.servod,
        )
        self.v4_entry = servo_dev_hierarchy.ServoDeviceEntry(
            tmpl.get_vid("servo_v4"),
            tmpl.get_pid("servo_v4"),
            "servo_v4_serial",
            "/sys/bus/usb/devices/-2-1.2",
        )
        self.v4_entry.devopts = argparse.Namespace()
        self.v4_entry.devopts.prefix = ["v4"]
        self.v4_entry.devopts.board = "brya"
        self.v4_entry.devopts.model = "default"
        self.v4_entry.devopts.token_db = "default"
        self.v4_dev = servo_dev.ServoDevice(
            self.v4_entry,
            ("localhost", 9999),
            None,
            self.servod,
        )

    def test_init(self):
        """Test __init__()."""
        self.assertEqual(self.v4_dev.template, self.v4_entry.dev_template)
        self.assertEqual(self.v4_dev.prefixes, ["v4"])
        self.assertEqual(self.v4_dev._serial, "servo_v4_serial")
        self.assertEqual(self.v4_dev.board, "brya_default")
        self.assertEqual(self.v4_dev.base_board, "")
        self.assertEqual(self.v4_dev.model, "default")
        self.assertTrue(self.v4_dev._ifaces_available.is_set())
        self.assertEqual(self.v4_dev._reinit_attempts, self.v4_dev.REINIT_ATTEMPTS)
        self.assertFalse(self.v4_dev._reinit_capable)
        self.assertFalse(self.v4_dev._disconnect_ok)
        self.assertEqual(self.v4_dev._sysfs_path, "/sys/bus/usb/devices/-2-1.2")
        self.assertEqual(self.v4_dev.dev_entry, self.v4_entry)
        self.assertEqual(self.v4_entry.servo_device, self.v4_dev)
        self.assertFalse(self.v4_dev._manual_interfaces)
        self.assertEqual(
            self.v4_dev._interfaces,
            ["ftdi_gpio", "ftdi_i2c"],
        )
        self.assertEqual(self.v4_dev._servod, self.servod)

    def test_init_manual_interfaces(self):
        """Test __init__() with manual interfaces."""
        self.v4_dev = servo_dev.ServoDevice(
            self.v4_entry,
            ("localhost", 9999),
            [1],
            self.servod,
        )

        self.assertTrue(self.v4_dev._manual_interfaces)
        self.assertEqual(self.v4_dev._interfaces, [1])

    def test_repr(self):
        """Test __repr__()."""
        self.assertEqual(
            "%r" % self.micro_dev, "servo_micro (18d1:501a) servo_micro_serial"
        )
        self.assertEqual("%r" % self.v4_dev, "servo_v4 (18d1:501b) servo_v4_serial")

    def test_str(self):
        """Test __str__()."""
        self.assertEqual(
            "%s" % self.micro_dev, "servo_micro (18d1:501a) servo_micro_serial"
        )
        self.assertEqual("%s" % self.v4_dev, "servo_v4 (18d1:501b) servo_v4_serial")

    def test_wait(self):
        """Test wait()."""
        self.v4_dev._ifaces_available.wait = unittest.mock.MagicMock(return_value=True)
        self.v4_dev.wait(10)
        self.v4_dev._ifaces_available.wait.assert_called_once_with(10)

    def test_wait_error(self):
        """Test wait()."""
        self.v4_dev._ifaces_available.wait = unittest.mock.MagicMock(return_value=False)
        with self.assertRaisesRegex(
            servo_dev.ServoDeviceError,
            "Timed out waiting for interfaces to become available.",
        ):
            self.v4_dev.wait(10)
        self.v4_dev._ifaces_available.wait.assert_called_once_with(10)

    def test_connect(self):
        """Test connect()."""
        self.v4_dev._ifaces_available.set = unittest.mock.MagicMock()
        self.v4_dev.connect()

        self.v4_dev._ifaces_available.set.assert_called_once()
        self.assertEqual(self.v4_dev._reinit_attempts, self.v4_dev.REINIT_ATTEMPTS)

    def test_disconnect(self):
        """Test disconnect()."""
        self.v4_dev._ifaces_available.clear = unittest.mock.MagicMock()
        self.v4_dev._logger.debug = unittest.mock.MagicMock()
        self.v4_dev._disconnect_ok = True
        self.v4_dev.disconnect()

        self.v4_dev._ifaces_available.clear.assert_called_once()
        self.v4_dev._logger.debug.assert_not_called()
        self.assertEqual(self.v4_dev._reinit_attempts, self.v4_dev.REINIT_ATTEMPTS)

    def test_disconnect_not_ok(self):
        """Test disconnect() if _disconnect_ok if false."""
        self.v4_dev._ifaces_available.clear = unittest.mock.MagicMock()
        self.v4_dev._logger.debug = unittest.mock.MagicMock()
        self.v4_dev._disconnect_ok = False
        self.v4_dev.disconnect()

        self.v4_dev._ifaces_available.clear.assert_called_once()
        self.v4_dev._logger.debug.assert_called_once_with(
            "%d reinit attempts remaining.", 199
        )
        self.assertEqual(self.v4_dev._reinit_attempts, self.v4_dev.REINIT_ATTEMPTS - 1)

    def test_reinit_ok(self):
        """Test reinit_ok()."""
        self.v4_dev._reinit_capable = True
        self.v4_dev._reinit_attempts = 100
        self.assertTrue(self.v4_dev.reinit_ok())

        self.v4_dev._reinit_capable = False
        self.v4_dev._reinit_attempts = 100
        self.assertFalse(self.v4_dev.reinit_ok())

        self.v4_dev._reinit_capable = True
        self.v4_dev._reinit_attempts = 0
        self.assertFalse(self.v4_dev.reinit_ok())

        self.v4_dev._reinit_capable = False
        self.v4_dev._reinit_attempts = 0
        self.assertFalse(self.v4_dev.reinit_ok())

    def test_get_id(self):
        """Test get_id()."""
        self.assertEqual(
            self.v4_dev.get_id(),
            (tmpl.get_vid("servo_v4"), tmpl.get_pid("servo_v4"), "servo_v4_serial"),
        )
        self.assertEqual(
            self.micro_dev.get_id(),
            (
                tmpl.get_vid("servo_micro"),
                tmpl.get_pid("servo_micro"),
                "servo_micro_serial",
            ),
        )

    def test_is_connected(self):
        """Test is_connected()."""
        self.assertFalse(self.v4_dev.is_connected())
        self.assertFalse(self.micro_dev.is_connected())

    def test_get_prefixes(self):
        """Test get_prefixes()."""
        self.assertEqual(self.v4_dev.get_prefixes(), ["v4"])
        self.assertEqual(self.micro_dev.get_prefixes(), ["micro"])

    def test_add_prefix(self):
        """Test add_prefix()."""
        self.v4_dev.add_prefix("v4")
        self.assertEqual(self.v4_dev.get_prefixes(), ["v4"])

        self.v4_dev.add_prefix("v4-main")
        self.assertEqual(self.v4_dev.get_prefixes(), ["v4", "v4-main"])

        self.v4_dev.add_prefix("v4")
        self.assertEqual(self.v4_dev.get_prefixes(), ["v4", "v4-main"])

    def test_set_disconnect_ok(self):
        """Test set_disconnect_ok()."""
        self.v4_dev._disconnect_ok = False
        self.v4_dev._reinit_attempts = 0
        self.v4_dev.set_disconnect_ok(True)
        self.assertTrue(self.v4_dev._disconnect_ok)
        self.assertEqual(self.v4_dev._reinit_attempts, self.v4_dev.REINIT_ATTEMPTS)

        self.v4_dev._disconnect_ok = True
        self.v4_dev._reinit_attempts = 0
        self.v4_dev.set_disconnect_ok(False)
        self.assertFalse(self.v4_dev._disconnect_ok)
        self.assertEqual(self.v4_dev._reinit_attempts, self.v4_dev.REINIT_ATTEMPTS)

    def test_disconnect_is_ok(self):
        """Test disconnect_is_ok()."""
        self.v4_dev._disconnect_ok = True
        self.assertTrue(self.v4_dev.disconnect_is_ok())

        self.v4_dev._disconnect_ok = False
        self.assertFalse(self.v4_dev.disconnect_is_ok())

    @unittest.mock.patch(
        "servo.utils.usb_hierarchy.Hierarchy.dev_num_from_sysfs",
        unittest.mock.MagicMock(return_value="123"),
    )
    def test_usb_devnum(self):
        """Test usb_devnum()."""
        self.assertEqual(self.v4_dev.usb_devnum(), "123")

    def test_get_interface_list(self):
        """Test get_interface_list()."""
        self.assertEqual(self.v4_dev.get_interface_list(), self.v4_dev._interface_list)

    def test_init_servo_interfaces(self):
        """Test init_servo_interfaces()."""
        with patch.object(self.v4_dev, "_driver_client") as mock_driver_client:
            mock_init_interface_list = unittest.mock.MagicMock()
            mock_driver_client.InitInterface = mock_init_interface_list
            self.v4_dev.init_servo_interfaces()
            mock_init_interface_list.assert_called_once_with(
                vid=self.v4_dev.template.VID,
                pid=self.v4_dev.template.PID,
                serial=self.v4_dev._serial,
                interface_template=json.dumps(self.v4_dev._interfaces),
                fault_tolerant=False,
                token_db=self.v4_dev._token_db,
            )

    def test_init_servo_interfaces_resource_busy(self):
        """Test init_servo_interfaces() when device is busy."""
        with patch.object(self.v4_dev, "_driver_client") as mock_driver_client:
            mock_resp = unittest.mock.MagicMock()
            mock_resp.success = False
            mock_resp.loglines = [
                "2026-04-01 20:31:12,394 - root - ERROR - [Errno 16] Resource busy"
            ]
            mock_driver_client.InitInterface.return_value = mock_resp

            with self.assertRaisesRegex(
                servo_dev.ServoDeviceError,
                r"Resource busy\. Is another servod instance running\?",
            ):
                self.v4_dev.init_servo_interfaces()

    def test_init_servo_interfaces_no_such_device(self):
        """Test init_servo_interfaces() when device is missing."""
        with patch.object(self.v4_dev, "_driver_client") as mock_driver_client:
            mock_resp = unittest.mock.MagicMock()
            mock_resp.success = False
            mock_resp.loglines = ["USBError: [Errno 2] No such device"]
            mock_driver_client.InitInterface.return_value = mock_resp

            with self.assertRaisesRegex(
                servo_dev.ServoDeviceError,
                r"No such device\. Is the device still connected\?",
            ):
                self.v4_dev.init_servo_interfaces()

    def test_set_board_and_model(self):
        """Test set_board_and_model()."""
        v2_entry = servo_dev_hierarchy.ServoDeviceEntry(
            tmpl.get_vid("servo_v2"),
            tmpl.get_pid("servo_v2"),
            "servo_v2_serial",
            "/sys/bus/usb/devices/-2-1.2",
        )
        v2_entry.devopts = argparse.Namespace()
        v2_entry.devopts.prefix = ["v2"]
        v2_entry.devopts.board = "puff"
        v2_entry.devopts.model = "default"
        v2_entry.devopts.token_db = "default"
        v2_dev = servo_dev.ServoDevice(
            v2_entry,
            ("localhost", 9999),
            None,
            self.servod,
        )
        v2_dev._sync_interface_lists = unittest.mock.MagicMock()
        mock_board_model_resp = unittest.mock.MagicMock()
        mock_board_model_resp.board_config = "config"
        mock_board_model_resp.board_id = "board_id"
        v2_dev._system_config_client.GetBoardModelConfig.return_value = (
            mock_board_model_resp
        )

        # Simulate different interfaces for "atlas"
        def side_effect(board, **_kwargs):
            if board == "atlas":
                mock = unittest.mock.MagicMock()
                mock.interface_list_json = json.dumps(["new_interface"])
                return mock
            mock = unittest.mock.MagicMock()
            mock.interface_list_json = json.dumps(["ftdi_gpio", "ftdi_i2c"])
            return mock

        v2_dev._system_config_client.GetServoInterfaces.side_effect = side_effect

        with patch.object(v2_dev, "_driver_client") as mock_driver_client:
            mock_driver_client.ResetInterface = unittest.mock.MagicMock()
            v2_dev._system_config_client.AddCfgFile = unittest.mock.MagicMock()
            v2_dev._system_config_client.AddCfgFile.return_value = (
                unittest.mock.MagicMock(systemConfig=[])
            )
            res = v2_dev.set_board_and_model("atlas", "default")

            self.assertTrue(res)
            v2_dev._sync_interface_lists.assert_called_once()
            v2_dev._system_config_client.GetBoardModelConfig.assert_called_once()
            v2_dev._system_config_client.AddCfgFile.assert_called_once()

    def test_set_board_and_model_keyerror(self):
        """Test set_board_and_model()."""
        self.v4_dev._sync_interface_lists = unittest.mock.MagicMock()
        mock_board_model_resp = unittest.mock.MagicMock()
        mock_board_model_resp.board_config = "config"
        mock_board_model_resp.board_id = "board_id"
        self.v4_dev._system_config_client.GetBoardModelConfig.return_value = (
            mock_board_model_resp
        )
        self.v4_dev._system_config_client.AddCfgFile = unittest.mock.MagicMock()
        self.v4_dev._system_config_client.AddCfgFile.return_value = (
            unittest.mock.MagicMock(systemConfig=[])
        )
        self.v4_dev._manual_interfaces = False

        res = self.v4_dev.set_board_and_model("atlas", "default")

        self.assertTrue(res)
        self.v4_dev._sync_interface_lists.assert_not_called()
        self.v4_dev._system_config_client.AddCfgFile.assert_called_once()
        unused_args, kwargs = self.v4_dev._system_config_client.AddCfgFile.call_args
        self.assertEqual(kwargs["prefix"], "v4")
        self.assertEqual(kwargs["filename"], "config")

    def test_set_board_and_model_no_config(self):
        """Test set_board_and_model()."""
        self.v4_dev._sync_interface_lists = unittest.mock.MagicMock()
        mock_board_model_resp = unittest.mock.MagicMock()
        mock_board_model_resp.board_config = ""
        mock_board_model_resp.board_id = "board_id"
        self.v4_dev._system_config_client.GetBoardModelConfig.return_value = (
            mock_board_model_resp
        )
        self.v4_dev._system_config_client.AddCfgFile = unittest.mock.MagicMock()
        self.v4_dev._manual_interfaces = False

        res = self.v4_dev.set_board_and_model("atlas", "default")

        self.assertFalse(res)
        self.v4_dev._sync_interface_lists.assert_not_called()
        self.v4_dev._system_config_client.AddCfgFile.assert_not_called()

    def test_sync_interface_lists(self):
        """Test _sync_interface_lists()."""
        with patch.object(self.v4_dev, "_driver_client") as mock_driver_client:
            mock_sync_interface_list = unittest.mock.MagicMock()
            mock_driver_client.SyncInterfaceList = mock_sync_interface_list
            self.v4_dev._sync_interface_lists()
            mock_sync_interface_list.assert_called_once_with(
                vid=self.v4_dev.template.VID,
                pid=self.v4_dev.template.PID,
                serial=self.v4_dev._serial,
                interface_template=json.dumps(self.v4_dev._interfaces),
                fault_tolerant=False,
            )

    def test_set_base_board(self):
        """Test set_base_board()."""
        self.v4_dev.set_base_board("grunt")
        self.assertEqual(self.v4_dev.base_board, "grunt")

    def test_reinitialize(self):
        """Test reinitialize()."""
        with patch.object(self.v4_dev, "_driver_client") as mock_driver_client:
            self.v4_dev.connect = unittest.mock.MagicMock()
            mock_reinitialize_interface = unittest.mock.MagicMock()
            mock_driver_client.ReinitializeInterfaces = mock_reinitialize_interface
            self.v4_dev.reinitialize()
            mock_reinitialize_interface.assert_called_once()
            self.v4_dev.connect.assert_called_once()

    def test_close(self):
        """Test close()."""
        with patch.object(self.v4_dev, "_driver_client") as mock_driver_client:
            mock_close_interface = unittest.mock.MagicMock()
            mock_driver_client.CloseInterface = mock_close_interface
            self.v4_dev.close()
            mock_close_interface.assert_called_once_with(
                vid=self.v4_dev.template.VID,
                pid=self.v4_dev.template.PID,
                serial=self.v4_dev._serial,
                timeout=0.5,
            )

    def test_clear_cached_drv(self):
        """Test clear_cached_drv()."""
        self.v4_dev._drv_dict = {1: 2}
        self.v4_dev.clear_cached_drv()
        self.assertEqual(self.v4_dev._drv_dict, {})

    def test_doc_all(self):
        """Test doc_all()."""
        mock_display_config_resp = unittest.mock.MagicMock()
        mock_display_config_resp.display_config = "displayconfig"
        self.v4_dev._system_config_client.GetDisplayConfig.return_value = (
            mock_display_config_resp
        )
        self.assertEqual(self.v4_dev.doc_all(), "displayconfig")

    def test_doc(self):
        """Test doc()."""
        self.v4_dev._logger.debug = unittest.mock.MagicMock()
        mock_is_control_resp = unittest.mock.MagicMock()
        mock_is_control_resp.value = True
        self.v4_dev._system_config_client.IsControl.return_value = mock_is_control_resp
        mock_doc_resp = unittest.mock.MagicMock()
        mock_doc_resp.doc = "controldoc"
        self.v4_dev._system_config_client.GetControlDoc.return_value = mock_doc_resp

        self.assertEqual(self.v4_dev.doc("control"), "controldoc")
        self.v4_dev._logger.debug.assert_called_once_with("name(%s)", "control")

    def test_doc_error(self):
        """Test doc() in case of error."""
        self.v4_dev._logger.debug = unittest.mock.MagicMock()
        mock_is_control_resp = unittest.mock.MagicMock()
        mock_is_control_resp.value = False
        self.v4_dev._system_config_client.IsControl.return_value = mock_is_control_resp

        with self.assertRaisesRegex(NameError, "No control ctrl"):
            self.v4_dev.doc("ctrl")
        self.v4_dev._logger.debug.assert_called_once_with("name(%s)", "ctrl")

    def test_hwinit(self):
        """Test hwinit()."""
        self.v4_dev._logger.debug = unittest.mock.MagicMock()
        self.v4_dev._logger.info = unittest.mock.MagicMock()
        self.v4_dev._logger.error = unittest.mock.MagicMock()
        mock_init_controls_resp = unittest.mock.MagicMock()
        mock_init_controls_resp.hwinit_json = json.dumps(
            [
                ("control1", "value1"),
                ("control2", "value2"),
                ("control3", "value3"),
            ]
        )
        self.v4_dev._system_config_client.GetInitControls.return_value = (
            mock_init_controls_resp
        )
        self.v4_dev.get = unittest.mock.MagicMock(side_effect=["value2", "not-value3"])
        self.v4_dev.set = unittest.mock.MagicMock()

        self.v4_dev.hwinit(True, ["control1"])

        self.v4_dev._logger.debug.assert_any_call(
            "Skip initializing control %r because it is already initialized "
            "for a child device.",
            "control1",
        )
        self.v4_dev.get.assert_has_calls(
            [unittest.mock.call("control2"), unittest.mock.call("control3")]
        )
        self.v4_dev.set.assert_any_call("control3", "value3")
        self.v4_dev._logger.info.assert_has_calls(
            [
                unittest.mock.call("Initializing %s to %s", "control2", "value2"),
                unittest.mock.call("Initializing %s to %s", "control3", "value3"),
            ]
        )
        self.v4_dev._logger.error.assert_not_called()

    def test_hwinit_error(self):
        """Test hwinit() in case of error."""
        self.v4_dev._logger.debug = unittest.mock.MagicMock()
        self.v4_dev._logger.info = unittest.mock.MagicMock()
        self.v4_dev._logger.error = unittest.mock.MagicMock()
        mock_init_controls_resp = unittest.mock.MagicMock()
        mock_init_controls_resp.hwinit_json = json.dumps(
            [
                ("control1", "value1"),
                ("control2", "value2"),
                ("control3", "value3"),
            ]
        )
        self.v4_dev._system_config_client.GetInitControls.return_value = (
            mock_init_controls_resp
        )
        self.v4_dev.get = unittest.mock.MagicMock(
            side_effect=["value2", ValueError("valueerror")]
        )
        self.v4_dev.set = unittest.mock.MagicMock()

        self.v4_dev.hwinit(True, ["control1"])

        self.v4_dev._logger.debug.assert_any_call(
            "Skip initializing control %r because it is already initialized "
            "for a child device.",
            "control1",
        )
        self.v4_dev.get.assert_has_calls(
            [unittest.mock.call("control2"), unittest.mock.call("control3")]
        )
        self.v4_dev.set.assert_called_once_with("active_dut_controller", "default")
        self.v4_dev._logger.info.assert_has_calls(
            [
                unittest.mock.call("Initializing %s to %s", "control2", "value2"),
                unittest.mock.call("Initializing %s to %s", "control3", "value3"),
            ]
        )
        self.v4_dev._logger.error.assert_has_calls(
            [
                unittest.mock.call(
                    "Problem initializing %s -> %s", "control3", "value3"
                ),
                unittest.mock.call("valueerror"),
                unittest.mock.call(
                    "Please consider verifying the logs and if the "
                    "error is not just a setup issue, consider filing "
                    "a bug. Also checkout go/servo-ki."
                ),
            ]
        )

    def test_get_root_hub_device(self):
        """Test get_root_hub_device()."""
        self.micro_entry.cluster_root = None
        self.assertIsNone(self.micro_dev.get_root_hub_device())

        self.micro_entry.cluster_root = self.v4_entry
        self.assertEqual(self.micro_dev.get_root_hub_device(), self.v4_dev)

    def test_is_root_hub_device(self):
        """Test is_root_hub_device()."""
        self.v4_entry.is_cluster_root = unittest.mock.MagicMock(return_value=False)
        self.assertFalse(self.v4_dev.is_root_hub_device())

        self.v4_entry.is_cluster_root = unittest.mock.MagicMock(return_value=True)
        self.assertTrue(self.v4_dev.is_root_hub_device())

    def test_get_child_devices(self):
        """Test get_child_devices()."""
        self.v4_dev.is_root_hub_device = unittest.mock.MagicMock(return_value=False)
        self.assertEqual(self.v4_dev.get_child_devices(), [])

        self.v4_dev.is_root_hub_device = unittest.mock.MagicMock(return_value=True)
        self.v4_entry.cluster_members = {self.v4_entry, self.micro_entry}
        self.assertTrue(self.v4_dev.get_child_devices(), [self.micro_dev])

    def test_to_json(self):
        """Test to_json()."""
        v4_json = json.loads(self.v4_dev.to_json())
        self.assertEqual(v4_json["prefix"], ["v4"])
        self.assertEqual(v4_json["type"], "servo_v4")
        self.assertEqual(v4_json["vendor_id"], tmpl.get_vid("servo_v4"))
        self.assertEqual(v4_json["product_id"], tmpl.get_pid("servo_v4"))
        self.assertEqual(v4_json["serial"], "servo_v4_serial")
        self.assertEqual(v4_json["sysfs_path"], "/sys/bus/usb/devices/-2-1.2")
        self.assertEqual(v4_json["root_hub_device"], None)
        self.assertEqual(v4_json["child_devices"], [])

        micro_json = json.loads(self.micro_dev.to_json())
        self.assertEqual(micro_json["prefix"], ["micro"])
        self.assertEqual(micro_json["type"], "servo_micro")
        self.assertEqual(micro_json["vendor_id"], tmpl.get_vid("servo_micro"))
        self.assertEqual(micro_json["product_id"], tmpl.get_pid("servo_micro"))
        self.assertEqual(micro_json["serial"], "servo_micro_serial")
        self.assertEqual(micro_json["sysfs_path"], "/sys/bus/usb/devices/-2-1.2.3")
        self.assertEqual(micro_json["root_hub_device"], None)
        self.assertEqual(micro_json["child_devices"], [])


if __name__ == "__main__":
    unittest.main()
