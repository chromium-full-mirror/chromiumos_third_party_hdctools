# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import unittest
import unittest.mock

import mock

from servo.drv import cros_ec_softrec_power
from servo.drv.pty_driver import DEFAULT_UART_TIMEOUT


class TestCrosEcSoftrecPower(unittest.TestCase):
    """
    Unit test class for crosEcSoftrecPower
    """

    def setUp(self):
        intfc = mock.Mock()
        params = {"cmd": "set"}
        self.drv = cros_ec_softrec_power.crosEcSoftrecPower(
            ("localhost", 9999), ("localhost", 9999), intfc, params
        )
        self.drv._driver_client = unittest.mock.MagicMock()
        self.drv._servod_get = unittest.mock.MagicMock(return_value="0")
        self.drv._servod_set = unittest.mock.MagicMock()
        self.drv._servod_has_control = unittest.mock.MagicMock(return_value=False)
        self.drv._cold_reset = unittest.mock.MagicMock()
        self.drv._power_on_ap = unittest.mock.MagicMock()

    @unittest.mock.patch("time.sleep")
    def test_power_on_rec_on_flushes_hostevent(self, mock_sleep):
        """Test that REC_ON sends hostevent with flush=True to avoid console chatter interference."""
        self.drv._power_on_bytype(self.drv.REC_ON, self.drv._REC_TYPE_REC_ON)

        # Verify LimitEcDriverChannel is called twice (once at start, once after reboot)
        self.assertEqual(self.drv._driver_client.LimitEcDriverChannel.call_count, 2)

        # Verify IssueCmdGetResult is called for hostevent with flush=True
        # This asserts our regression fix (b:494270575) stays in place
        self.drv._driver_client.IssueCmdGetResult.assert_any_call(
            cmds=self.drv._HOSTEVENT_CMD_REC_ON,
            regex_list=["Events:"],
            flush=True,
            time_out=DEFAULT_UART_TIMEOUT,
            prefix=self.drv._prefix,
        )

        # Verify RestoreEcDriverChannel is called
        self.drv._driver_client.RestoreEcDriverChannel.assert_called_once()

    @unittest.mock.patch("time.sleep")
    def test_power_on_rec_off_flushes_hostevents(self, mock_sleep):
        """Test that REC_OFF sends hostevents with flush=True."""
        self.drv._power_on_bytype(self.drv.REC_OFF, self.drv._REC_TYPE_REC_OFF)

        # Verify LimitEcDriverChannel is called once
        self.drv._driver_client.LimitEcDriverChannel.assert_called_once()

        # Verify REC_OFF_CLEARB is sent with flush=True
        self.drv._driver_client.IssueCmdGetResult.assert_any_call(
            cmds=self.drv._HOSTEVENT_CMD_REC_OFF_CLEARB,
            regex_list=["Events:"],
            flush=True,
            time_out=DEFAULT_UART_TIMEOUT,
            prefix=self.drv._prefix,
        )

        # Verify REC_OFF is sent with flush=True
        self.drv._driver_client.IssueCmdGetResult.assert_any_call(
            cmds=self.drv._HOSTEVENT_CMD_REC_OFF,
            regex_list=["Events:"],
            flush=True,
            time_out=DEFAULT_UART_TIMEOUT,
            prefix=self.drv._prefix,
        )
