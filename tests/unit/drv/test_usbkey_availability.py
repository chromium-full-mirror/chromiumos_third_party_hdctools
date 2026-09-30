# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests usbkeyAvailability class."""

import unittest
from unittest import mock

from servo.drv import usbkey_availability


class TestUsbkeyAvailability(unittest.TestCase):
    """Unit test class for usbkeyAvailability."""

    def setUp(self):
        """Set up for each test case."""
        params = {"cmd": "set", "input_type": "str"}
        self.drv = usbkey_availability.usbkeyAvailability(
            ("localhost", 9999), ("localhost", 9999), "mock_interface", params
        )

    @mock.patch("servo.drv.hw_driver.HwDriver._servod_set")
    @mock.patch("servo.drv.hw_driver.HwDriver._servod_get")
    @mock.patch("servo.drv.hw_driver.HwDriver._servod_has_control")
    def test_set_off_noop(self, has_control_mock, servod_get_mock, servod_set_mock):
        """Test that setting 'off' is a no-op."""
        self.drv._set("off")
        has_control_mock.assert_not_called()
        servod_get_mock.assert_not_called()
        servod_set_mock.assert_not_called()

    @mock.patch("servo.drv.hw_driver.HwDriver._servod_set")
    @mock.patch("servo.drv.hw_driver.HwDriver._servod_get")
    @mock.patch("servo.drv.hw_driver.HwDriver._servod_has_control")
    def test_ro_non_pdc_sets_servo_pd_role_snk(
        self, has_control_mock, servod_get_mock, servod_set_mock
    ):
        """Test that RO mode on a non-PDC board sets servo_pd_role to snk."""
        has_control_mock.side_effect = lambda name: name in {
            "root.dut_connection_type",
            "ec_active_copy",
            "ec_board",
            "servo_pd_role",
        }
        get_values = {
            "root.dut_connection_type": "type-c",
            "ec_active_copy": "RO (active_ro)",
            "ec_board": "bluey",
        }
        servod_get_mock.side_effect = lambda name: get_values[name]

        self.drv._set("on")
        servod_set_mock.assert_called_once_with("servo_pd_role", "snk")

    @mock.patch("servo.drv.hw_driver.HwDriver._servod_set")
    @mock.patch("servo.drv.hw_driver.HwDriver._servod_get")
    @mock.patch("servo.drv.hw_driver.HwDriver._servod_has_control")
    def test_ro_pdc_keepalive_skips_snk(
        self, has_control_mock, servod_get_mock, servod_set_mock
    ):
        """Test that pdc_ccd_keepalive_en skips servo_pd_role:snk and falls back to DFP."""
        has_control_mock.side_effect = lambda name: name in {
            "root.dut_connection_type",
            "ec_active_copy",
            "ec_board",
            "pdc_ccd_keepalive_en",
            "servo_pd_role",
            "dut_pd_data_role",
        }
        get_values = {
            "root.dut_connection_type": "type-c",
            "ec_active_copy": "RO (active_ro)",
            "ec_board": "fatcat",
        }
        servod_get_mock.side_effect = lambda name: get_values[name]

        self.drv._set("on")
        servod_set_mock.assert_called_once_with("dut_pd_data_role", "DFP")
