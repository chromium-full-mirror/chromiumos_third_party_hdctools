# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# pylint: disable=line-too-long, redefined-outer-name
import multiprocessing
import select
import unittest.mock

import pytest

from ec3po import console


@pytest.fixture
def console_mock_fixture():
    c = unittest.mock.MagicMock()
    c.controller_pty = 11
    c.interface_pty = 12

    class MockCmdPipe:
        def fileno(self):
            return 13

        def recv(self):
            return b""

        def close(self):
            pass

    c.cmd_pipe = MockCmdPipe()
    c.cmd_pipe.recv = unittest.mock.MagicMock()
    c.cmd_pipe.close = unittest.mock.MagicMock()

    class MockDbgPipe:
        def fileno(self):
            return 14

        def recv(self):
            return b""

        def close(self):
            pass

    c.dbg_pipe = MockDbgPipe()
    c.dbg_pipe.recv = unittest.mock.MagicMock()
    c.dbg_pipe.close = unittest.mock.MagicMock()

    c.user_pty = "pty0"
    c.logger = unittest.mock.MagicMock()
    c.oobm_queue.empty.return_value = True
    c.raw_debug = False
    c.interrogation_mode = b"never"
    c.is_tokenized = False
    return c


@unittest.mock.patch("ec3po.console.select.epoll")
@unittest.mock.patch("ec3po.console.sys_interface")
def test_start_loop_shutdown_pipe(mock_sys_intf, mock_epoll, console_mock_fixture):
    command_active = multiprocessing.Value("b", False)

    shutdown_pipe = unittest.mock.MagicMock()
    shutdown_pipe.fileno.return_value = 15

    epoll_outer = unittest.mock.MagicMock()
    epoll_inner = unittest.mock.MagicMock()
    mock_epoll.side_effect = [epoll_outer, epoll_inner]

    # Outer epoll is used for checking if controller connected
    epoll_outer.poll.return_value = []

    # Inner epoll is used for actual reading
    # Let's say it polls and returns that shutdown_pipe is ready
    epoll_inner.poll.return_value = [(15, select.EPOLLIN)]

    # Needs to enter the inner epoll context manager
    epoll_inner.__enter__.return_value = epoll_inner

    console.start_loop(
        console_mock_fixture, command_active, shutdown_pipe=shutdown_pipe
    )

    # Ensure unregister was called
    epoll_outer.unregister.assert_called_once_with(11)

    # Ensure all pipes closed
    console_mock_fixture.dbg_pipe.close.assert_called_once()
    console_mock_fixture.cmd_pipe.close.assert_called_once()
    shutdown_pipe.close.assert_called_once()
    mock_sys_intf.close.assert_any_call(11)
    mock_sys_intf.close.assert_any_call(12)


@unittest.mock.patch("ec3po.console.select.epoll")
@unittest.mock.patch("ec3po.console.sys_interface")
def test_start_loop_keyboard_interrupt(
    unused_mock_sys_intf, mock_epoll, console_mock_fixture
):
    command_active = multiprocessing.Value("b", False)
    epoll_outer = unittest.mock.MagicMock()
    mock_epoll.return_value = epoll_outer
    epoll_outer.register.side_effect = KeyboardInterrupt()

    console.start_loop(console_mock_fixture, command_active)

    # Just checking it handles the keyboard interrupt gracefully and cleans up
    console_mock_fixture.dbg_pipe.close.assert_called_once()


@unittest.mock.patch("ec3po.console.select.epoll")
@unittest.mock.patch("ec3po.console.sys_interface")
def test_start_loop_read_controller_pty(
    mock_sys_intf, mock_epoll, console_mock_fixture
):
    command_active = multiprocessing.Value("b", False)

    epoll_outer = unittest.mock.MagicMock()
    epoll_inner = unittest.mock.MagicMock()

    # Provide multiple epolls: outer, inner (first loop), inner (second loop for exit)
    epoll_inner_2 = unittest.mock.MagicMock()
    mock_epoll.side_effect = [epoll_outer, epoll_inner, epoll_inner_2]

    epoll_outer.poll.return_value = []  # controller_connected = True

    # First loop read controller pty
    epoll_inner.poll.return_value = [(11, select.EPOLLIN)]
    epoll_inner.__enter__.return_value = epoll_inner

    mock_sys_intf.read.return_value = b"hi"

    # Second loop fake shutdown by raising EOF on read
    epoll_inner_2.poll.return_value = [(11, select.EPOLLIN)]
    epoll_inner_2.__enter__.return_value = epoll_inner_2

    def handle_char_side_effect(unused_c):
        if console_mock_fixture.handle_char.call_count == 2:
            raise EOFError()

    console_mock_fixture.handle_char.side_effect = handle_char_side_effect

    console.start_loop(console_mock_fixture, command_active)

    mock_sys_intf.read.assert_called_with(11, console.CONSOLE_MAX_READ)
    console_mock_fixture.handle_char.assert_called()


@unittest.mock.patch("ec3po.console.select.epoll")
@unittest.mock.patch("ec3po.console.sys_interface")
def test_start_loop_read_interface_pty(mock_sys_intf, mock_epoll, console_mock_fixture):
    command_active = multiprocessing.Value("b", True)  # command active!

    epoll_outer = unittest.mock.MagicMock()
    epoll_inner = unittest.mock.MagicMock()
    epoll_inner_2 = unittest.mock.MagicMock()
    mock_epoll.side_effect = [epoll_outer, epoll_inner, epoll_inner_2]

    epoll_outer.poll.return_value = []

    epoll_inner.poll.return_value = [(12, select.EPOLLIN)]
    epoll_inner.__enter__.return_value = epoll_inner
    mock_sys_intf.read.return_value = b"h"

    epoll_inner_2.poll.return_value = [(12, select.EPOLLIN)]
    epoll_inner_2.__enter__.return_value = epoll_inner_2

    console_mock_fixture.handle_char.side_effect = EOFError()

    console.start_loop(console_mock_fixture, command_active)
    mock_sys_intf.read.assert_called_with(12, console.CONSOLE_MAX_READ)


@unittest.mock.patch("ec3po.console.select.epoll")
@unittest.mock.patch("ec3po.console.sys_interface")
def test_start_loop_read_cmd_pipe(mock_sys_intf, mock_epoll, console_mock_fixture):
    command_active = multiprocessing.Value("b", False)

    epoll_outer = unittest.mock.MagicMock()
    epoll_inner = unittest.mock.MagicMock()
    epoll_inner_2 = unittest.mock.MagicMock()
    mock_epoll.side_effect = [epoll_outer, epoll_inner, epoll_inner_2]

    epoll_outer.poll.return_value = []

    epoll_inner.poll.return_value = [(13, select.EPOLLIN)]
    epoll_inner.__enter__.return_value = epoll_inner

    console_mock_fixture.raw_debug = True

    epoll_inner_2.poll.return_value = [(13, select.EPOLLIN)]
    epoll_inner_2.__enter__.return_value = epoll_inner_2
    console_mock_fixture.cmd_pipe.recv.side_effect = [b"cmd_data", EOFError()]

    console.start_loop(console_mock_fixture, command_active)
    mock_sys_intf.write.assert_called_with(11, b"cmd_data")


@unittest.mock.patch("ec3po.console.select.epoll")
@unittest.mock.patch("ec3po.console.sys_interface")
def test_start_loop_read_dbg_pipe(
    unused_mock_sys_intf, mock_epoll, console_mock_fixture
):
    command_active = multiprocessing.Value("b", False)

    epoll_outer = unittest.mock.MagicMock()
    epoll_inner = unittest.mock.MagicMock()
    epoll_inner_2 = unittest.mock.MagicMock()
    mock_epoll.side_effect = [epoll_outer, epoll_inner, epoll_inner_2]

    epoll_outer.poll.return_value = []

    epoll_inner.poll.return_value = [(14, select.EPOLLIN)]
    epoll_inner.__enter__.return_value = epoll_inner

    console_mock_fixture.interrogation_mode = b"auto"
    console_mock_fixture.is_tokenized = False

    epoll_inner_2.poll.return_value = [(14, select.EPOLLIN)]
    epoll_inner_2.__enter__.return_value = epoll_inner_2
    console_mock_fixture.dbg_pipe.recv.side_effect = [b"dbg_data", EOFError()]

    console.start_loop(console_mock_fixture, command_active)

    console_mock_fixture.check_buffer_for_enhanced_image.assert_called_once_with(
        b"dbg_data"
    )
    console_mock_fixture.handle_debug_pipe_data.assert_called_once_with(
        b"dbg_data", True, False
    )
