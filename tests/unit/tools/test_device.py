# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Unit-tests to ensure that servodtool device works as intended."""

import argparse
import time
import unittest
import unittest.mock

import usb

import servo.drv.pty_driver as pty_driver
from servo.tools import device
from servo.utils import usb_hierarchy


class TestDevice(unittest.TestCase):
    """Test device.py."""

    def test_help(self):
        """Test help()."""
        self.assertEqual(device.Device().help, "Manage servo device.")

    @unittest.mock.patch(
        "servo.utils.usb_hierarchy.Hierarchy.get_all_usb_device_sysfs_paths",
        unittest.mock.MagicMock(return_value=["/path/1/a/b/c", "/path/2/a/b/c"]),
    )
    @unittest.mock.patch(
        "servo.utils.usb_hierarchy.Hierarchy.serial_from_sysfs",
        unittest.mock.MagicMock(side_effect=["not_id", "id"]),
    )
    def test__usb_path(self):
        """Test _usb_path()."""
        d = device.Device()
        res = d._usb_path("id")

        usb_hierarchy.Hierarchy.get_all_usb_device_sysfs_paths.assert_called_once_with(
            list(device.servo_dev_templates.SERVO_ID_DEFAULTS)
        )
        usb_hierarchy.Hierarchy.serial_from_sysfs.assert_has_calls(
            [unittest.mock.call("/path/1/a/b/c"), unittest.mock.call("/path/2/a/b/c")]
        )
        self.assertEqual(res, "/path/2/a/b/c")

    @unittest.mock.patch(
        "servo.utils.usb_hierarchy.Hierarchy.get_all_usb_device_sysfs_paths",
        unittest.mock.MagicMock(return_value=["/path/1/a/b/c", "/path/2/a/b/c"]),
    )
    @unittest.mock.patch(
        "servo.utils.usb_hierarchy.Hierarchy.serial_from_sysfs",
        unittest.mock.MagicMock(side_effect=["not_id", "not_id"]),
    )
    def test__usb_path_nonexistent(self):
        """Test _usb_path()."""
        d = device.Device()
        res = d._usb_path("id")

        usb_hierarchy.Hierarchy.get_all_usb_device_sysfs_paths.assert_called_once_with(
            list(device.servo_dev_templates.SERVO_ID_DEFAULTS)
        )
        usb_hierarchy.Hierarchy.serial_from_sysfs.assert_has_calls(
            [unittest.mock.call("/path/1/a/b/c"), unittest.mock.call("/path/2/a/b/c")]
        )
        self.assertIsNone(res)

    def test_usb_path(self):
        """Test usb_path()."""
        d = device.Device()
        d._usb_path = unittest.mock.MagicMock(return_value="/path/1/a/b/c")
        d._logger.info = unittest.mock.MagicMock()
        d.error = unittest.mock.MagicMock()
        args = argparse.Namespace()
        args.serial = "id"
        d.usb_path(args)

        d._usb_path.assert_called_once_with("id")
        d._logger.info.assert_called_once_with("/path/1/a/b/c")
        d.error.assert_not_called()

    def test_usb_path_nonexistent(self):
        """Test usb_path()."""
        d = device.Device()
        d._usb_path = unittest.mock.MagicMock(return_value=None)
        d._logger.info = unittest.mock.MagicMock()
        d.error = unittest.mock.MagicMock()
        args = argparse.Namespace()
        args.serial = "id"
        d.usb_path(args)

        d._usb_path.assert_called_once_with("id")
        d._logger.info.assert_not_called()
        d.error.assert_called_once_with("Device with serial %r not found.", "id")

    @unittest.mock.patch(
        "servo.utils.usb_hierarchy.Hierarchy.vendor_id_from_sysfs",
        unittest.mock.MagicMock(return_value=0x18D1),
    )
    @unittest.mock.patch(
        "servo.utils.usb_hierarchy.Hierarchy.product_id_from_sysfs",
        unittest.mock.MagicMock(return_value=0x501B),
    )
    @unittest.mock.patch(
        "servo.utils.usb_hierarchy.Hierarchy.dev_num_from_sysfs",
        unittest.mock.MagicMock(return_value=1),
    )
    @unittest.mock.patch(
        "servo.drv.pty_driver.PtyDriver.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    @unittest.mock.patch(
        "servo.drv.pty_driver.PtyDriver._issue_cmd_get_results",
        unittest.mock.MagicMock(),
    )
    @unittest.mock.patch(
        "servo.common.interface.stm32uart.Suart.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    @unittest.mock.patch(
        "servo.common.interface.stm32uart.Suart.run", unittest.mock.MagicMock()
    )
    @unittest.mock.patch(
        "servo.common.interface.stm32uart.Suart.reinitialize",
        unittest.mock.MagicMock(
            side_effect=[
                Exception("reinit fail"),
                Exception("reinit fail"),
                Exception("reinit fail"),
                None,
            ]
        ),
    )
    @unittest.mock.patch("time.sleep", unittest.mock.MagicMock())
    def test_reboot(self):
        """Test reboot()."""
        d = device.Device()
        d._usb_path = unittest.mock.MagicMock(return_value="/path/1/a/b/c")
        d.error = unittest.mock.MagicMock(side_effect=SystemExit(1))
        d._logger.debug = unittest.mock.MagicMock()
        d._check_devnum_reset = unittest.mock.MagicMock()
        args = argparse.Namespace()
        args.serial = "id"

        d.reboot(args)

        d._usb_path.assert_called_once_with("id")
        usb_hierarchy.Hierarchy.vendor_id_from_sysfs.assert_called_once_with(
            "/path/1/a/b/c"
        )
        usb_hierarchy.Hierarchy.product_id_from_sysfs.assert_called_once_with(
            "/path/1/a/b/c"
        )
        usb_hierarchy.Hierarchy.dev_num_from_sysfs.assert_called_once_with(
            "/path/1/a/b/c"
        )
        pty_driver.PtyDriver._issue_cmd_get_results.assert_has_calls(
            [
                unittest.mock.call("chan 0", [">"]),
                unittest.mock.call("reboot", [">"]),
                unittest.mock.call("chan 0", [">"]),
                unittest.mock.call("serialno", [r"Serial number: ([^\r\n]+)[\n\r]+"]),
                unittest.mock.call("chan restore", [">"]),
            ]
        )
        d._check_devnum_reset("/path/1/a/b/c", 1, "reboot")
        d._logger.debug.assert_has_calls(
            [
                unittest.mock.call(
                    "Attempt %d to interact with console post reboot", 1
                ),
                unittest.mock.call(unittest.mock.ANY),
                unittest.mock.call(
                    "Attempt %d to interact with console post reboot", 2
                ),
                unittest.mock.call(unittest.mock.ANY),
                unittest.mock.call(
                    "Attempt %d to interact with console post reboot", 3
                ),
                unittest.mock.call(unittest.mock.ANY),
                unittest.mock.call(
                    "Attempt %d to interact with console post reboot", 4
                ),
            ]
        )
        time.sleep.assert_has_calls(
            [
                unittest.mock.call(d.REBOOT_SLEEP_S),
                unittest.mock.call(d.REBOOT_SLEEP_S),
                unittest.mock.call(d.REBOOT_SLEEP_S),
            ]
        )
        d.error.assert_not_called()

    def test_reboot_nonexistent(self):
        """Test reboot()."""
        d = device.Device()
        d._usb_path = unittest.mock.MagicMock(return_value=None)
        d.error = unittest.mock.MagicMock(side_effect=SystemExit(1))
        args = argparse.Namespace()
        args.serial = "id"

        with self.assertRaises(SystemExit) as cm:
            d.reboot(args)

        self.assertEqual(cm.exception.code, 1)
        d._usb_path.assert_called_once_with("id")
        d.error.assert_called_once_with("Device with serial %r not found.", "id")

    @unittest.mock.patch(
        "servo.utils.usb_hierarchy.Hierarchy.vendor_id_from_sysfs",
        unittest.mock.MagicMock(return_value=0x18D1),
    )
    @unittest.mock.patch(
        "servo.utils.usb_hierarchy.Hierarchy.product_id_from_sysfs",
        unittest.mock.MagicMock(return_value=0x5042),
    )
    @unittest.mock.patch(
        "servo.utils.usb_hierarchy.Hierarchy.dev_num_from_sysfs",
        unittest.mock.MagicMock(return_value=1),
    )
    def test_reboot_cannot_reboot(self):
        """Test reboot()."""
        d = device.Device()
        d._usb_path = unittest.mock.MagicMock(return_value="/path/1/a/b/c")
        d.error = unittest.mock.MagicMock(side_effect=SystemExit(1))
        args = argparse.Namespace()
        args.serial = "id"

        with self.assertRaises(SystemExit) as cm:
            d.reboot(args)

        self.assertEqual(cm.exception.code, 1)
        d._usb_path.assert_called_once_with("id")
        usb_hierarchy.Hierarchy.vendor_id_from_sysfs.assert_called_once_with(
            "/path/1/a/b/c"
        )
        usb_hierarchy.Hierarchy.product_id_from_sysfs.assert_called_once_with(
            "/path/1/a/b/c"
        )
        usb_hierarchy.Hierarchy.dev_num_from_sysfs.assert_called_once_with(
            "/path/1/a/b/c"
        )
        d.error.assert_called_once_with(
            "Device %04x:%04x %s does not support reboot", 0x18D1, 0x5042, "id"
        )

    @unittest.mock.patch(
        "servo.utils.usb_hierarchy.Hierarchy.vendor_id_from_sysfs",
        unittest.mock.MagicMock(return_value=0x18D1),
    )
    @unittest.mock.patch(
        "servo.utils.usb_hierarchy.Hierarchy.product_id_from_sysfs",
        unittest.mock.MagicMock(return_value=0x501B),
    )
    @unittest.mock.patch(
        "servo.utils.usb_hierarchy.Hierarchy.dev_num_from_sysfs",
        unittest.mock.MagicMock(return_value=1),
    )
    @unittest.mock.patch(
        "servo.drv.pty_driver.PtyDriver.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    @unittest.mock.patch(
        "servo.drv.pty_driver.PtyDriver._issue_cmd_get_results",
        unittest.mock.MagicMock(
            side_effect=[None, pty_driver.PtyError("No data was sent from the pty")]
        ),
    )
    @unittest.mock.patch(
        "servo.common.interface.stm32uart.Suart.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    @unittest.mock.patch(
        "servo.common.interface.stm32uart.Suart.run", unittest.mock.MagicMock()
    )
    @unittest.mock.patch(
        "servo.common.interface.stm32uart.Suart.reinitialize",
        unittest.mock.MagicMock(side_effect=Exception("reinit fail")),
    )
    @unittest.mock.patch("time.sleep", unittest.mock.MagicMock())
    def test_reboot_exception(self):
        """Test reboot()."""
        d = device.Device()
        d._usb_path = unittest.mock.MagicMock(return_value="/path/1/a/b/c")
        d.error = unittest.mock.MagicMock(side_effect=SystemExit(1))
        d._logger.debug = unittest.mock.MagicMock()
        d._check_devnum_reset = unittest.mock.MagicMock()
        args = argparse.Namespace()
        args.serial = "id"

        with self.assertRaises(SystemExit) as cm:
            d.reboot(args)

        self.assertEqual(cm.exception.code, 1)
        d._usb_path.assert_called_once_with("id")
        usb_hierarchy.Hierarchy.vendor_id_from_sysfs.assert_called_once_with(
            "/path/1/a/b/c"
        )
        usb_hierarchy.Hierarchy.product_id_from_sysfs.assert_called_once_with(
            "/path/1/a/b/c"
        )
        usb_hierarchy.Hierarchy.dev_num_from_sysfs.assert_called_once_with(
            "/path/1/a/b/c"
        )
        pty_driver.PtyDriver._issue_cmd_get_results.assert_has_calls(
            [unittest.mock.call("chan 0", [">"]), unittest.mock.call("reboot", [">"])]
        )
        d._check_devnum_reset("/path/1/a/b/c", 1, "reboot")
        d._logger.debug.assert_has_calls(
            [
                unittest.mock.call(
                    "Attempt %d to interact with console post reboot", 1
                ),
                unittest.mock.call(unittest.mock.ANY),
                unittest.mock.call(
                    "Attempt %d to interact with console post reboot", 2
                ),
                unittest.mock.call(unittest.mock.ANY),
                unittest.mock.call(
                    "Attempt %d to interact with console post reboot", 3
                ),
                unittest.mock.call(unittest.mock.ANY),
                unittest.mock.call(
                    "Attempt %d to interact with console post reboot", 4
                ),
                unittest.mock.call(unittest.mock.ANY),
            ]
        )
        time.sleep.assert_has_calls(
            [
                unittest.mock.call(d.REBOOT_SLEEP_S),
                unittest.mock.call(d.REBOOT_SLEEP_S),
                unittest.mock.call(d.REBOOT_SLEEP_S),
                unittest.mock.call(d.REBOOT_SLEEP_S),
            ]
        )
        d.error.assert_called_once_with(
            "Device %04x:%04x %s issue after reboot: %s",
            0x18D1,
            0x501B,
            "id",
            unittest.mock.ANY,
        )

    @unittest.mock.patch(
        "servo.utils.usb_hierarchy.Hierarchy.dev_num_from_sysfs",
        unittest.mock.MagicMock(return_value=1),
    )
    @unittest.mock.patch(
        "servo.utils.usb_hierarchy.Hierarchy.bus_num_from_sysfs",
        unittest.mock.MagicMock(return_value=2),
    )
    @unittest.mock.patch("usb.core.find", unittest.mock.MagicMock())
    @unittest.mock.patch("usb.util.get_string", unittest.mock.MagicMock())
    def test_usb_comms(self):
        """Test usb_comms()."""
        d = device.Device()
        d._usb_path = unittest.mock.MagicMock(return_value="/path/1/a/b/c")
        d.error = unittest.mock.MagicMock(side_effect=SystemExit(1))
        args = argparse.Namespace()
        args.serial = "id"

        d.usb_comms(args)

        d._usb_path.assert_called_once_with("id")
        usb_hierarchy.Hierarchy.dev_num_from_sysfs.assert_called_once_with(
            "/path/1/a/b/c"
        )
        usb_hierarchy.Hierarchy.bus_num_from_sysfs.assert_called_once_with(
            "/path/1/a/b/c"
        )
        usb.core.find.assert_called_once_with(address=1, bus=2)
        usb.util.get_string.assert_called_once()
        d.error.assert_not_called()

    def test_usb_comms_nonexistent(self):
        """Test usb_comms()."""
        d = device.Device()
        d._usb_path = unittest.mock.MagicMock(return_value=None)
        d.error = unittest.mock.MagicMock(side_effect=SystemExit(1))
        args = argparse.Namespace()
        args.serial = "id"

        with self.assertRaises(SystemExit) as cm:
            d.usb_comms(args)

        self.assertEqual(cm.exception.code, 1)
        d._usb_path.assert_called_once_with("id")
        d.error.assert_called_once_with("Device with serial %r not found.", "id")

    @unittest.mock.patch(
        "servo.utils.usb_hierarchy.Hierarchy.dev_num_from_sysfs",
        unittest.mock.MagicMock(return_value=1),
    )
    @unittest.mock.patch(
        "servo.utils.usb_hierarchy.Hierarchy.bus_num_from_sysfs",
        unittest.mock.MagicMock(return_value=2),
    )
    @unittest.mock.patch("usb.core.find", unittest.mock.MagicMock(return_value=None))
    def test_usb_comms_no_usb(self):
        """Test usb_comms()."""
        d = device.Device()
        d._usb_path = unittest.mock.MagicMock(return_value="/path/1/a/b/c")
        d.error = unittest.mock.MagicMock(side_effect=SystemExit(1))
        args = argparse.Namespace()
        args.serial = "id"

        with self.assertRaises(SystemExit) as cm:
            d.usb_comms(args)

        self.assertEqual(cm.exception.code, 1)
        d._usb_path.assert_called_once_with("id")
        usb_hierarchy.Hierarchy.dev_num_from_sysfs.assert_called_once_with(
            "/path/1/a/b/c"
        )
        usb_hierarchy.Hierarchy.bus_num_from_sysfs.assert_called_once_with(
            "/path/1/a/b/c"
        )
        usb.core.find.assert_called_once_with(address=1, bus=2)
        d.error.assert_called_once_with(
            "Device with serial %r not found on pyusb.", "id"
        )

    @unittest.mock.patch(
        "servo.utils.usb_hierarchy.Hierarchy.dev_num_from_sysfs",
        unittest.mock.MagicMock(return_value=1),
    )
    @unittest.mock.patch(
        "servo.utils.usb_hierarchy.Hierarchy.bus_num_from_sysfs",
        unittest.mock.MagicMock(return_value=2),
    )
    @unittest.mock.patch("usb.core.find", unittest.mock.MagicMock())
    @unittest.mock.patch(
        "usb.util.get_string",
        unittest.mock.MagicMock(side_effect=ValueError("value err")),
    )
    def test_usb_comms_fail_comms(self):
        """Test usb_comms()."""
        d = device.Device()
        d._usb_path = unittest.mock.MagicMock(return_value="/path/1/a/b/c")
        d.error = unittest.mock.MagicMock(side_effect=SystemExit(1))
        args = argparse.Namespace()
        args.serial = "id"

        with self.assertRaises(SystemExit) as cm:
            d.usb_comms(args)

        self.assertEqual(cm.exception.code, 1)
        d._usb_path.assert_called_once_with("id")
        usb_hierarchy.Hierarchy.dev_num_from_sysfs.assert_called_once_with(
            "/path/1/a/b/c"
        )
        usb_hierarchy.Hierarchy.bus_num_from_sysfs.assert_called_once_with(
            "/path/1/a/b/c"
        )
        usb.core.find.assert_called_once_with(address=1, bus=2)
        usb.util.get_string.assert_called_once()
        d.error.assert_called_once_with(
            "Device with serial %r has USB comms issues. %s", "id", unittest.mock.ANY
        )

    @unittest.mock.patch("time.sleep", unittest.mock.MagicMock())
    @unittest.mock.patch(
        "servo.utils.usb_hierarchy.Hierarchy.dev_num_from_sysfs",
        unittest.mock.MagicMock(return_value=2),
    )
    def test__check_devnum_reset(self):
        """Test _check_devnum_reset()."""
        d = device.Device()
        d.error = unittest.mock.MagicMock(side_effect=SystemExit(1))
        with unittest.mock.patch(
            "time.time",
            unittest.mock.MagicMock(side_effect=[1, 1, 2, 3, 1 + d.MAX_REINIT_SLEEP_S]),
        ):
            d._check_devnum_reset("/path/1/a/b/c", 1, "reset")

        usb_hierarchy.Hierarchy.dev_num_from_sysfs.assert_called_once_with(
            "/path/1/a/b/c"
        )
        d.error.assert_not_called()

    @unittest.mock.patch("time.sleep", unittest.mock.MagicMock())
    @unittest.mock.patch(
        "servo.utils.usb_hierarchy.Hierarchy.dev_num_from_sysfs",
        unittest.mock.MagicMock(return_value=1),
    )
    def test__check_devnum_reset_same_devnum(self):
        """Test _check_devnum_reset()."""
        d = device.Device()
        d.error = unittest.mock.MagicMock(side_effect=SystemExit(1))
        with unittest.mock.patch(
            "time.time",
            unittest.mock.MagicMock(side_effect=[1, 1, 2, 3, 1 + d.MAX_REINIT_SLEEP_S]),
        ):
            with self.assertRaises(SystemExit) as cm:
                d._check_devnum_reset("/path/1/a/b/c", 1, "reset")

        self.assertEqual(cm.exception.code, 1)
        usb_hierarchy.Hierarchy.dev_num_from_sysfs.assert_called_once_with(
            "/path/1/a/b/c"
        )
        d.error.assert_called_once_with(
            "%r likely unsuccessful. devnum stayed the same.", "reset"
        )

    @unittest.mock.patch("time.sleep", unittest.mock.MagicMock())
    @unittest.mock.patch(
        "servo.utils.usb_hierarchy.Hierarchy.dev_num_from_sysfs",
        unittest.mock.MagicMock(side_effect=usb_hierarchy.HierarchyError()),
    )
    def test__check_devnum_reset_cannot_read_devnum(self):
        """Test _check_devnum_reset()."""
        d = device.Device()
        d.error = unittest.mock.MagicMock(side_effect=SystemExit(1))
        with unittest.mock.patch(
            "time.time",
            unittest.mock.MagicMock(side_effect=[1, 1, 2, 3, 1 + d.MAX_REINIT_SLEEP_S]),
        ):
            with self.assertRaises(SystemExit) as cm:
                d._check_devnum_reset("/path/1/a/b/c", 1, "reset")

        self.assertEqual(cm.exception.code, 1)
        usb_hierarchy.Hierarchy.dev_num_from_sysfs.assert_has_calls(
            [
                unittest.mock.call("/path/1/a/b/c"),
                unittest.mock.call("/path/1/a/b/c"),
                unittest.mock.call("/path/1/a/b/c"),
            ]
        )
        d.error.assert_called_once_with(
            "unable to read device |devnum| file after %ds. Giving up.",
            d.MAX_REINIT_SLEEP_S,
        )

    def test_add_args(self):
        """Test add_args()."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="tool")
        tparser = subparsers.add_parser("device")
        device.Device().add_args(tparser)

        self.assertEqual(
            parser.parse_args(["device", "-s", "id", "reboot"]).command, "reboot"
        )
        self.assertEqual(
            parser.parse_args(["device", "-s", "id", "usb-comms"]).command, "usb-comms"
        )
        self.assertEqual(
            parser.parse_args(["device", "-s", "id", "usb-path"]).command, "usb-path"
        )


if __name__ == "__main__":
    unittest.main()
