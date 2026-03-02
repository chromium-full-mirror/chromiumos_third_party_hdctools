# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# pylint: disable=line-too-long

import multiprocessing
import os
import pty
import unittest
from unittest import mock

from ec3po import console


class TestConsoleMore(unittest.TestCase):
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

    def tearDown(self):
        os.close(self.primary_pty)
        os.close(self.secondary_pty)
        os.close(self.interface_pty)
        os.close(self.interface_secondary)
        self.cmd_pipe_parent.close()
        self.cmd_pipe_child.close()
        self.dbg_pipe_parent.close()
        self.dbg_pipe_child.close()

    def test_canonicalize_time_string(self):
        self.assertEqual(console.canonicalize_time_string("12:34567"), b"12:34 ")

    @mock.patch("ec3po.console.sys_interface.write")
    def test_print_history(self, mock_write):
        self.console.history = [b"first", b"second"]
        self.console.print_history()
        mock_write.assert_called()

    @mock.patch("ec3po.console.sys_interface.write")
    def test_print_oobm_help(self, mock_write):
        self.console.print_oobm_help()
        mock_write.assert_called()

    @mock.patch("ec3po.console.sys_interface.write")
    def test_move_cursor(self, mock_write):
        self.console.input_buffer = b"123456"
        self.console.input_buffer_pos = 3
        self.console.move_cursor("left", 2)
        mock_write.assert_called_with(self.primary_pty, b"\x1b[2D")

        self.console.move_cursor("right", 2)
        # Because we moved left 2, the original sequence encoded `count`. But wait, in move_cursor `seq` is built BEFORE `count = min()`.
        # So seq is built with original count.
        mock_write.assert_called_with(self.primary_pty, b"\x1b[2C")

    @mock.patch("ec3po.console.sys_interface.write")
    def test_kill_line(self, mock_write):
        self.console.input_buffer = b"12345"
        self.console.input_buffer_pos = 2
        # diff = 3. move_cursor right 3, then 3 backspaces.
        # send_backspace uses \x08 \x08
        self.console.kill_line()
        # Just check it called write (will be called multiple times)
        self.assertTrue(mock_write.called)

    @mock.patch("ec3po.console.sys_interface.write")
    def test_send_to_controller(self, mock_write):
        self.console.send_to_controller(b"hello")
        mock_write.assert_called_with(self.primary_pty, b"hello")

    def test_check_buffer_for_enhanced_image(self):
        # Should set enhanced_ec to True if it finds a match
        self.console.check_buffer_for_enhanced_image(
            b"Enhanced Console is enabled (v1.0.0)\\n"
        )
        self.assertTrue(self.console.enhanced_ec)

        self.console.enhanced_ec = False
        self.console.check_buffer_for_enhanced_image(b"regular console output")
        self.assertFalse(self.console.enhanced_ec)

    @mock.patch("ec3po.console.sys_interface.write")
    def test_handle_esc(self, unused_mock_write):
        # Escape sequence logic:
        # ESC -> BRACKET -> char
        self.console.esc_state = console.EscState.ESC_START
        self.console.handle_esc(ord("["))
        self.assertEqual(self.console.esc_state, console.EscState.ESC_BRACKET)

        # Test up arrow
        self.console.history = [b"hist1"]
        self.console.history_pos = 1
        self.console.handle_esc(ord("A"))
        self.assertEqual(self.console.esc_state, 0)
        self.assertEqual(self.console.input_buffer[:5], b"hist1")

    @mock.patch("ec3po.console.sys_interface.write")
    def test_handle_debug_pipe_data(self, mock_write):
        class MockCommandActive:
            value = True

        self.console.handle_debug_pipe_data(
            b"some debug data", True, MockCommandActive()
        )
        mock_write.assert_any_call(self.console.controller_pty, b"some debug data")
        mock_write.assert_any_call(self.console.interface_pty, b"some debug data")

    @mock.patch("ec3po.console.sys_interface.write")
    @mock.patch.object(
        console.Console, "check_for_enhanced_ec_image", return_value=True
    )
    def test_handle_char_more_controls(self, unused_mock_check, unused_mock_write):
        self.console.enhanced_ec = True

        # Test left/right arrows via ESC
        self.console.input_buffer = b"abc"
        self.console.input_buffer_pos = 3

        self.console.handle_char(console.ControlKey.ESC)
        self.console.handle_char(ord("["))
        self.console.handle_char(ord("D"))  # Left arrow
        self.assertEqual(self.console.input_buffer_pos, 2)

        self.console.handle_char(console.ControlKey.ESC)
        self.console.handle_char(ord("["))
        self.console.handle_char(ord("C"))  # Right arrow
        self.assertEqual(self.console.input_buffer_pos, 3)

        # Test CTRL_D (EOF)
        self.console.handle_char(console.ControlKey.CTRL_D)

        # Test CTRL_K (clear line)
        self.console.handle_char(console.ControlKey.CTRL_K)
        self.assertEqual(self.console.input_buffer, b"abc")
        self.assertEqual(self.console.input_buffer_pos, 3)

        # Test CTRL_A (move to beginning)
        self.console.input_buffer = b"abc"
        self.console.input_buffer_pos = 3
        self.console.handle_char(console.ControlKey.CTRL_A)
        self.assertEqual(self.console.input_buffer_pos, 0)

        # Test CTRL_E (move to end)
        self.console.handle_char(console.ControlKey.CTRL_E)
        self.assertEqual(self.console.input_buffer_pos, 3)

    def test_main(self):
        with mock.patch(
            "ec3po.console.argparse.ArgumentParser.parse_args"
        ) as mock_args, mock.patch("os.path.exists", return_value=True), mock.patch(
            "ec3po.console.multiprocessing.connection.Client"
        ) as unused_mock_client, mock.patch(
            "ec3po.console.start_loop"
        ) as mock_loop, mock.patch(
            "ec3po.console.sys_interface.openpty", return_value=(1, 2)
        ) as unused_mock_openpty, mock.patch(
            "ec3po.console.sys_interface.ttyname", return_value="fake_pty"
        ) as unused_mock_ttyname, mock.patch(
            "ec3po.console.sys_interface.chmod"
        ) as unused_mock_chmod, mock.patch(
            "ec3po.console.threadproc_shim.Value", create=True
        ) as unused_mock_val, mock.patch(
            "ec3po.console.threadproc_shim.ThreadOrProcess"
        ) as unused_mock_thread:

            mock_args.return_value = mock.MagicMock(
                command_pipe="/tmp/cmd",
                debug_pipe="/tmp/dbg",
                pty="/dev/pts/1",
                control_pty="/dev/pts/2",
                tokens=None,
                name="test",
                log_level="info",
            )

            console.main(["--log-level", "info", "fake_pty"])

            mock_loop.assert_called()
