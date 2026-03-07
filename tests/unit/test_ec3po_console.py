# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for ec3po console loop."""

import select
from unittest import mock

from ec3po import console


@mock.patch("select.epoll")
@mock.patch("ec3po.console.sys_interface.read")
@mock.patch("ec3po.console.sys_interface.close")
def test_console_start_loop_controller(_mock_close, mock_read, mock_epoll):
    mock_console = mock.Mock()
    mock_console.logger = mock.Mock()
    mock_console.controller_pty = 101
    mock_console.interface_pty = 102
    mock_console.user_pty = 103
    mock_console.is_tokenized = False
    mock_console.cmd_pipe = mock.Mock()
    mock_console.dbg_pipe = mock.Mock()
    mock_console.oobm_queue.empty.return_value = True

    mock_command_active = mock.Mock()
    mock_command_active.value = False

    mock_epoll_instance = mock.Mock()
    mock_epoll_instance.__enter__ = mock.Mock(return_value=mock_epoll_instance)
    mock_epoll_instance.__exit__ = mock.Mock()
    mock_epoll.return_value = mock_epoll_instance

    shutdown_pipe = mock.Mock()
    shutdown_pipe.fileno.return_value = 99

    mock_read.return_value = b"testdata"

    def poll_side_effect(*_args, **kwargs):
        _timeout = kwargs.get("timeout", _args[0] if _args else None)
        if _timeout == 0:
            return []

        if not hasattr(poll_side_effect, "called"):
            poll_side_effect.called = True
            return [(mock_console.controller_pty, select.EPOLLIN)]
        return [(99, select.EPOLLIN)]

    mock_epoll_instance.poll.side_effect = poll_side_effect

    console.start_loop(mock_console, mock_command_active, shutdown_pipe)

    mock_read.assert_called_once_with(101, mock.ANY)
    _mock_close.assert_any_call(101)


@mock.patch("select.epoll")
@mock.patch("ec3po.console.sys_interface.read")
@mock.patch("ec3po.console.sys_interface.close")
def test_console_start_loop_interface(_mock_close, mock_read, mock_epoll):
    mock_console = mock.Mock()
    mock_console.logger = mock.Mock()
    mock_console.controller_pty = 101
    mock_console.interface_pty = 102
    mock_console.user_pty = 103
    mock_console.cmd_pipe = mock.Mock()
    mock_console.dbg_pipe = mock.Mock()
    mock_console.oobm_queue.empty.return_value = True

    mock_command_active = mock.Mock()
    mock_command_active.value = True

    mock_epoll_instance = mock.Mock()
    mock_epoll_instance.__enter__ = mock.Mock(return_value=mock_epoll_instance)
    mock_epoll_instance.__exit__ = mock.Mock()
    mock_epoll.return_value = mock_epoll_instance

    shutdown_pipe = mock.Mock()
    shutdown_pipe.fileno.return_value = 99

    mock_read.return_value = b"x"

    def poll_side_effect(*_args, **kwargs):
        _timeout = kwargs.get("timeout", _args[0] if _args else None)
        if _timeout == 0:
            return []

        if not hasattr(poll_side_effect, "called"):
            poll_side_effect.called = True
            return [(mock_console.interface_pty, select.EPOLLIN)]
        return [(99, select.EPOLLIN)]

    mock_epoll_instance.poll.side_effect = poll_side_effect

    console.start_loop(mock_console, mock_command_active, shutdown_pipe)

    mock_console.handle_char.assert_called_once_with(ord(b"x"))


@mock.patch("select.epoll")
@mock.patch("ec3po.console.sys_interface.read")
@mock.patch("ec3po.console.sys_interface.close")
def test_console_start_loop_interface_eof(_mock_close, mock_read, mock_epoll):
    mock_console = mock.Mock()
    mock_console.logger = mock.Mock()
    mock_console.controller_pty = 101
    mock_console.interface_pty = 102
    mock_console.user_pty = 103
    mock_console.cmd_pipe = mock.Mock()
    mock_console.dbg_pipe = mock.Mock()
    mock_console.oobm_queue.empty.return_value = True

    mock_command_active = mock.Mock()
    mock_command_active.value = True

    mock_epoll_instance = mock.Mock()
    mock_epoll_instance.__enter__ = mock.Mock(return_value=mock_epoll_instance)
    mock_epoll_instance.__exit__ = mock.Mock()
    mock_epoll.return_value = mock_epoll_instance

    shutdown_pipe = mock.Mock()
    shutdown_pipe.fileno.return_value = 99

    mock_read.return_value = b"x"
    mock_console.handle_char.side_effect = EOFError("test eof")

    def poll_side_effect(*_args, **kwargs):
        _timeout = kwargs.get("timeout", _args[0] if _args else None)
        if _timeout == 0:
            return []

        if not hasattr(poll_side_effect, "called"):
            poll_side_effect.called = True
            return [(mock_console.interface_pty, select.EPOLLIN)]
        return [(99, select.EPOLLIN)]

    mock_epoll_instance.poll.side_effect = poll_side_effect

    console.start_loop(mock_console, mock_command_active, shutdown_pipe)

    mock_console.handle_char.assert_called_once_with(ord(b"x"))


@mock.patch("select.epoll")
@mock.patch("ec3po.console.sys_interface.read")
@mock.patch("ec3po.console.sys_interface.close")
def test_console_start_loop_interface_oserror(_mock_close, mock_read, mock_epoll):
    mock_console = mock.Mock()
    mock_console.logger = mock.Mock()
    mock_console.controller_pty = 101
    mock_console.interface_pty = 102
    mock_console.user_pty = 103
    mock_console.cmd_pipe = mock.Mock()
    mock_console.dbg_pipe = mock.Mock()
    mock_console.oobm_queue.empty.return_value = True

    mock_command_active = mock.Mock()
    mock_command_active.value = True

    mock_epoll_instance = mock.Mock()
    mock_epoll_instance.__enter__ = mock.Mock(return_value=mock_epoll_instance)
    mock_epoll_instance.__exit__ = mock.Mock()
    mock_epoll.return_value = mock_epoll_instance

    shutdown_pipe = mock.Mock()
    shutdown_pipe.fileno.return_value = 99

    mock_read.return_value = b"x"
    mock_console.handle_char.side_effect = OSError("test oserror")

    def poll_side_effect(*_args, **kwargs):
        _timeout = kwargs.get("timeout", _args[0] if _args else None)
        if _timeout == 0:
            return []

        if not hasattr(poll_side_effect, "called"):
            poll_side_effect.called = True
            return [(mock_console.interface_pty, select.EPOLLIN)]
        return [(99, select.EPOLLIN)]

    mock_epoll_instance.poll.side_effect = poll_side_effect

    console.start_loop(mock_console, mock_command_active, shutdown_pipe)

    mock_console.handle_char.assert_called_once_with(ord(b"x"))
