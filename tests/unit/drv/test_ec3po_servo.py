# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest
from unittest import mock

from servo.drv import ec3po_servo


class TestEc3poServo(unittest.TestCase):
    """Tests for ec3po_servo driver."""

    def setUp(self):
        self._mock_interface = mock.MagicMock()
        del self._mock_interface._uart_state
        self._params = {"cmd": "set", "control_name": "test_control"}
        self.patcher = mock.patch("servo.drv.pty_driver.PtyDriver._issue_cmd")
        self.mock_issue_cmd = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_chan_commands_enabled_by_default(self):
        """Verify chan commands are sent by default."""
        driver = ec3po_servo.ec3poServo(None, None, self._mock_interface, self._params)
        self.assertTrue(driver._has_chan)

        # Manually trigger channel limiting
        driver._limit_channel()
        expected_calls = [
            mock.call("chan save"),
            mock.call("chan %d" % ec3po_servo.COMMAND_CHANNEL_MASK),
        ]
        self.mock_issue_cmd.assert_has_calls(expected_calls)

        driver._restore_channel()
        self.mock_issue_cmd.assert_any_call("chan restore")

    def test_chan_commands_disabled_explicitly(self):
        """Verify chan commands are skipped when has_chan='no'."""
        self._params["has_chan"] = "no"
        driver = ec3po_servo.ec3poServo(None, None, self._mock_interface, self._params)
        self.assertFalse(driver._has_chan)

        driver._limit_channel()
        driver._restore_channel()

        # No calls should have been made to _issue_cmd for chan
        self.mock_issue_cmd.assert_not_called()

    def test_chan_commands_enabled_explicitly(self):
        """Verify chan commands are sent when has_chan='yes'."""
        self._params["has_chan"] = "yes"
        driver = ec3po_servo.ec3poServo(None, None, self._mock_interface, self._params)
        self.assertTrue(driver._has_chan)

        driver._limit_channel()
        self.mock_issue_cmd.assert_any_call("chan save")
