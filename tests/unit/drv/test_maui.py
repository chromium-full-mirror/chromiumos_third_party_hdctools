# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from servo.drv.maui import maui


@pytest.fixture
def maui_driver():
    mock_interface = MagicMock()
    mock_interface.get_pty.return_value = "/dev/pts/999"
    # Basic params
    params = {
        "uart_cmd": "version",
        "regex": r"Version: (\d+)",
        "group": "1",
        "cmd": "get",
    }
    with patch("servo.drv.pty_driver.PtyDriver._refresh_pty_path"):
        driver = maui(("localhost", 9999), ("localhost", 9998), mock_interface, params)
    return driver


@patch("servo.drv.maui.maui._issue_cmd_get_results")
def test_maui_get_text(mock_issue, maui_driver):
    mock_issue.return_value = ["123"]
    assert maui_driver._Get_text() == "123"
    mock_issue.assert_called_with("version", [r"Version: (\d+)"], timeout=10.0)


def test_maui_issue_cmd_get_results_first_time(maui_driver):
    with patch("servo.drv.uart.uart._issue_cmd_get_results") as mock_super_issue:
        mock_super_issue.return_value = [("match",)]

        maui_driver._issue_cmd_get_results("test_cmd", ["regex"])

        # Verify wakeup was sent via super call
        mock_super_issue.assert_any_call("\n\n\n", [r"maui\$ "], timeout=5)
        # Verify main command was sent via super call
        mock_super_issue.assert_any_call("test_cmd", ["regex"], timeout=None)

        assert maui_driver._prompt_found is True


def test_maui_issue_cmd_get_results_second_time(maui_driver):
    maui_driver._prompt_found = True

    with patch("servo.drv.uart.uart._issue_cmd_get_results") as mock_super_issue:
        mock_super_issue.return_value = [("match",)]

        maui_driver._issue_cmd_get_results("test_cmd", ["regex"])

        # Verify wakeup was NOT sent again
        # There should only be ONE call to super_issue
        assert mock_super_issue.call_count == 1
        mock_super_issue.assert_called_with("test_cmd", ["regex"], timeout=None)
