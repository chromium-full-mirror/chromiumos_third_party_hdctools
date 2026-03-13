# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# pylint: disable=no-value-for-parameter
import unittest
import unittest.mock

from servo.common import interface as _interface
from servo.common import servo_dev_templates as tmpl
from servo.common.utils.interface_utils import InterfaceUtils
from servo.data import servo_interfaces


class TestInterfaceUtils(unittest.TestCase):
    def setUp(self):
        """Set up for each test case."""
        unittest.TestCase.setUp(self)
        self.vid = "6353"
        self.pid = "21005"
        self.serial = "servo_v4_serial"

    def test_get_interface_key(self):
        """Test get interface key"""

        expected_key = "{}_{}_{}".format(self.vid, self.pid, self.serial)
        assert (
            InterfaceUtils.get_interface_key(self.vid, self.pid, self.serial)
            == expected_key
        )

    def test_sync_interface_lists(self):
        """Test sync interface list"""
        interfaces = [True] * 68
        InterfaceUtils.sync_interface_lists(
            interfaces=interfaces, vid=self.vid, pid=self.pid, serial=self.serial
        )
        interface_key = InterfaceUtils.get_interface_key(
            self.vid, self.pid, self.serial
        )
        self.assertIn(interface_key, InterfaceUtils._interface_dict)
        _interface_list = InterfaceUtils.get_interface_list(interface_key)
        _interface_init = InterfaceUtils.get_init_list(interface_key)
        self.assertEqual(len(_interface_list), len(interfaces))
        for interface in _interface_list:
            self.assertTrue(isinstance(interface, _interface.empty.Empty))
        self.assertEqual(_interface_init, [False] * len(interfaces))

    @unittest.mock.patch(
        "servo.common.interface.build", unittest.mock.MagicMock(return_value=None)
    )
    def test_init_servo_interfaces(self):
        """Test init_servo_interfaces()."""
        servo_v4_vid = tmpl.get_vid("servo_v4")
        servo_v4_pid = tmpl.get_pid("servo_v4")
        servo_v4_interfaces = servo_interfaces.INTERFACE_DEFAULTS[servo_v4_vid][
            servo_v4_pid
        ]
        InterfaceUtils.sync_interface_lists(
            interfaces=servo_v4_interfaces,
            vid=servo_v4_vid,
            pid=servo_v4_pid,
            serial="servo_v4_serial",
        )
        InterfaceUtils.init_servo_interfaces(
            interfaces=servo_v4_interfaces,
            vid=servo_v4_vid,
            pid=servo_v4_pid,
            serial="servo_v4_serial",
        )
        interface_key = InterfaceUtils.get_interface_key(
            servo_v4_vid, servo_v4_pid, "servo_v4_serial"
        )
        _interface_init = InterfaceUtils.get_init_list(interface_key)
        _interface_list = InterfaceUtils.get_interface_list(interface_key)
        for i, interface in enumerate(_interface_list):
            if i not in [22, 23, 24, 25, 26]:
                self.assertTrue(isinstance(interface, _interface.empty.Empty))
                self.assertFalse(_interface_init[i])
            else:
                self.assertIsNone(interface)
                self.assertTrue(_interface_init[i])

        servo_micro_vid = tmpl.get_vid("servo_micro")
        servo_micro_pid = tmpl.get_pid("servo_micro")
        servo_micro_interfaces = servo_interfaces.INTERFACE_DEFAULTS[servo_micro_vid][
            servo_micro_pid
        ]
        InterfaceUtils.sync_interface_lists(
            interfaces=servo_micro_interfaces,
            vid=servo_micro_vid,
            pid=servo_micro_pid,
            serial="servo_micro_serial",
        )
        InterfaceUtils.init_servo_interfaces(
            interfaces=servo_micro_interfaces,
            vid=servo_micro_vid,
            pid=servo_micro_pid,
            serial="servo_micro_serial",
        )

        interface_key = InterfaceUtils.get_interface_key(
            servo_micro_vid, servo_micro_pid, "servo_micro_serial"
        )
        _interface_init = InterfaceUtils.get_init_list(interface_key)
        _interface_list = InterfaceUtils.get_interface_list(interface_key)

        for i, interface in enumerate(_interface_list):
            if i not in [1, 2, 3, 6, 7, 8, 9, 10, 11]:
                self.assertTrue(isinstance(interface, _interface.empty.Empty))
                self.assertFalse(_interface_init[i])
            else:
                self.assertIsNone(interface)
                self.assertTrue(_interface_init[i])

    @unittest.mock.patch(
        "servo.common.interface.ec3po_interface.EC3PO.build",
        unittest.mock.MagicMock(
            return_value=unittest.mock.MagicMock(spec=_interface.ec3po_interface.EC3PO)
        ),
    )
    @unittest.mock.patch(
        "servo.common.interface.stm32uart.Suart.build",
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
        InterfaceUtils._interface_dict = {
            "6365_20500_serial": {
                "interface_list": [
                    _interface.ec3po_interface.EC3PO.build(),
                    _interface.stm32uart.Suart.build(),
                    _interface.empty.Empty.build(),
                    _interface.ec3po_interface.EC3PO.build(),
                ]
            }
        }

        InterfaceUtils._logger.info = unittest.mock.MagicMock()
        InterfaceUtils.close_interface("6365_20500_serial")

        InterfaceUtils._logger.info.assert_has_calls(
            [
                unittest.mock.call("Turning down interface %d", 0),
                unittest.mock.call("Turning down interface %d", 3),
                unittest.mock.call("Turning down interface %d", 1),
            ]
        )

    @unittest.mock.patch(
        "servo.common.interface.interface.Interface.reinitialize",
        unittest.mock.MagicMock(),
    )
    @unittest.mock.patch(
        "servo.common.interface.ec3po_interface.EC3PO.build",
        unittest.mock.MagicMock(
            return_value=unittest.mock.MagicMock(spec=_interface.ec3po_interface.EC3PO)
        ),
    )
    @unittest.mock.patch(
        "servo.common.interface.stm32uart.Suart.build",
        unittest.mock.MagicMock(
            return_value=unittest.mock.MagicMock(spec=_interface.stm32uart.Suart)
        ),
    )
    def test_reinitialize(self):
        """Test reinitialize()."""
        interface_key = "6365_20500_serial"
        InterfaceUtils._interface_dict = {
            interface_key: {
                "interface_list": [
                    _interface.empty.Empty.build(),
                    _interface.empty.Empty.build(),
                ]
            },
            "other_device": {
                "interface_list": [
                    _interface.empty.Empty.build(),
                ]
            },
        }
        # Test targeted reinitialize
        _interface.interface.Interface.reinitialize.reset_mock()
        InterfaceUtils.reinitialize(vid=6365, pid=20500, serial="serial")
        self.assertEqual(_interface.interface.Interface.reinitialize.call_count, 2)

        # Test global reinitialize
        _interface.interface.Interface.reinitialize.reset_mock()
        InterfaceUtils.reinitialize()
        expected_call_count = sum(
            len(d["interface_list"]) for d in InterfaceUtils._interface_dict.values()
        )
        self.assertEqual(
            _interface.interface.Interface.reinitialize.call_count, expected_call_count
        )

    @unittest.mock.patch(
        "servo.common.interface.build",
        unittest.mock.MagicMock(side_effect=ValueError("valueerr")),
    )
    def test_init_servo_interfaces_fault_tolerant(self):
        """Test init_servo_interfaces()."""
        servo_v4_vid = tmpl.get_vid("servo_v4")
        servo_v4_pid = tmpl.get_pid("servo_v4")
        servo_v4_serial = "servo_v4_serial"
        servo_v4_interfaces = servo_interfaces.INTERFACE_DEFAULTS[servo_v4_vid][
            servo_v4_pid
        ]
        interface_key = InterfaceUtils.get_interface_key(
            servo_v4_vid, servo_v4_pid, servo_v4_serial
        )
        InterfaceUtils._interface_dict[interface_key] = {
            "interface_list": [],
            "interface_init": [],
        }
        InterfaceUtils.sync_interface_lists(
            interfaces=servo_v4_interfaces,
            vid=servo_v4_vid,
            pid=servo_v4_pid,
            serial=servo_v4_serial,
        )
        InterfaceUtils.init_servo_interfaces(
            interfaces=servo_v4_interfaces,
            vid=servo_v4_vid,
            pid=servo_v4_pid,
            serial=servo_v4_serial,
            fault_tolerant=True,
        )
        _interface_list = InterfaceUtils.get_interface_list(interface_key)
        _interface_init = InterfaceUtils.get_init_list(interface_key)
        for i, interface in enumerate(_interface_list):
            self.assertTrue(isinstance(interface, _interface.empty.Empty))
            self.assertFalse(_interface_init[i])

    @unittest.mock.patch(
        "servo.common.interface.build", unittest.mock.MagicMock(return_value=None)
    )
    def test_init_servo_interfaces_error(self):
        """Test init_servo_interfaces()."""
        servo_v4_vid = tmpl.get_vid("servo_v4")
        servo_v4_pid = tmpl.get_pid("servo_v4")
        servo_v4_serial = "servo_v4_serial"
        servo_v4_interfaces = servo_interfaces.INTERFACE_DEFAULTS[servo_v4_vid][
            servo_v4_pid
        ]
        InterfaceUtils.sync_interface_lists(
            interfaces=servo_v4_interfaces,
            vid=servo_v4_vid,
            pid=servo_v4_pid,
            serial=servo_v4_serial,
        )
        InterfaceUtils.init_servo_interfaces(
            interfaces=servo_v4_interfaces,
            vid=servo_v4_vid,
            pid=servo_v4_pid,
            serial=servo_v4_serial,
        )
        interface_key = InterfaceUtils.get_interface_key(
            servo_v4_vid, servo_v4_pid, servo_v4_serial
        )
        InterfaceUtils._interface_dict[interface_key]["interface_init"][26] = False
        interfaces = servo_v4_interfaces.copy()
        interfaces[26] = 2
        with self.assertRaisesRegex(
            TypeError, "Illegal interface data type %s" % type(2)
        ):
            InterfaceUtils.init_servo_interfaces(
                interfaces=interfaces,
                vid=servo_v4_vid,
                pid=servo_v4_pid,
                serial=servo_v4_serial,
            )
