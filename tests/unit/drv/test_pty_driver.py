# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from servo.drv.pty_driver import PtyDriver
from servo.drv.pty_driver import PtyError


@pytest.fixture
def pty_driver():
    mock_interface = MagicMock()
    mock_interface.get.return_value = "/dev/pts/999"
    # Basic params
    params = {"cmd": "get"}
    with patch("servo.drv.pty_driver.PtyDriver._open"):
        driver = PtyDriver(
            ("localhost", 9999), ("localhost", 9998), mock_interface, params
        )
    return driver


@patch("servo.drv.pty_driver.PtyDriver._Get_uart_timeout", return_value=3)
def test_pty_driver_get_timeout(mock_get, pty_driver):
    assert pty_driver._Get_uart_timeout() == 3


@patch("servo.drv.pty_driver.PtyDriver._Get_uart_timeout", return_value=5.0)
@patch("servo.drv.pty_driver.PtyDriver._Set_uart_timeout")
def test_pty_driver_set_timeout(mock_set, mock_get, pty_driver):
    pty_driver._Set_uart_timeout(5.0)
    assert pty_driver._Get_uart_timeout() == 5.0


@patch("servo.drv.pty_driver.sys_interface.open", return_value=1)
def test_pty_driver_flush(mock_open, pty_driver):
    mock_child = MagicMock()
    mock_child.sendline.return_value = 1
    pty_driver._child = mock_child

    # Test success
    pty_driver._flush()
    mock_child.sendline.assert_called_with("")
    mock_child.expect.assert_called()


def test_pty_driver_make_xml_friendly(pty_driver):
    # member.decode() requires bytes
    res = pty_driver._make_xml_friendly(b"good\x00bad")
    assert "good" in res and "bad" in res
    assert "\x00" not in res


@patch("servo.drv.pty_driver.fdpexpect.fdspawn")
@patch("servo.drv.pty_driver.sys_interface.open", return_value=1)
@patch("servo.drv.pty_driver.PtyDriver._flush")
@patch("servo.drv.pty_driver.PtyDriver._send")
def test_pty_driver_issue_cmd_get_results(
    mock_send, mock_flush, mock_open, mock_fdspawn, pty_driver
):
    mock_child = MagicMock()
    mock_fdspawn.return_value = mock_child
    mock_child.sendline.return_value = 1

    # Setup mock to return a match
    mock_match = MagicMock()
    mock_match.lastindex = 0
    mock_match.group.return_value = (b"match_text",)
    mock_child.match = mock_match

    result = pty_driver._issue_cmd_get_results("test_cmd", ["regex1"])
    assert result == [("match_text",)]
    mock_send.assert_called_with("test_cmd", flush=1)


@patch("servo.drv.pty_driver.fdpexpect.fdspawn")
@patch("servo.drv.pty_driver.sys_interface.open", return_value=1)
@patch("servo.drv.pty_driver.PtyDriver._flush")
@patch("servo.drv.pty_driver.PtyDriver._send")
def test_pty_driver_issue_cmd_get_results_timeout(
    mock_send, mock_flush, mock_open, mock_fdspawn, pty_driver
):
    mock_child = MagicMock()
    mock_fdspawn.return_value = mock_child
    mock_child.sendline.return_value = 1
    mock_child.before = b"partial output"

    import pexpect

    # Setup mock to timeout
    mock_child.expect.side_effect = pexpect.TIMEOUT("timeout")

    with pytest.raises(PtyError, match="Timeout waiting for response"):
        pty_driver._issue_cmd_get_results("test_cmd", ["regex1"])
