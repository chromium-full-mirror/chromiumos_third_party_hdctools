# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for ec3po interpreter."""

import select
from unittest import mock

from ec3po import interpreter


class MockFd:
    def __init__(self, fd):
        self.fd = fd
        self.close_called = False

    def fileno(self):
        return self.fd

    def close(self):
        self.close_called = True


@mock.patch("select.epoll")
def test_interpreter_start_loop(mock_epoll):
    mock_interp = mock.Mock()
    mock_interp.logger = mock.Mock()
    mock_interp.cmd_pipe = MockFd(101)
    mock_interp.dbg_pipe = MockFd(102)
    mock_interp.ec_uart_pty = MockFd(103)
    mock_interp.inputs = [
        mock_interp.cmd_pipe,
        mock_interp.dbg_pipe,
        mock_interp.ec_uart_pty,
    ]
    mock_interp.outputs = []

    mock_epoll_instance = mock.Mock()
    mock_epoll_instance.__enter__ = mock.Mock(return_value=mock_epoll_instance)
    mock_epoll_instance.__exit__ = mock.Mock()
    mock_epoll.return_value = mock_epoll_instance

    shutdown_pipe = MockFd(99)

    def poll_side_effect(*_args, **kwargs):
        _timeout = kwargs.get("timeout", _args[0] if _args else None)
        if not hasattr(poll_side_effect, "called_101"):
            poll_side_effect.called_101 = True
            return [(101, select.EPOLLIN)]
        if not hasattr(poll_side_effect, "called_103"):
            poll_side_effect.called_103 = True
            return [(103, select.EPOLLIN)]
        return [(99, select.EPOLLIN)]

    mock_epoll_instance.poll.side_effect = poll_side_effect

    interpreter.start_loop(mock_interp, shutdown_pipe)

    mock_interp.handle_user_data.assert_called_once()
    mock_interp.handle_ec_data.assert_called_once()


@mock.patch("select.epoll")
def test_interpreter_start_loop_error_handling(mock_epoll):
    mock_interp = mock.Mock()
    mock_interp.logger = mock.Mock()
    mock_interp.cmd_pipe = MockFd(101)
    mock_interp.dbg_pipe = MockFd(102)
    mock_interp.ec_uart_pty = MockFd(103)
    mock_interp.inputs = [
        mock_interp.cmd_pipe,
        mock_interp.dbg_pipe,
        mock_interp.ec_uart_pty,
    ]
    mock_interp.outputs = []

    mock_epoll_instance = mock.Mock()
    mock_epoll_instance.__enter__ = mock.Mock(return_value=mock_epoll_instance)
    mock_epoll_instance.__exit__ = mock.Mock()
    mock_epoll.return_value = mock_epoll_instance

    mock_interp.handle_user_data.side_effect = EOFError("test eof")

    def poll_side_effect(*_args, **kwargs):
        _timeout = kwargs.get("timeout", _args[0] if _args else None)
        if not hasattr(poll_side_effect, "called_101"):
            poll_side_effect.called_101 = True
            return [(101, select.EPOLLIN)]
        return [(99, select.EPOLLIN)]

    mock_epoll_instance.poll.side_effect = poll_side_effect

    shutdown_pipe = MockFd(99)

    interpreter.start_loop(mock_interp, shutdown_pipe)

    mock_interp.handle_user_data.assert_called_once()


@mock.patch("select.epoll")
def test_interpreter_start_loop_oserror(mock_epoll):
    mock_interp = mock.Mock()
    mock_interp.logger = mock.Mock()
    mock_interp.cmd_pipe = MockFd(101)
    mock_interp.dbg_pipe = MockFd(102)
    mock_interp.ec_uart_pty = MockFd(103)
    mock_interp.inputs = [
        mock_interp.cmd_pipe,
        mock_interp.dbg_pipe,
        mock_interp.ec_uart_pty,
    ]
    mock_interp.outputs = []

    mock_epoll_instance = mock.Mock()
    mock_epoll_instance.__enter__ = mock.Mock(return_value=mock_epoll_instance)
    mock_epoll_instance.__exit__ = mock.Mock()
    mock_epoll.return_value = mock_epoll_instance

    mock_interp.handle_ec_data.side_effect = OSError("test oserror")
    mock_interp.handle_user_data.side_effect = EOFError("test eof")

    def poll_side_effect(*_args, **kwargs):
        _timeout = kwargs.get("timeout", _args[0] if _args else None)
        if not hasattr(poll_side_effect, "called_103"):
            poll_side_effect.called_103 = True
            return [(103, select.EPOLLIN)]
        if not hasattr(poll_side_effect, "called_101"):
            poll_side_effect.called_101 = True
            return [(101, select.EPOLLIN)]
        return [(99, select.EPOLLIN)]

    mock_epoll_instance.poll.side_effect = poll_side_effect

    shutdown_pipe = MockFd(99)

    interpreter.start_loop(mock_interp, shutdown_pipe)

    mock_interp.handle_ec_data.assert_called_once()
    mock_interp.handle_user_data.assert_called_once()
