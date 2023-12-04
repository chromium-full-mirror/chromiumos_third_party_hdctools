# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import json
import unittest
import unittest.mock

from servo import servo_dev
from servo import servo_dev_templates as tmpl
from servo import servo_interfaces
from servo import servo_server
from servo.common import interface as _interface
from servo.common.config import system_config
from servo.data.drv import na
from servo.utils import servo_dev_hierarchy


class TestServoDevice(unittest.TestCase):
    """Test ServoDevice."""

    def setUp(self):
        """Set up for each test case."""
        unittest.TestCase.setUp(self)
        self.servod = servo_server.Servod()
        self.micro_entry = servo_dev_hierarchy.ServoDeviceEntry(
            tmpl.GetVID("servo_micro"),
            tmpl.GetPID("servo_micro"),
            "servo_micro_serial",
            "/sys/bus/usb/devices/-2-1.2.3",
        )
        self.micro_entry.devopts = argparse.Namespace()
        self.micro_entry.devopts.prefix = ["micro"]
        self.micro_entry.devopts.board = "atlas"
        self.micro_entry.devopts.model = "default"
        self.micro_dev = servo_dev.ServoDevice(
            self.micro_entry, system_config.SystemConfig(), None, self.servod
        )
        self.v4_entry = servo_dev_hierarchy.ServoDeviceEntry(
            tmpl.GetVID("servo_v4"),
            tmpl.GetPID("servo_v4"),
            "servo_v4_serial",
            "/sys/bus/usb/devices/-2-1.2",
        )
        self.v4_entry.devopts = argparse.Namespace()
        self.v4_entry.devopts.prefix = ["v4"]
        self.v4_entry.devopts.board = "brya"
        self.v4_entry.devopts.model = "default"
        self.v4_dev = servo_dev.ServoDevice(
            self.v4_entry, system_config.SystemConfig(), None, self.servod
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
        self.assertTrue(isinstance(self.v4_dev.syscfg, system_config.SystemConfig))
        self.assertFalse(self.v4_dev._manual_interfaces)
        self.assertEqual(
            self.v4_dev._interfaces,
            servo_interfaces.INTERFACE_DEFAULTS[tmpl.GetVID("servo_v4")][
                tmpl.GetPID("servo_v4")
            ],
        )
        self.assertEqual(len(self.v4_dev._interface_list), len(self.v4_dev._interfaces))
        for interface in self.v4_dev._interface_list:
            self.assertTrue(isinstance(interface, _interface.empty.Empty))
        self.assertEqual(
            self.v4_dev._interface_init, [False] * len(self.v4_dev._interfaces)
        )
        self.assertEqual(self.v4_dev._servod, self.servod)

    def test_init_manual_interfaces(self):
        """Test __init__() with manual interfaces."""
        self.v4_dev = servo_dev.ServoDevice(
            self.v4_entry, system_config.SystemConfig(), [1], self.servod
        )

        self.assertTrue(self.v4_dev._manual_interfaces)
        self.assertEqual(self.v4_dev._interfaces, [1])
        self.assertEqual(len(self.v4_dev._interface_list), 1)
        self.assertTrue(
            isinstance(self.v4_dev._interface_list[0], _interface.empty.Empty)
        )
        self.assertEqual(self.v4_dev._interface_init, [False])

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
            "%d reinit attempts remaining.", 99
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
            (tmpl.GetVID("servo_v4"), tmpl.GetPID("servo_v4"), "servo_v4_serial"),
        )
        self.assertEqual(
            self.micro_dev.get_id(),
            (
                tmpl.GetVID("servo_micro"),
                tmpl.GetPID("servo_micro"),
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
        "servo.utils.usb_hierarchy.Hierarchy.DevNumFromSysfs",
        unittest.mock.MagicMock(return_value="123"),
    )
    def test_usb_devnum(self):
        """Test usb_devnum()."""
        self.assertEqual(self.v4_dev.usb_devnum(), "123")

    def test_get_interface_list(self):
        """Test get_interface_list()."""
        self.assertEqual(self.v4_dev.get_interface_list(), self.v4_dev._interface_list)

    @unittest.mock.patch(
        "servo.common.interface.Build", unittest.mock.MagicMock(return_value=None)
    )
    def test_init_servo_interfaces(self):
        """Test init_servo_interfaces()."""
        self.v4_dev.init_servo_interfaces()
        for i, interface in enumerate(self.v4_dev._interface_list):
            if i not in [22, 23, 24, 25, 26]:
                self.assertTrue(isinstance(interface, _interface.empty.Empty))
                self.assertFalse(self.v4_dev._interface_init[i])
            else:
                self.assertIsNone(interface)
                self.assertTrue(self.v4_dev._interface_init[i])

        self.micro_dev.init_servo_interfaces()
        for i, interface in enumerate(self.micro_dev._interface_list):
            if i not in [1, 2, 3, 6, 7, 8, 9, 10, 11]:
                self.assertTrue(isinstance(interface, _interface.empty.Empty))
                self.assertFalse(self.micro_dev._interface_init[i])
            else:
                self.assertIsNone(interface)
                self.assertTrue(self.micro_dev._interface_init[i])

    @unittest.mock.patch(
        "servo.common.interface.Build", unittest.mock.MagicMock(return_value=None)
    )
    def test_init_servo_interfaces_error(self):
        """Test init_servo_interfaces()."""
        self.v4_dev._interfaces = self.v4_dev._interfaces.copy()
        self.v4_dev._interfaces[26] = 2
        with self.assertRaisesRegex(
            servo_dev.ServoDeviceError, "Illegal interface data type"
        ):
            self.v4_dev.init_servo_interfaces()
        for i, interface in enumerate(self.v4_dev._interface_list):
            if i not in [22, 23, 24, 25]:
                self.assertTrue(isinstance(interface, _interface.empty.Empty))
                self.assertFalse(self.v4_dev._interface_init[i])
            else:
                self.assertIsNone(interface)
                self.assertTrue(self.v4_dev._interface_init[i])

    @unittest.mock.patch(
        "servo.common.interface.Build",
        unittest.mock.MagicMock(side_effect=ValueError("valueerr")),
    )
    def test_init_servo_interfaces_fault_tolerant(self):
        """Test init_servo_interfaces()."""
        self.v4_dev.init_servo_interfaces(fault_tolerant=True)
        for i, interface in enumerate(self.v4_dev._interface_list):
            self.assertTrue(isinstance(interface, _interface.empty.Empty))
            self.assertFalse(self.v4_dev._interface_init[i])

    def test_set_board_and_model(self):
        """Test set_board_and_model()."""
        v2_entry = servo_dev_hierarchy.ServoDeviceEntry(
            tmpl.GetVID("servo_v2"),
            tmpl.GetPID("servo_v2"),
            "servo_v2_serial",
            "/sys/bus/usb/devices/-2-1.2",
        )
        v2_entry.devopts = argparse.Namespace()
        v2_entry.devopts.prefix = ["v2"]
        v2_entry.devopts.board = "puff"
        v2_entry.devopts.model = "default"
        v2_dev = servo_dev.ServoDevice(
            v2_entry, system_config.SystemConfig(), None, self.servod
        )
        v2_dev._sync_interface_lists = unittest.mock.MagicMock()
        v2_dev.syscfg.get_board_model_config = unittest.mock.MagicMock(
            return_value=("config", "board_id")
        )
        v2_dev.syscfg.set_board_cfg = unittest.mock.MagicMock()
        v2_dev.syscfg.add_cfg_file = unittest.mock.MagicMock()
        v2_dev._manual_interfaces = False

        res = v2_dev.set_board_and_model("atlas", "default")

        self.assertTrue(res)
        v2_dev._sync_interface_lists.assert_called_once()
        v2_dev.syscfg.get_board_model_config.assert_called_once_with("atlas", "default")
        v2_dev.syscfg.set_board_cfg.assert_called_once_with("config")
        v2_dev.syscfg.add_cfg_file.assert_called_once_with("v2", "config")

    def test_set_board_and_model_keyerror(self):
        """Test set_board_and_model()."""
        self.v4_dev._sync_interface_lists = unittest.mock.MagicMock()
        self.v4_dev.syscfg.get_board_model_config = unittest.mock.MagicMock(
            return_value=("config", "board_id")
        )
        self.v4_dev.syscfg.set_board_cfg = unittest.mock.MagicMock()
        self.v4_dev.syscfg.add_cfg_file = unittest.mock.MagicMock()
        self.v4_dev._manual_interfaces = False

        res = self.v4_dev.set_board_and_model("atlas", "default")

        self.assertTrue(res)
        self.v4_dev._sync_interface_lists.assert_not_called()
        self.v4_dev.syscfg.get_board_model_config.assert_called_once_with(
            "atlas", "default"
        )
        self.v4_dev.syscfg.set_board_cfg.assert_called_once_with("config")
        self.v4_dev.syscfg.add_cfg_file.assert_called_once_with("v4", "config")

    def test_set_board_and_model_no_config(self):
        """Test set_board_and_model()."""
        self.v4_dev._sync_interface_lists = unittest.mock.MagicMock()
        self.v4_dev.syscfg.get_board_model_config = unittest.mock.MagicMock(
            return_value=(None, "board_id")
        )
        self.v4_dev.syscfg.set_board_cfg = unittest.mock.MagicMock()
        self.v4_dev.syscfg.add_cfg_file = unittest.mock.MagicMock()
        self.v4_dev._manual_interfaces = False

        res = self.v4_dev.set_board_and_model("atlas", "default")

        self.assertFalse(res)
        self.v4_dev._sync_interface_lists.assert_not_called()
        self.v4_dev.syscfg.get_board_model_config.assert_called_once_with(
            "atlas", "default"
        )
        self.v4_dev.syscfg.set_board_cfg.assert_not_called()
        self.v4_dev.syscfg.add_cfg_file.assert_not_called()

    def test_sync_interface_lists(self):
        """Test _sync_interface_lists()."""
        self.v4_dev._interfaces = [True] * 68
        self.v4_dev._interface_list = []
        self.v4_dev._interface_init = []

        self.v4_dev._sync_interface_lists()

        self.assertEqual(len(self.v4_dev._interface_list), len(self.v4_dev._interfaces))
        for interface in self.v4_dev._interface_list:
            self.assertTrue(isinstance(interface, _interface.empty.Empty))
        self.assertEqual(
            self.v4_dev._interface_init, [False] * len(self.v4_dev._interfaces)
        )

    def test_set_base_board(self):
        """Test set_base_board()."""
        self.v4_dev.set_base_board("grunt")
        self.assertEqual(self.v4_dev.base_board, "grunt")

    @unittest.mock.patch(
        "servo.common.interface.interface.Interface.reinitialize",
        unittest.mock.MagicMock(),
    )
    def test_reinitialize(self):
        """Test reinitialize()."""
        self.v4_dev.connect = unittest.mock.MagicMock()
        self.v4_dev.reinitialize()

        self.assertEqual(
            _interface.interface.Interface.reinitialize.call_count,
            len(self.v4_dev._interface_list),
        )
        self.v4_dev.connect.assert_called_once()

    @unittest.mock.patch(
        "servo.common.interface.ec3po_interface.EC3PO.Build",
        unittest.mock.MagicMock(
            return_value=unittest.mock.MagicMock(spec=_interface.ec3po_interface.EC3PO)
        ),
    )
    @unittest.mock.patch(
        "servo.common.interface.stm32uart.Suart.Build",
        unittest.mock.MagicMock(
            return_value=unittest.mock.MagicMock(spec=_interface.stm32uart.Suart)
        ),
    )
    @unittest.mock.patch(
        "servo.common.interface.ec3po_interface.EC3PO.close", unittest.mock.MagicMock()
    )
    @unittest.mock.patch(
        "servo.common.interface.stm32uart.Suart.close", unittest.mock.MagicMock()
    )
    def test_close(self):
        """Test close()."""
        self.v4_dev._interface_list = [
            _interface.ec3po_interface.EC3PO.Build(),
            _interface.stm32uart.Suart.Build(),
            _interface.empty.Empty.Build(),
            _interface.ec3po_interface.EC3PO.Build(),
        ]
        self.v4_dev._logger.info = unittest.mock.MagicMock()

        self.v4_dev.close()

        self.v4_dev._logger.info.assert_has_calls(
            [
                unittest.mock.call("Turning down interface %d", 0),
                unittest.mock.call("Turning down interface %d", 3),
                unittest.mock.call("Turning down interface %d", 1),
            ]
        )

    def test_get(self):
        """Test get()."""
        na_drv = unittest.mock.MagicMock(spec=na.na)
        self.v4_dev._get_param_drv = unittest.mock.MagicMock(
            return_value=({}, na_drv, self.v4_dev)
        )
        self.v4_dev.wait = unittest.mock.MagicMock()
        na_drv.get = unittest.mock.MagicMock(return_value="return_value")
        self.v4_dev.syscfg.reformat_val = unittest.mock.MagicMock(
            return_value="reformatted_return_value"
        )

        self.assertEqual(self.v4_dev.get("cold_reset"), "reformatted_return_value")

    def test_set(self):
        """Test set()."""
        na_drv = unittest.mock.MagicMock(spec=na.na)
        self.v4_dev._get_param_drv = unittest.mock.MagicMock(
            return_value=({}, na_drv, self.v4_dev)
        )
        self.v4_dev.wait = unittest.mock.MagicMock()
        self.v4_dev.syscfg.resolve_val = unittest.mock.MagicMock(
            return_value="reformatted_set_value"
        )
        na_drv.set = unittest.mock.MagicMock()

        self.assertTrue(self.v4_dev.set("cold_reset", "on"))

    def test_get_param_drv_get_cache(self):
        """Test _get_param_drv()."""
        self.v4_dev._drv_dict["cold_reset"] = {"get": ["testing"]}
        self.assertEqual(self.v4_dev._get_param_drv("cold_reset", True), ["testing"])

    def test_get_param_drv_set_cache(self):
        """Test _get_param_drv()."""
        self.v4_dev._drv_dict["cold_reset"] = {"set": ["testing"]}
        self.assertEqual(self.v4_dev._get_param_drv("cold_reset", False), ["testing"])

    @unittest.mock.patch(
        "servo.data.drv.cr50.cr50.__init__", unittest.mock.MagicMock(return_value=None)
    )
    @unittest.mock.patch(
        "servo.data.drv.cr50.cr50.set_complement", unittest.mock.MagicMock()
    )
    def test_get_param_drv_get_no_cache(self):
        """Test _get_param_drv()."""
        get_params = {
            "cmd": "get",
            "uart_cmd": "ecrst",
            "regex": "EC_RST_L is (asserted|deasserted)",
            "group": "1",
            "interface": "9",
            "drv": "cr50",
            "map": "asserted_re",
            "clobber_ok": "",
        }
        set_params = {
            "cmd": "set",
            "subtype": "cold_reset",
            "interface": "9",
            "drv": "cr50",
            "map": "onoff_i",
            "clobber_ok": "",
        }
        map_params = {"deasserted", "asserted"}
        self.v4_dev.syscfg.lookup_control_params = unittest.mock.MagicMock(
            return_value=(set_params, get_params)
        )
        self.v4_dev.syscfg.lookup_map_params = unittest.mock.MagicMock(
            return_value=(map_params)
        )
        self.assertEqual(self.v4_dev._get_param_drv("cold_reset", True)[0], get_params)

    @unittest.mock.patch(
        "servo.data.drv.cr50.cr50.__init__", unittest.mock.MagicMock(return_value=None)
    )
    @unittest.mock.patch(
        "servo.data.drv.cr50.cr50.set_complement", unittest.mock.MagicMock()
    )
    def test_get_param_drv_set_no_cache(self):
        """Test _get_param_drv()."""
        get_params = {
            "cmd": "get",
            "uart_cmd": "ecrst",
            "regex": "EC_RST_L is (asserted|deasserted)",
            "group": "1",
            "interface": "9",
            "drv": "cr50",
            "map": "asserted_re",
            "clobber_ok": "",
        }
        set_params = {
            "cmd": "set",
            "subtype": "cold_reset",
            "interface": "9",
            "drv": "cr50",
            "map": "onoff_i",
            "clobber_ok": "",
        }
        map_params = {"0", "1"}
        self.v4_dev.syscfg.lookup_control_params = unittest.mock.MagicMock(
            return_value=(set_params, get_params)
        )
        self.v4_dev.syscfg.lookup_map_params = unittest.mock.MagicMock(
            return_value=(map_params)
        )
        self.assertEqual(self.v4_dev._get_param_drv("cold_reset", False)[0], set_params)

    def test_clear_cached_drv(self):
        """Test clear_cached_drv()."""
        self.v4_dev._drv_dict = {1: 2}
        self.v4_dev.clear_cached_drv()
        self.assertEqual(self.v4_dev._drv_dict, {})

    def test_doc_all(self):
        """Test doc_all()."""
        self.v4_dev.syscfg.display_config = unittest.mock.MagicMock(
            return_value="displayconfig"
        )
        self.assertEqual(self.v4_dev.doc_all(), "displayconfig")

    def test_doc(self):
        """Test doc()."""
        self.v4_dev._logger.debug = unittest.mock.MagicMock()
        self.v4_dev.syscfg.is_control = unittest.mock.MagicMock(return_value=True)
        self.v4_dev.syscfg.get_control_docstring = unittest.mock.MagicMock(
            return_value="controldoc"
        )

        self.assertEqual(self.v4_dev.doc("control"), "controldoc")
        self.v4_dev._logger.debug.assert_called_once_with("name(%s)", "control")

    def test_doc_error(self):
        """Test doc() in case of error."""
        self.v4_dev._logger.debug = unittest.mock.MagicMock()
        self.v4_dev.syscfg.is_control = unittest.mock.MagicMock(return_value=False)

        with self.assertRaisesRegex(NameError, "No control ctrl"):
            self.v4_dev.doc("ctrl")
        self.v4_dev._logger.debug.assert_called_once_with("name(%s)", "ctrl")

    def test_hwinit(self):
        """Test hwinit()."""
        self.v4_dev._logger.debug = unittest.mock.MagicMock()
        self.v4_dev._logger.info = unittest.mock.MagicMock()
        self.v4_dev._logger.error = unittest.mock.MagicMock()
        self.v4_dev.syscfg.hwinit = [
            ("control1", "value1"),
            ("control2", "value2"),
            ("control3", "value3"),
        ]
        self.v4_dev.get = unittest.mock.MagicMock(side_effect=["value2", "not-value3"])
        self.v4_dev.set = unittest.mock.MagicMock()

        self.v4_dev.hwinit(True, ["control1"])

        self.v4_dev._logger.debug.assert_called_once_with(
            "Skip initializing control %r because it is already initialized "
            "for a child device.",
            "control1",
        )
        self.v4_dev.get.assert_has_calls(
            [unittest.mock.call("control2"), unittest.mock.call("control3")]
        )
        self.v4_dev.set.assert_called_once_with("control3", "value3")
        self.v4_dev._logger.info.assert_has_calls(
            [
                unittest.mock.call("Initialized %s to %s", "control2", "value2"),
                unittest.mock.call("Initialized %s to %s", "control3", "value3"),
            ]
        )
        self.v4_dev._logger.error.assert_not_called()

    def test_hwinit_error(self):
        """Test hwinit() in case of error."""
        self.v4_dev._logger.debug = unittest.mock.MagicMock()
        self.v4_dev._logger.info = unittest.mock.MagicMock()
        self.v4_dev._logger.error = unittest.mock.MagicMock()
        self.v4_dev.syscfg.hwinit = [
            ("control1", "value1"),
            ("control2", "value2"),
            ("control3", "value3"),
        ]
        self.v4_dev.get = unittest.mock.MagicMock(
            side_effect=["value2", ValueError("valueerror")]
        )
        self.v4_dev.set = unittest.mock.MagicMock()

        self.v4_dev.hwinit(True, ["control1"])

        self.v4_dev._logger.debug.assert_called_once_with(
            "Skip initializing control %r because it is already initialized "
            "for a child device.",
            "control1",
        )
        self.v4_dev.get.assert_has_calls(
            [unittest.mock.call("control2"), unittest.mock.call("control3")]
        )
        self.v4_dev.set.assert_not_called()
        self.v4_dev._logger.info.assert_called_once_with(
            "Initialized %s to %s", "control2", "value2"
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
        self.assertEqual(v4_json["vendor_id"], tmpl.GetVID("servo_v4"))
        self.assertEqual(v4_json["product_id"], tmpl.GetPID("servo_v4"))
        self.assertEqual(v4_json["serial"], "servo_v4_serial")
        self.assertEqual(v4_json["sysfs_path"], "/sys/bus/usb/devices/-2-1.2")
        self.assertEqual(v4_json["root_hub_device"], None)
        self.assertEqual(v4_json["child_devices"], [])

        micro_json = json.loads(self.micro_dev.to_json())
        self.assertEqual(micro_json["prefix"], ["micro"])
        self.assertEqual(micro_json["type"], "servo_micro")
        self.assertEqual(micro_json["vendor_id"], tmpl.GetVID("servo_micro"))
        self.assertEqual(micro_json["product_id"], tmpl.GetPID("servo_micro"))
        self.assertEqual(micro_json["serial"], "servo_micro_serial")
        self.assertEqual(micro_json["sysfs_path"], "/sys/bus/usb/devices/-2-1.2.3")
        self.assertEqual(micro_json["root_hub_device"], None)
        self.assertEqual(micro_json["child_devices"], [])


if __name__ == "__main__":
    unittest.main()
