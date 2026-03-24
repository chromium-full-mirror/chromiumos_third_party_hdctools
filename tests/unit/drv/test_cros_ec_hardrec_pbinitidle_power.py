# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import unittest
import unittest.mock

import mock

from servo.common.interface import interface
from servo.drv import cros_ec_hardrec_pbinitidle_power
from servo.drv import hw_driver


class TestCrosEcHardrecPbintidlePower(unittest.TestCase):
    """
    Unit test class for relaySwitch
    """

    def setUp(self):
        intfc = mock.Mock(interface.Interface)
        params = {"cmd": "set"}
        self.cros_ec_hardrec_pbinitidle_power = (
            cros_ec_hardrec_pbinitidle_power.crosEcHardrecPbinitidlePower(
                ("localhost", 9999), ("localhost", 9999), intfc, params
            )
        )

    def test_reset_cycle(self):
        """Test _reset_cycle"""
        self.cros_ec_hardrec_pbinitidle_power._servod_get = unittest.mock.MagicMock(
            return_value="S1"
        )
        self.cros_ec_hardrec_pbinitidle_power._servod_set = unittest.mock.MagicMock()
        self.cros_ec_hardrec_pbinitidle_power._power_on_rec = unittest.mock.MagicMock()
        self.cros_ec_hardrec_pbinitidle_power._power_on_rec_force_mrc = (
            unittest.mock.MagicMock()
        )
        self.cros_ec_hardrec_pbinitidle_power._power_on_normal = (
            unittest.mock.MagicMock()
        )
        self.cros_ec_hardrec_pbinitidle_power._cold_reset = unittest.mock.MagicMock()
        self.cros_ec_hardrec_pbinitidle_power._reset_cycle()
        self.cros_ec_hardrec_pbinitidle_power._power_on_normal.assert_called_once()
        self.cros_ec_hardrec_pbinitidle_power._cold_reset.assert_called_once()
