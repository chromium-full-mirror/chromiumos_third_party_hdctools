# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from servo.drv import maui as maui_module
from servo.drv.maui import maui
from servo.drv.maui import MauiError
from servo.drv.pty_driver import PtyError


SUPER_ISSUE = "servo.drv.uart.uart._issue_cmd_get_results"


def _make_driver(params):
    mock_interface = MagicMock()
    mock_interface.get_pty.return_value = "/dev/pts/999"
    with patch("servo.drv.pty_driver.PtyDriver._refresh_pty_path"):
        return maui(("localhost", 9999), ("localhost", 9998), mock_interface, params)


def _wrapped(regex):
    return "(?:%s)|%s" % (regex, maui_module._FW_ERROR_RE)


@pytest.fixture
def maui_driver():
    # Basic params
    params = {
        "uart_cmd": "version",
        "regex": r"Version: (\d+)",
        "group": "1",
        "cmd": "get",
    }
    return _make_driver(params)


@pytest.fixture
def action_driver():
    driver = _make_driver({"cmd": "set", "timeout": "5.0"})
    driver._prompt_found = True
    return driver


@patch("servo.drv.maui.maui._issue_cmd_get_results")
def test_maui_get_text(mock_issue, maui_driver):
    mock_issue.return_value = ["123"]
    assert maui_driver._Get_text() == "123"
    mock_issue.assert_called_with("version", [r"Version: (\d+)"], timeout=10.0)


def test_maui_get_text_returns_group(maui_driver):
    maui_driver._prompt_found = True
    with patch(SUPER_ISSUE) as mock_super_issue:
        mock_super_issue.return_value = [("Version: 42", "42")]
        assert maui_driver._Get_text() == "42"


def test_maui_issue_cmd_get_results_first_time(maui_driver):
    with patch(SUPER_ISSUE) as mock_super_issue:
        # pty_driver returns a plain string for a regex without groups.
        mock_super_issue.return_value = ["regex"]

        assert maui_driver._issue_cmd_get_results("test_cmd", ["regex"]) == ["regex"]

        # Verify wakeup was sent via super call
        mock_super_issue.assert_any_call("\n\n\n", [r"maui\$ "], None, 5)
        # Verify main command was sent via super call, wrapped with the
        # firmware error regex and with the default (finite) timeout.
        mock_super_issue.assert_any_call("test_cmd", [_wrapped("regex")], None, 3)

        assert maui_driver._prompt_found is True


def test_maui_issue_cmd_get_results_second_time(maui_driver):
    maui_driver._prompt_found = True

    with patch(SUPER_ISSUE) as mock_super_issue:
        mock_super_issue.return_value = ["regex"]

        assert maui_driver._issue_cmd_get_results("test_cmd", ["regex"]) == ["regex"]

        # Verify wakeup was NOT sent again
        # There should only be ONE call to super_issue
        assert mock_super_issue.call_count == 1
        mock_super_issue.assert_called_with("test_cmd", [_wrapped("regex")], None, 3)


def test_maui_wakeup_failure_still_sends_command(maui_driver):
    with patch(SUPER_ISSUE) as mock_super_issue:
        mock_super_issue.side_effect = [PtyError("no prompt"), ["regex"]]

        assert maui_driver._issue_cmd_get_results("test_cmd", ["regex"]) == ["regex"]

        assert mock_super_issue.call_count == 2
        mock_super_issue.assert_called_with("test_cmd", [_wrapped("regex")], None, 3)


def test_maui_uart_cmd_passes_flush(maui_driver):
    """PtyDriver._Set_uart_cmd passes flush/timeout positionally."""
    maui_driver._prompt_found = True
    maui_driver._interface._uart_state = {
        "uart_regexp": [r"Maui version (\S+)"],
        "uart_flush": False,
        "uart_timeout": 2,
    }
    with patch(SUPER_ISSUE) as mock_super_issue:
        mock_super_issue.return_value = [("Maui version 1.2", "1.2")]
        maui_driver._Set_uart_cmd("version")
        mock_super_issue.assert_called_once_with(
            "version", [_wrapped(r"Maui version (\S+)")], False, 2
        )
    assert maui_driver._interface._uart_state["uart_cmd"] == [
        ("Maui version 1.2", "1.2")
    ]


@pytest.mark.parametrize(
    "subtype,value,cmd,done_re",
    [
        ("dut_power", 0, "power_dut off", r"DUT Power: OFF"),
        ("dut_power", 1, "power_dut on", r"DUT Power: ON"),
        ("dut_power", 2, "power_dut cycle", r"DUT Power: Cycling started"),
        ("dut_data", 0, "data_dut off", r"DUT Data: OFF"),
        ("dut_data", 1, "data_dut on", r"DUT Data: ON"),
        ("dut_data", 2, "data_dut cycle", r"DUT Data: Cycling started"),
    ],
)
def test_maui_set_actions(action_driver, subtype, value, cmd, done_re):
    with patch(SUPER_ISSUE) as mock_super_issue:
        mock_super_issue.return_value = [done_re]
        getattr(action_driver, "_Set_%s" % subtype)(value)
        mock_super_issue.assert_called_once_with(cmd, [_wrapped(done_re)], None, 5.0)


@pytest.mark.parametrize("subtype", ["dut_power", "dut_data"])
def test_maui_set_action_invalid_value(action_driver, subtype):
    with patch(SUPER_ISSUE) as mock_super_issue:
        with pytest.raises(MauiError, match="use off, on or cycle"):
            getattr(action_driver, "_Set_%s" % subtype)(3)
        mock_super_issue.assert_not_called()


def test_maui_set_action_firmware_error(action_driver):
    with patch(SUPER_ISSUE) as mock_super_issue:
        mock_super_issue.return_value = [
            ("\nFailed to cut DUT power: -5", "Failed to cut DUT power: -5")
        ]
        with pytest.raises(
            MauiError, match="'power_dut off' failed: Failed to cut DUT power: -5"
        ):
            action_driver._Set_dut_power(0)


def test_maui_firmware_error_with_groups(action_driver):
    with patch(SUPER_ISSUE) as mock_super_issue:
        mock_super_issue.return_value = [
            ("\nFailed to read X", None, "Failed to read X")
        ]
        with pytest.raises(MauiError, match="Failed to read X"):
            action_driver._issue_cmd_get_results("adc read X", [r"\[X\] = (\d+) mV"])


def _search(regex, output):
    """Search the wrapped regex in |output| the way pexpect does (bytes)."""
    return re.search(_wrapped(regex).encode(), output, re.DOTALL)


def test_fw_error_regex_success():
    match = _search(r"DUT Power: OFF", b"power_dut off\r\nDUT Power: OFF (PDC)\r\n")
    assert match.group(0) == b"DUT Power: OFF"
    assert match.group("maui_error") is None


@pytest.mark.parametrize(
    "line,error",
    [
        # Zephyr shell_error(): bold red, newline inside the coloured span.
        (
            b"\x1b[1;31mFailed to cut DUT power: -5\r\n\x1b[m",
            b"Failed to cut DUT power: -5",
        ),
        (
            b"\x1b[1;31mFailed to cut DUT power: -5\x1b[0m\r\n",
            b"Failed to cut DUT power: -5",
        ),
        # Anything in the error colour counts, even if not in the text list.
        (
            b"\x1b[1;31mH2H flash is busy\r\n\x1b[m",
            b"H2H flash is busy",
        ),
        # Colours off: known messages.
        (b"Failed to cut DUT power: -5\r\n", b"Failed to cut DUT power: -5"),
        (b"Invalid argument: foo\r\n", b"Invalid argument: foo"),
        (b"Usage: power_dut <on|off|cycle>\r\n", b"Usage: power_dut <on|off|cycle>"),
        (
            b"Unknown channel 'X' (not available on this board)\r\n",
            b"Unknown channel 'X' (not available on this board)",
        ),
        (
            b"No temperature sensor configured\r\n",
            b"No temperature sensor configured",
        ),
        (b"PDC device not ready\r\n", b"PDC device not ready"),
        (b"power_dut: command not found\r\n", b"power_dut: command not found"),
        (b"led: wrong parameter count\r\n", b"led: wrong parameter count"),
    ],
)
def test_fw_error_regex_detects_errors(line, error):
    match = _search(r"DUT Power: OFF", b"power_dut off\r\n" + line)
    assert match.group("maui_error") == error


def test_fw_error_regex_waits_for_full_line():
    # The shell flushes output in small chunks; a partial error line must
    # not match yet (it would truncate the error message).
    output = b"power_dut off\r\n\x1b[1;31mFailed to cut D"
    assert _search(r"DUT Power: OFF", output) is None


@pytest.mark.parametrize(
    "log_line",
    [
        b"[00:00:01.234,000] <err> tps6699x: Failed to read reg\r\n",
        # Colours off: nothing between the timestamp and the message.
        b"[00:00:05.123,000] <err> adc: ADC controller for channel X is not ready\r\n",
        # Coloured log line.
        b"\x1b[1;33m[00:00:05.100,000] <wrn> sbu_mux: PDC device not ready\r\n",
        # Log line without timestamp, coloured as an error.
        b"\x1b[1;31m<err> adc: ADC controller is not ready\r\n",
    ],
)
def test_fw_error_regex_ignores_log_lines(log_line):
    output = b"adc read X\r\n" + log_line + b"[X] = 5012 mV\r\n"
    match = _search(r"\[X\] = (-?\d+) mV", output)
    assert match.group(1) == b"5012"
    assert match.group("maui_error") is None


def test_fw_error_regex_ignores_echo():
    assert _search(r"DUT Power: OFF", b"power_dut off\r\n") is None
