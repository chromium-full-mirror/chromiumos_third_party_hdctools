# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for ec3po console UART stream capture."""

import errno
import multiprocessing
import os
import pty
import unittest
from unittest import mock

from ec3po import console


OVERFLOW = "<overflow>"


class TestCaptureState(unittest.TestCase):
    """Tests for console.CaptureState."""

    def test_inactive_drops_data(self):
        cap = console.CaptureState(100)
        cap.append(b"hello")
        self.assertEqual(cap.drain(OVERFLOW), "")

    def test_active_collects_and_drains(self):
        cap = console.CaptureState(100)
        cap.set_active(True)
        cap.append(b"hello ")
        cap.append(b"world")
        self.assertEqual(cap.drain(OVERFLOW), "hello world")
        self.assertEqual(cap.drain(OVERFLOW), "")

    def test_tail_drainable_after_disable(self):
        cap = console.CaptureState(100)
        cap.set_active(True)
        cap.append(b"tail")
        cap.set_active(False)
        self.assertFalse(cap.active)
        self.assertEqual(cap.drain(OVERFLOW), "tail")

    def test_reenable_clears_stale_data(self):
        cap = console.CaptureState(100)
        cap.set_active(True)
        cap.append(b"stale")
        cap.set_active(False)
        cap.set_active(True)
        self.assertEqual(cap.drain(OVERFLOW), "")

    def test_set_active_idempotent_keeps_data(self):
        cap = console.CaptureState(100)
        cap.set_active(True)
        cap.append(b"keep")
        cap.set_active(True)
        self.assertEqual(cap.drain(OVERFLOW), "keep")

    def test_overflow_marker(self):
        cap = console.CaptureState(4)
        cap.set_active(True)
        cap.append(b"abcd")
        cap.append(b"e")
        self.assertEqual(cap.drain(OVERFLOW), "abcd" + OVERFLOW)
        # Marker is reported once and the buffer has room again.
        cap.append(b"f")
        self.assertEqual(cap.drain(OVERFLOW), "f")

    def test_invalid_utf8_ignored(self):
        cap = console.CaptureState(100)
        cap.set_active(True)
        cap.append(b"a\xffb")
        self.assertEqual(cap.drain(OVERFLOW), "ab")

    def test_overflow_drops_until_drain(self):
        # A chunk that doesn't fit must not let later, smaller chunks in,
        # otherwise the stream has a silent gap before the marker.
        cap = console.CaptureState(5)
        cap.set_active(True)
        cap.append(b"abc")
        cap.append(b"wxyz")  # Doesn't fit: overflow.
        cap.append(b"d")  # Would fit, but must be dropped.
        self.assertEqual(cap.drain(OVERFLOW), "abc" + OVERFLOW)
        cap.append(b"d")
        self.assertEqual(cap.drain(OVERFLOW), "d")

    def test_reenable_clears_overflow(self):
        cap = console.CaptureState(2)
        cap.set_active(True)
        cap.append(b"abc")
        cap.set_active(False)
        cap.set_active(True)
        cap.append(b"x")
        self.assertEqual(cap.drain(OVERFLOW), "x")


class TestConsoleCapture(unittest.TestCase):
    """Tests for capture in the console output path."""

    def setUp(self):
        self.primary_pty, self.secondary_pty = pty.openpty()
        self.interface_pty, self.interface_secondary = pty.openpty()
        self.cmd_pipe_parent, self.cmd_pipe_child = multiprocessing.Pipe()
        self.dbg_pipe_parent, self.dbg_pipe_child = multiprocessing.Pipe()
        self.capture = console.CaptureState(1000)
        self.console = console.Console(
            controller_pty=self.primary_pty,
            user_pty=os.ttyname(self.secondary_pty),
            interface_pty=self.interface_pty,
            cmd_pipe=self.cmd_pipe_child,
            dbg_pipe=self.dbg_pipe_child,
            name="test_console",
            capture=self.capture,
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

    @mock.patch(
        "ec3po.console.sys_interface.write", side_effect=lambda fd, data: len(data)
    )
    def test_capture_without_user_connected(self, mock_write):
        self.console.timestamp_enabled = False
        self.capture.set_active(True)
        self.console.handle_debug_pipe_data(b"line1\r\n", False, False)
        self.assertEqual(self.capture.drain(OVERFLOW), "line1\r\n")
        # Nothing is written to the user PTY when no user is connected.
        for call in mock_write.call_args_list:
            self.assertNotEqual(call.args[0], self.primary_pty)

    @mock.patch(
        "ec3po.console.sys_interface.write", side_effect=lambda fd, data: len(data)
    )
    def test_capture_matches_user_pty_with_timestamps(self, mock_write):
        self.console.timestamp_enabled = True
        self.capture.set_active(True)
        self.console.handle_debug_pipe_data(b"a\nb\n", True, False)
        self.console.handle_debug_pipe_data(b"c\n", True, False)
        written = b"".join(
            call.args[1]
            for call in mock_write.call_args_list
            if call.args[0] == self.primary_pty
        ).decode()
        captured = self.capture.drain(OVERFLOW)
        self.assertEqual(captured, written)
        # Every line carries a host timestamp.
        lines = captured.splitlines()
        self.assertEqual(len(lines), 3)
        for line, text in zip(lines, ["a", "b", "c"]):
            self.assertRegex(line, r"^\d\d-\d\d-\d\d \d\d:\d\d:\d\d\.\d\d\d " + text)

    @mock.patch(
        "ec3po.console.sys_interface.write", side_effect=lambda fd, data: len(data)
    )
    def test_no_capture_when_inactive(self, unused_mock_write):
        self.console.handle_debug_pipe_data(b"data\n", True, False)
        self.assertEqual(self.capture.drain(OVERFLOW), "")

    @mock.patch(
        "ec3po.console.sys_interface.write", side_effect=lambda fd, data: len(data)
    )
    def test_console_without_capture_state(self, mock_write):
        self.console.capture = None
        self.console.timestamp_enabled = False
        self.console.handle_debug_pipe_data(b"data", True, False)
        mock_write.assert_any_call(self.primary_pty, b"data")
        self.assertFalse(self.console.capture_active())

    @mock.patch(
        "ec3po.console.sys_interface.write", side_effect=lambda fd, data: len(data)
    )
    def test_console_generated_output_captured(self, mock_write):
        # Output the console writes itself (OOBM prompt and echo here; local
        # echo/prompt on enhanced EC images) appears on the user PTY even when
        # it originates from servod's command PTY, so it must be captured too.
        self.capture.set_active(True)
        for byte in b"%ab":
            self.console.handle_char(byte)
        written = b"".join(
            call.args[1]
            for call in mock_write.call_args_list
            if call.args[0] == self.primary_pty
        ).decode()
        self.assertEqual(written, "\r\n% ab")
        self.assertEqual(self.capture.drain(OVERFLOW), written)

    @mock.patch(
        "ec3po.console.sys_interface.write", side_effect=lambda fd, data: len(data)
    )
    def test_interface_pty_writes_not_captured(self, unused_mock_write):
        self.console.timestamp_enabled = False
        self.capture.set_active(True)
        self.console._write(self.interface_pty, b"cmd output")
        self.assertEqual(self.capture.drain(OVERFLOW), "")

    @mock.patch(
        "ec3po.console.sys_interface.write",
        side_effect=OSError(errno.EAGAIN, "blocked"),
    )
    def test_capture_survives_blocked_user_pty(self, unused_mock_write):
        # A stalled terminal drops data on the PTY, but not in the capture.
        self.console.timestamp_enabled = False
        self.capture.set_active(True)
        self.console.handle_debug_pipe_data(b"keep me\r\n", True, False)
        self.assertEqual(self.capture.drain(OVERFLOW), "keep me\r\n")

    @mock.patch(
        "ec3po.console.sys_interface.write",
        side_effect=OSError(errno.EIO, "terminal gone"),
    )
    def test_capture_keeps_timestamp_and_line_on_write_error(self, unused_mock_write):
        # A failed user PTY write must not leave a bare timestamp in the
        # capture or drop the line it belongs to.
        self.console.timestamp_enabled = True
        self.console.tm_req = True
        self.capture.set_active(True)
        self.console.handle_debug_pipe_data(b"keep me\n", True, False)
        self.assertRegex(
            self.capture.drain(OVERFLOW),
            r"^\d\d-\d\d-\d\d \d\d:\d\d:\d\d\.\d\d\d keep me\n$",
        )
        self.assertTrue(self.console.tm_req)

    @mock.patch(
        "ec3po.console.sys_interface.write", side_effect=lambda fd, data: len(data)
    )
    def test_line_state_tracked_while_capture_off(self, unused_mock_write):
        # Capture turned off at a prompt (no trailing newline); the EC keeps
        # printing lines nobody sees. The first captured line after re-enable
        # must still start with a timestamp.
        self.console.timestamp_enabled = True
        self.capture.set_active(True)
        self.console.handle_debug_pipe_data(b"> ", False, False)
        self.assertFalse(self.console.tm_req)
        self.capture.set_active(False)
        self.console.handle_debug_pipe_data(b"unseen\n", False, False)
        self.assertTrue(self.console.tm_req)
        self.capture.set_active(True)
        self.console.handle_debug_pipe_data(b"next\n", False, False)
        self.assertRegex(
            self.capture.drain(OVERFLOW),
            r"^\d\d-\d\d-\d\d \d\d:\d\d:\d\d\.\d\d\d next\n$",
        )


if __name__ == "__main__":
    unittest.main()
