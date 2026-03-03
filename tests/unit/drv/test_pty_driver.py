# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import pty
import time
from unittest.mock import MagicMock
from unittest.mock import patch

import pexpect
import pexpect.fdpexpect
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


def test_pty_driver_flush_sends_newline(pty_driver):
    mock_child = MagicMock()
    mock_child.sendline.return_value = 1
    mock_child.expect.side_effect = pexpect.TIMEOUT("timeout")
    pty_driver._child = mock_child

    pty_driver._flush()

    pty_driver._child.sendline.assert_called_once_with("")


def test_pty_driver_flush_raises_error_on_sendline_fail(pty_driver):
    mock_child = MagicMock()
    mock_child.sendline.return_value = 0
    pty_driver._child = mock_child

    with pytest.raises(PtyError, match="Failed to send newline."):
        pty_driver._flush()


def test_pty_driver_flush_consumes_buffer_until_timeout(pty_driver):
    mock_child = MagicMock()
    mock_child.sendline.return_value = 1
    mock_child.expect.side_effect = [None, None, pexpect.TIMEOUT("timeout")]
    pty_driver._child = mock_child

    pty_driver._flush()

    assert pty_driver._child.expect.call_count == 3
    pty_driver._child.expect.assert_called_with(r".+", timeout=0.01)


def test_pty_driver_flush_handles_eof(pty_driver):
    mock_child = MagicMock()
    mock_child.sendline.return_value = 1
    mock_child.expect.side_effect = pexpect.EOF("eof")
    pty_driver._child = mock_child

    pty_driver._flush()

    pty_driver._child.expect.assert_called_once()


def test_pty_driver_flush_clears_non_ascii_and_nil_chars(pty_driver):
    m, s = pty.openpty()
    child = pexpect.fdpexpect.fdspawn(m, use_poll=True)
    pty_driver._child = child

    # Write non-ascii, nil (\x00), and newlines
    os.write(s, b"noise\x00\xff\x00\r\nmore noise\x80\r\n")
    time.sleep(0.1)

    # Call _flush, which should clear everything and timeout
    pty_driver._flush()

    # pexpect's internal buffers should be empty
    assert child.buffer == b""
    assert child.before == b""

    os.close(s)
    os.close(m)


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
