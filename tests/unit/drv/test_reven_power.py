# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests reven power commands."""

import unittest

import mock

from servo.common.interface import interface
from servo.core import servo_server
from servo.drv import hw_driver
from servo.drv import reven_power


class TestRevenPower(unittest.TestCase):
    """
    Unit test class for revenPower
    """

    def setUp(self):
        intfc = mock.Mock(interface.Interface)
        params = {"cmd": "set"}
        self.reven_power = reven_power.revenPower(
            ("localhost", 9999), ("localhost", 9999), intfc, params
        )

    @mock.patch("servo.drv.hw_driver.HwDriver._servod_set")
    def test_power_off(self, servod_set_mock):
        """Test power_off"""
        self.reven_power._power_off(2)
        servod_set_mock.assert_called_once_with("relay_pwrbtn_press", 2)

    @mock.patch("servo.drv.hw_driver.HwDriver._servod_set")
    def test_power_on(self, servod_set_mock):
        """Test power_on"""
        self.reven_power._power_on(self.reven_power.REC_OFF, 2)
        servod_set_mock.assert_called_once_with("relay_pwrbtn_press", 2)

    @mock.patch("servo.drv.hw_driver.HwDriver._servod_set")
    def test_power_on_bad_input(self, servod_set_mock):
        """Test power_on returns error when wrong rec mode passed in"""
        self.assertRaises(
            reven_power.RevenPowerError,
            self.reven_power._power_on,
            self.reven_power.REC_ON,
        )
        servod_set_mock.assert_not_called()

    @mock.patch("servo.drv.reven_power.revenPower._power_on")
    @mock.patch("servo.drv.reven_power.revenPower._power_off")
    def test_reset_cycle(self, power_off_mock, power_on_mock):
        """Test that reset_cycle makes correct calls to on and off functions"""
        self.reven_power._reset_cycle(0)
        power_off_mock.assert_called_once()
        power_on_mock.assert_called_once_with(self.reven_power.REC_OFF)
