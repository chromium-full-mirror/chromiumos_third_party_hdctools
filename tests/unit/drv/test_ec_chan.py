# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest
from unittest import mock

from servo.drv import ec


class TestEcChan(unittest.TestCase):
    """Tests for ec driver channel limiting."""

    def setUp(self):
        self._mock_interface = mock.MagicMock()
        del self._mock_interface._uart_state
        self._params = {"cmd": "set", "control_name": "test_control"}
        # Mock _issue_cmd to avoid real IO
        self.patcher = mock.patch("servo.drv.pty_driver.PtyDriver._issue_cmd")
        self.mock_issue_cmd = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_chan_commands_enabled_by_default(self):
        """Verify chan commands are sent by default."""
        driver = ec.ec(None, None, self._mock_interface, self._params)
        self.assertTrue(driver._has_chan)

        driver._limit_channel()
        expected_calls = [
            mock.call("chan save"),
            mock.call("chan %d" % ec.COMMAND_CHANNEL_MASK),
        ]
        self.mock_issue_cmd.assert_has_calls(expected_calls)

        driver._restore_channel()
        self.mock_issue_cmd.assert_any_call("chan restore")

    def test_chan_commands_disabled_explicitly(self):
        """Verify chan commands are skipped when has_chan='no'."""
        self._params["has_chan"] = "no"
        driver = ec.ec(None, None, self._mock_interface, self._params)
        self.assertFalse(driver._has_chan)

        driver._limit_channel()
        driver._restore_channel()

        self.mock_issue_cmd.assert_not_called()
