# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for PtyDriver."""

import errno
import logging
from unittest import mock

import pexpect
import pytest

from servo_updater.ecusb import pty_driver


@pytest.fixture(name="mock_interface")
def _mock_interface():
    interface = mock.Mock()
    interface.get_pty.return_value = "/dev/pts/99"
    return interface


@pytest.fixture(name="pty_drv")
def _pty_drv(mock_interface):
    return pty_driver.PtyDriver(mock_interface, [])


@mock.patch("servo_updater.ecusb.pty_driver.os.open")
@mock.patch("servo_updater.ecusb.pty_driver.fcntl.fcntl")
@mock.patch("servo_updater.ecusb.pty_driver.fdpexpect.fdspawn")
@mock.patch("servo_updater.ecusb.pty_driver.time.sleep")
def test_open_close(
    unused_mock_sleep, mock_fdspawn, unused_mock_fcntl, mock_open, pty_drv
):
    mock_open.return_value = 123
    mock_child = mock.Mock()
    mock_fdspawn.return_value = mock_child

    pty_drv._open()
    mock_open.assert_called_once_with("/dev/pts/99", mock.ANY)
    mock_fdspawn.assert_called_once_with(123)
    assert pty_drv._fd == 123
    assert pty_drv._child == mock_child

    pty_drv._close()
    mock_child.close.assert_called_once()
    assert pty_drv._fd is None
    assert pty_drv._child is None


@mock.patch("servo_updater.ecusb.pty_driver.os.open", return_value=123)
@mock.patch("servo_updater.ecusb.pty_driver.fcntl.fcntl")
@mock.patch("servo_updater.ecusb.pty_driver.fdpexpect.fdspawn")
@mock.patch("servo_updater.ecusb.pty_driver.time.sleep")
@mock.patch("servo_updater.ecusb.pty_driver.os.close")
def test_close_handles_ebadf(
    mock_os_close,
    unused_mock_sleep,
    mock_fdspawn,
    unused_mock_fcntl,
    unused_mock_open,
    pty_drv,
    caplog,
):
    """Verify that EBADF during os.close is silently handled."""
    mock_child = mock.Mock()
    mock_fdspawn.return_value = mock_child

    pty_drv._open()

    # Simulate os.close raising EBADF
    mock_os_close.side_effect = OSError(errno.EBADF, "Bad file descriptor")

    with caplog.at_level(logging.DEBUG):
        pty_drv._close()

    # The exception should be caught and not re-raised
    mock_os_close.assert_called_once_with(123)
    # The EBADF error shouldn't be logged because it's expected
    assert "Error closing fd 123" not in caplog.text


@mock.patch("servo_updater.ecusb.pty_driver.os.open", return_value=123)
@mock.patch("servo_updater.ecusb.pty_driver.fcntl.fcntl")
@mock.patch("servo_updater.ecusb.pty_driver.fdpexpect.fdspawn")
@mock.patch("servo_updater.ecusb.pty_driver.time.sleep")
@mock.patch("servo_updater.ecusb.pty_driver.os.close")
# pylint: disable=unused-argument
def test_close_raises_other_oserror(
    mock_os_close,
    unused_mock_sleep,
    mock_fdspawn,
    unused_mock_fcntl,
    unused_mock_open,
    pty_drv,
    caplog,
):
    """Verify that non-EBADF OSError is re-raised."""
    mock_child = mock.Mock()
    mock_fdspawn.return_value = mock_child

    pty_drv._open()

    # Simulate os.close raising EIO
    mock_os_close.side_effect = OSError(errno.EIO, "I/O error")

    with pytest.raises(OSError):
        pty_drv._close()


@mock.patch("servo_updater.ecusb.pty_driver.os.open", return_value=123)
@mock.patch("servo_updater.ecusb.pty_driver.fcntl.fcntl")
@mock.patch("servo_updater.ecusb.pty_driver.fdpexpect.fdspawn")
@mock.patch("servo_updater.ecusb.pty_driver.time.sleep")
def test_flush(
    unused_mock_sleep, mock_fdspawn, unused_mock_fcntl, unused_mock_open, pty_drv
):
    mock_child = mock.Mock()
    mock_child.sendline.return_value = 1
    mock_fdspawn.return_value = mock_child

    # Simulate expect timing out immediately, which ends flush
    mock_child.expect.side_effect = pexpect.TIMEOUT("timeout")

    pty_drv._open()
    pty_drv._flush()

    mock_child.sendline.assert_called_with("")
    mock_child.expect.assert_called()


@mock.patch("servo_updater.ecusb.pty_driver.os.open", return_value=123)
@mock.patch("servo_updater.ecusb.pty_driver.fcntl.fcntl")
@mock.patch("servo_updater.ecusb.pty_driver.fdpexpect.fdspawn")
@mock.patch("servo_updater.ecusb.pty_driver.time.sleep")
def test_send_failure(
    unused_mock_sleep, mock_fdspawn, unused_mock_fcntl, unused_mock_open, pty_drv
):
    mock_child = mock.Mock()
    # sendline returns 0 instead of len(cmd) + 1
    mock_child.sendline.return_value = 0
    mock_fdspawn.return_value = mock_child

    mock_child.expect.side_effect = pexpect.TIMEOUT("timeout")
    pty_drv._open()

    with pytest.raises(pty_driver.PtyError, match="Failed to send newline."):
        pty_drv._send("testcmd")


@mock.patch("servo_updater.ecusb.pty_driver.os.open", return_value=123)
@mock.patch("servo_updater.ecusb.pty_driver.fcntl.fcntl")
@mock.patch("servo_updater.ecusb.pty_driver.fdpexpect.fdspawn")
@mock.patch("servo_updater.ecusb.pty_driver.time.sleep")
def test_issue_cmd_get_results(
    unused_mock_sleep, mock_fdspawn, unused_mock_fcntl, unused_mock_open, pty_drv
):
    mock_child = mock.Mock()

    def fake_sendline(cmd):
        return len(cmd) + 1

    mock_child.sendline.side_effect = fake_sendline

    # Setup the match object returned by expect
    mock_match = mock.Mock()
    mock_match.lastindex = 2
    mock_match.group.return_value = (b"matched_string", b"group1", b"group2")
    mock_child.match = mock_match

    mock_fdspawn.return_value = mock_child

    # first expect is inside _flush and should timeout to exit flush loop
    # second expect is our actual expect
    mock_child.expect.side_effect = [pexpect.TIMEOUT("timeout"), None]

    results = pty_drv._issue_cmd_get_results("mycmd", ["myregex"])

    assert len(results) == 1
    assert results[0] == ("matched_string", "group1", "group2")


@mock.patch("servo_updater.ecusb.pty_driver.os.open", return_value=123)
@mock.patch("servo_updater.ecusb.pty_driver.fcntl.fcntl")
@mock.patch("servo_updater.ecusb.pty_driver.fdpexpect.fdspawn")
@mock.patch("servo_updater.ecusb.pty_driver.time.sleep")
def test_issue_cmd_get_multi_results(
    unused_mock_sleep, mock_fdspawn, unused_mock_fcntl, unused_mock_open, pty_drv
):
    mock_child = mock.Mock()

    def fake_sendline(cmd):
        return len(cmd) + 1

    mock_child.sendline.side_effect = fake_sendline

    mock_match = mock.Mock()
    mock_match.lastindex = 1
    mock_match.group.return_value = (b"match1", b"g1")

    mock_child.match = mock_match
    mock_fdspawn.return_value = mock_child

    # flush timeout, then two matches, then timeout to break loop
    mock_child.expect.side_effect = [
        pexpect.TIMEOUT("timeout"),
        None,
        None,
        pexpect.TIMEOUT("timeout"),
    ]

    results = pty_drv._issue_cmd_get_multi_results("mycmd", "myregex")

    assert len(results) == 2
    assert results[0] == ("match1", "g1")
    assert results[1] == ("match1", "g1")


def test_uart_setters_getters(pty_drv):
    pty_drv._set_uart_timeout(5)
    assert pty_drv._get_uart_timeout() == 5

    pty_drv._set_uart_regexp("['regex1', 'regex2']")
    assert pty_drv._get_uart_regexp() == "['regex1', 'regex2']"

    with pytest.raises(pty_driver.PtyError):
        pty_drv._set_uart_regexp(123)

    pty_drv._set_uart_capture(True)
    pty_drv._interface.set_capture_active.assert_called_with(True)

    pty_drv._get_uart_capture()
    pty_drv._interface.get_capture_active.assert_called_once()

    pty_drv._get_uart_stream()
    pty_drv._interface.get_stream.assert_called_once()


@mock.patch.object(pty_driver.PtyDriver, "_issue_cmd_get_results")
@mock.patch.object(pty_driver.PtyDriver, "_issue_cmd")
def test_set_uart_cmd(mock_issue_cmd, mock_issue_cmd_get_results, pty_drv):
    pty_drv._dict["uart_regexp"] = None
    pty_drv._set_uart_cmd("cmd1")
    mock_issue_cmd.assert_called_with("cmd1")
    assert pty_drv._get_uart_cmd() == "None"

    pty_drv._dict["uart_regexp"] = ["regex"]
    pty_drv._dict["uart_timeout"] = 3
    mock_issue_cmd_get_results.return_value = [("match",)]
    pty_drv._set_uart_cmd("cmd2")
    mock_issue_cmd_get_results.assert_called_with("cmd2", ["regex"], 3)
    assert pty_drv._get_uart_cmd() == "[('match',)]"


@mock.patch.object(pty_driver.PtyDriver, "_issue_cmd")
def test_set_uart_multicmd(mock_issue_cmd, pty_drv):
    pty_drv._set_uart_multicmd("cmd1;cmd2")
    mock_issue_cmd.assert_called_with(["cmd1", "cmd2"])
