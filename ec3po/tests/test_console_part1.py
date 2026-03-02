# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import multiprocessing
import os
import pty
import unittest
from unittest import mock

from ec3po import console


class TestConsole(unittest.TestCase):
    def setUp(self):
        self.primary_pty, self.secondary_pty = pty.openpty()
        self.interface_pty, self.interface_secondary = pty.openpty()
        self.cmd_pipe_parent, self.cmd_pipe_child = multiprocessing.Pipe()
        self.dbg_pipe_parent, self.dbg_pipe_child = multiprocessing.Pipe()

        self.console = console.Console(
            controller_pty=self.primary_pty,
            user_pty=os.ttyname(self.secondary_pty),
            interface_pty=self.interface_pty,
            cmd_pipe=self.cmd_pipe_child,
            dbg_pipe=self.dbg_pipe_child,
            name="test_console",
        )
        self.console.enhanced_ec = True

    def tearDown(self):
        os.close(self.primary_pty)
        os.close(self.secondary_pty)
        os.close(self.interface_pty)
        os.close(self.interface_secondary)
        self.cmd_pipe_parent.close()
        self.cmd_pipe_child.close()
        self.dbg_pipe_parent.close()
        self.dbg_pipe_child.close()

    def test_initialization(self):
        self.assertEqual(self.console.user_pty, os.ttyname(self.secondary_pty))
        self.assertFalse(self.console.receiving_oobm_cmd)
        self.assertEqual(self.console.input_buffer_pos, 0)
        self.assertEqual(self.console.input_buffer, b"")
        self.assertTrue(self.console.enhanced_ec)

    def test_log_console_output(self):
        self.console.oobm_cmd = True
        self.console.logger = mock.MagicMock()
        # Send a newline to trigger the log dump
        self.console.log_console_output(b"hello world\n")
        self.console.logger.debug.assert_called_with("%s", "hello world\\n")

    def test_handle_char_normal(self):
        self.console.check_for_enhanced_ec_image = mock.MagicMock(return_value=True)
        self.console.enhanced_ec = True
        with mock.patch(
            "ec3po.console.sys_interface.write", return_value=1
        ) as unused_mock_write, mock.patch.object(self.console.cmd_pipe, "send"):
            self.console.handle_char(ord("a"))
            self.assertEqual(self.console.input_buffer_pos, 1)
            self.assertEqual(len(self.console.input_buffer), 1)
            self.assertEqual(self.console.input_buffer[0:1], b"a")

    def test_handle_char_backspace(self):
        self.console.check_for_enhanced_ec_image = mock.MagicMock(return_value=True)
        self.console.enhanced_ec = True
        with mock.patch(
            "ec3po.console.sys_interface.write", return_value=1
        ), mock.patch.object(self.console.cmd_pipe, "send"):
            self.console.handle_char(ord("a"))
            self.assertEqual(self.console.input_buffer_pos, 1)
            with mock.patch.object(self.console, "send_backspace") as unused_mock_bs:
                self.console.handle_char(console.ControlKey.BACKSPACE)
                self.assertEqual(self.console.input_buffer_pos, 0)
                self.assertEqual(self.console.input_buffer, b"")

    def test_handle_char_enter(self):
        self.console.check_for_enhanced_ec_image = mock.MagicMock(return_value=True)
        self.console.enhanced_ec = True
        with mock.patch(
            "ec3po.console.sys_interface.write", return_value=1
        ), mock.patch.object(self.console.cmd_pipe, "send"):
            self.console.handle_char(ord("a"))
            self.console.handle_char(ord("b"))
            self.console.handle_char(ord("c"))
            self.console.handle_char(console.ControlKey.CARRIAGE_RETURN)
            self.assertEqual(self.console.history[0], b"abc")
            self.assertEqual(self.console.history_pos, 1)
            self.assertEqual(self.console.input_buffer_pos, 0)
            self.assertEqual(self.console.input_buffer, b"")

    def test_is_printable(self):
        self.assertTrue(console.is_printable(ord("a")))
        self.assertTrue(console.is_printable(ord(" ")))
        self.assertTrue(console.is_printable(ord("~")))
        self.assertFalse(console.is_printable(0x00))
        self.assertFalse(console.is_printable(0x1F))

    def test_slice_out_char(self):
        self.console.check_for_enhanced_ec_image = mock.MagicMock(return_value=True)
        self.console.enhanced_ec = True
        with mock.patch(
            "ec3po.console.sys_interface.write", return_value=1
        ), mock.patch.object(self.console.cmd_pipe, "send"):
            self.console.handle_char(ord("a"))
            self.console.handle_char(ord("b"))
            self.console.handle_char(ord("c"))
            self.console.input_buffer_pos -= 1
            self.console.slice_out_char()
        self.assertEqual(len(self.console.input_buffer), 2)
        self.assertEqual(self.console.input_buffer[0:1], b"a")
        self.assertEqual(self.console.input_buffer[1:2], b"b")

    def test_show_previous_command(self):
        self.console.history = [b"cmd1", b"cmd2"]
        self.console.history_pos = 2
        with mock.patch("ec3po.console.sys_interface.write", return_value=1):
            self.console.show_previous_command()
            self.assertEqual(self.console.history_pos, 1)
            self.assertEqual(self.console.input_buffer[:4], b"cmd2")
            self.console.show_previous_command()
            self.assertEqual(self.console.history_pos, 0)
            self.assertEqual(self.console.input_buffer[:4], b"cmd1")

    def test_show_next_command(self):
        self.console.history = [b"cmd1", b"cmd2"]
        self.console.history_pos = 0
        self.console.input_buffer = b"cmd1"
        self.console.input_buffer_pos = 4
        with mock.patch("ec3po.console.sys_interface.write", return_value=1):
            self.console.show_next_command()
            self.assertEqual(self.console.history_pos, 1)
            self.assertEqual(self.console.input_buffer[:4], b"cmd2")

    def test_process_oobm_queue(self):
        # Test timestamp command
        self.console.oobm_queue.put(b"timestamp on")
        self.console.process_oobm_queue()
        assert self.console.timestamp_enabled is True

        # Test loglevel command
        self.console.oobm_queue.put(b"loglevel 10")
        with mock.patch.object(self.console.cmd_pipe, "send") as mock_send:
            self.console.process_oobm_queue()
            mock_send.assert_called_with(b"loglevel 10")
