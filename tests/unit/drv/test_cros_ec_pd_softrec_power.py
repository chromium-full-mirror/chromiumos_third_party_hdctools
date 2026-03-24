# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import unittest
import unittest.mock
from unittest.mock import call

import mock

from servo.common.interface import interface
from servo.drv import cros_ec_pd_softrec_power
from servo.drv import hw_driver


class TestCrosEcPdSoftrecPower(unittest.TestCase):
    """
    Unit test class for relaySwitch
    """

    def setUp(self):
        intfc = mock.Mock(interface.Interface)
        params = {"cmd": "set"}
        self.cros_ec_pd_softrec_power = cros_ec_pd_softrec_power.crosEcPdSoftrecPower(
            ("localhost", 9999), ("localhost", 9999), intfc, params
        )

    def test_cold_reset(self):
        """Test _reset_cycle"""
        self.cros_ec_pd_softrec_power._servod_set = unittest.mock.MagicMock()
        self.cros_ec_pd_softrec_power._cold_reset()
        expected_calls = [
            call("cold_reset", "on"),
            call("usbpd_reset", "on"),
            call("usbpd_reset", "off"),
            call("cold_reset", "off"),
        ]
        self.cros_ec_pd_softrec_power._servod_set.assert_has_calls(
            expected_calls, any_order=False
        )

    def test_power_on_bytype(self):
        """Test _power_on_bytype"""
        self.cros_ec_pd_softrec_power._servod_set = unittest.mock.MagicMock()
        self.cros_ec_pd_softrec_power._reboot_to_ro_with_ap_off = (
            unittest.mock.MagicMock()
        )
        self.cros_ec_pd_softrec_power._power_on_bytype(
            self.cros_ec_pd_softrec_power.REC_ON
        )
        self.cros_ec_pd_softrec_power._reboot_to_ro_with_ap_off.assert_called_once()
        expected_calls = [
            call("ec_uart_regexp", "['Events:']"),
            call("ec_uart_cmd", "hostevent set 0x4000"),
            call("ec_uart_regexp", "None"),
        ]
        self.cros_ec_pd_softrec_power._servod_set.assert_has_calls(
            expected_calls, any_order=False
        )
