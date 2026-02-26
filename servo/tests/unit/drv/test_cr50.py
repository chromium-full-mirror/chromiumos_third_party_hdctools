# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re
import unittest

import mock

from servo.data.drv import cr50
from servo.data.drv import pty_driver


@mock.patch("servo.data.drv.pty_driver.PtyDriver._issue_cmd_get_results")
class TestPromptDetection(unittest.TestCase):
    class cr50(cr50.cr50):
        def __init__(self):
            pass

        _logger = mock.MagicMock()

    def test_normal_prompt(self, issueCmdMock):
        issueCmdMock.return_value = "value"
        uut = self.cr50()
        self.assertEqual("value", uut._issue_cmd_get_results("cmd\n", []))
        issueCmdMock.assert_called_with(
            "cmd\n", [], flush=None, timeout=pty_driver.DEFAULT_UART_TIMEOUT
        )

    def test_spurious_prompt(self, issueCmdMock):
        def fakeIssueCmd(*args, **kwargs):
            if issueCmdMock.call_count >= cr50.cr50.PROMPT_DETECTION_TRIES:
                return "value"
            else:
                raise pty_driver.PtyError("error")

        issueCmdMock.side_effect = fakeIssueCmd
        uut = self.cr50()
        self.assertEqual("value", uut._issue_cmd_get_results("cmd\n", []))
        issueCmdMock.assert_called_with(
            "cmd\n", [], flush=None, timeout=pty_driver.DEFAULT_UART_TIMEOUT
        )
        # Prompt detection tries + issue of actual command
        self.assertEqual(cr50.cr50.PROMPT_DETECTION_TRIES + 1, issueCmdMock.call_count)

    def test_no_prompt(self, issueCmdMock):
        issueCmdMock.side_effect = pty_driver.PtyError("error")
        uut = self.cr50()
        with self.assertRaises(pty_driver.PtyError):
            uut._issue_cmd_get_results("cmd\n", [])
        self.assertEqual(cr50.cr50.PROMPT_DETECTION_TRIES, issueCmdMock.call_count)


class TestClearRollback(unittest.TestCase):
    def setUp(self):
        self.mock_interface = mock.MagicMock()
        params = {"cmd": "set", "control_name": "gsc_clear_rollback"}
        self.drv = cr50.cr50(
            ("localhost", 9991), ("localhost", 9992), self.mock_interface, params
        )
        self.drv._issue_cmd = mock.MagicMock()
        self.drv._issue_cmd_get_results = mock.MagicMock()

    def test_clear_rollback_sequence(self):
        self.drv._Set_clear_rollback("unused")

        # Verify the sequence of commands
        expected_cmds = [
            mock.call("ccd testlab open"),
            mock.call("ccd reset factory"),
            mock.call("ccd set OpenNoTPMWipe ifopened"),
            mock.call("ccd lock"),
            mock.call("ccd reset"),
        ]
        self.drv._issue_cmd.assert_has_calls(expected_cmds)

        # Verify ccd open specifically with its regex and timeout
        self.drv._issue_cmd_get_results.assert_called_with(
            "ccd open", [r"(State: Open|TPM erased)"], timeout=60
        )
