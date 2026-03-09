# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import signal
import subprocess
from unittest import mock

import pytest

from servo.common import terminal_freezer


@pytest.fixture(name="mock_sys_interface")
def mock_sys_interface_fixture():
    with mock.patch("servo.common.terminal_freezer.sys_interface") as m:
        yield m


@pytest.fixture(name="mock_kill")
def mock_kill_fixture():
    with mock.patch("servo.common.terminal_freezer.os.kill") as m:
        yield m


@pytest.fixture(name="unused_mock_sleep")
def unused_mock_sleep_fixture():
    with mock.patch("servo.common.terminal_freezer.time.sleep") as m:
        yield m


def test_pid_namespace_used(tmp_path):
    # pylint: disable=unused-argument
    with mock.patch(
        "builtins.open", mock.mock_open(read_data="cros_sdk --something\n")
    ):
        assert terminal_freezer.pid_namespace_used() is True

    with mock.patch("builtins.open", mock.mock_open(read_data="other_command\n")):
        assert terminal_freezer.pid_namespace_used() is False


@mock.patch("servo.common.terminal_freezer.pid_namespace_used", return_value=True)
def test_terminal_freezer_init_warning(unused_mock_pid_ns, caplog):
    _tf = terminal_freezer.TerminalFreezer("/dev/pts/1")
    assert "This chroot was not entered with" in caplog.text


@mock.patch("builtins.open", mock.mock_open(read_data="bash\n"))
def test_terminal_freezer_enter_exit(mock_sys_interface, mock_kill, unused_mock_sleep):
    mock_sys_interface.check_output.return_value = "p1234\nR5678\n"
    tf = terminal_freezer.TerminalFreezer("/dev/pts/1")

    with tf:
        mock_sys_interface.check_output.assert_called_with(
            ["lsof", "-FR", "/dev/pts/1"], stderr=subprocess.STDOUT, encoding="utf-8"
        )
        # 5678 should be stopped first because of reversed()
        mock_kill.assert_has_calls(
            [
                mock.call(5678, signal.SIGSTOP),
                mock.call(1234, signal.SIGSTOP),
            ]
        )

    mock_kill.assert_has_calls(
        [
            mock.call(1234, signal.SIGCONT),
            mock.call(5678, signal.SIGCONT),
        ]
    )


@mock.patch("builtins.open", mock.mock_open(read_data="servod --board=foo\n"))
def test_terminal_freezer_ignores_servod(
    mock_sys_interface, mock_kill, unused_mock_sleep
):
    mock_sys_interface.check_output.return_value = "p1234\n"
    tf = terminal_freezer.TerminalFreezer("/dev/pts/1")

    with tf:
        mock_kill.assert_not_called()


@mock.patch("builtins.open", mock.mock_open(read_data="bash\n"))
def test_terminal_freezer_lsof_fails(mock_sys_interface, mock_kill, unused_mock_sleep):
    mock_sys_interface.check_output.side_effect = subprocess.CalledProcessError(
        1, "lsof"
    )
    tf = terminal_freezer.TerminalFreezer("/dev/pts/1")

    with tf:
        mock_kill.assert_not_called()


@mock.patch("builtins.open", mock.mock_open(read_data="bash\n"))
def test_terminal_freezer_os_kill_fails_enter(
    mock_sys_interface, mock_kill, unused_mock_sleep
):
    mock_sys_interface.check_output.return_value = "p1234\n"
    mock_kill.side_effect = OSError("Permission denied")
    tf = terminal_freezer.TerminalFreezer("/dev/pts/1")

    with pytest.raises(OSError):
        with tf:
            pass


@mock.patch("builtins.open", mock.mock_open(read_data="bash\n"))
def test_terminal_freezer_os_kill_fails_exit(
    mock_sys_interface, mock_kill, unused_mock_sleep, caplog
):
    mock_sys_interface.check_output.return_value = "p1234\n"
    tf = terminal_freezer.TerminalFreezer("/dev/pts/1")

    # Kill works on enter, fails on exit
    def kill_side_effect(unused_pid, sig):
        if sig == signal.SIGCONT:
            raise OSError("No such process")

    mock_kill.side_effect = kill_side_effect

    with tf:
        pass

    assert "Error when trying to unfreeze process 1234" in caplog.text
