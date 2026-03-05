# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# pylint: disable=line-too-long

from unittest.mock import MagicMock
from unittest.mock import patch

from servo.common.interface import ec3po_interface


class TestEC3PO:
    @patch("servo.common.interface.ec3po_interface.sys_interface")
    @patch("servo.common.interface.ec3po_interface.termios")
    @patch("servo.common.interface.ec3po_interface.tty")
    @patch("servo.common.interface.ec3po_interface.console.start_loop")
    @patch("servo.common.interface.ec3po_interface.interpreter.start_loop")
    @patch("servo.common.interface.ec3po_interface.threadproc_shim.ThreadOrProcess")
    @patch("servo.common.interface.ec3po_interface._os_pipe_files")
    @patch("servo.common.interface.ec3po_interface.threadproc_shim.Pipe")
    def test_init(
        self,
        mock_pipe,
        mock_pipe_files,
        mock_thread,
        unused_mock_interp_loop,
        unused_mock_console_loop,
        mock_tty,
        unused_mock_termios,
        mock_sys,
    ):
        mock_raw_uart = MagicMock()
        mock_raw_uart.get_pty.return_value = "/dev/pts/1"

        # Setup mocked openpty to return distinct integer fds
        mock_sys.openpty.side_effect = [(103, 104), (105, 106)]
        mock_tty.setraw = MagicMock()
        mock_sys.ttyname.return_value = "/dev/pts/2"
        mock_sys.ttyname.side_effect = lambda fd: f"/dev/pts/{fd}"

        # Mock pipes
        mock_pipe.return_value = (MagicMock(), MagicMock())
        mock_pipe_files.return_value = (MagicMock(), MagicMock())

        # Instantiate
        ec3po_instance = ec3po_interface.EC3PO(
            mock_raw_uart, "test_source", {"vendor": "google"}
        )

        # Checks
        assert ec3po_instance.get_pty() == "/dev/pts/104"
        assert ec3po_instance.get_control_pty() == "/dev/pts/106"
        assert ec3po_instance.get_device_info() == {"vendor": "google"}

        ec3po_instance.get_command_lock()
        assert ec3po_instance._command_active.value is True

        ec3po_instance.release_command_lock()
        assert ec3po_instance._command_active.value is False

        ec3po_instance.set_interp_connect(1)
        assert ec3po_instance.get_interp_connect() == 1

        ec3po_instance.set_loglevel("debug")
        assert ec3po_instance.get_loglevel() == "debug"

        ec3po_instance.set_timestamp(1)
        assert ec3po_instance.get_timestamp() == 1

        # Test close
        ec3po_instance.close()
        # Thread join should be called
        assert mock_thread.return_value.join.called

    @patch("servo.common.interface.ec3po_interface.EC3PO.__init__", return_value=None)
    def test_build(self, unused_mock_init):
        res = ec3po_interface.EC3PO.build(
            1,
            0x18D1,
            0x501A,
            "serial123",
            {"raw_pty": "mock_pty", "source": "src"},
            MagicMock(),
            "test_source",
            ("localhost", 1234),
        )
        # When __init__ is mocked to return None, type is still EC3PO, but object is empty.
        assert res is not None

    def test_name(self):
        assert ec3po_interface.EC3PO.name() == "ec3po_uart"

    def test_run_callbacks(self):
        cb1 = MagicMock(return_value=1)
        cb2 = MagicMock(return_value=2)
        assert ec3po_interface._run_callbacks(cb1, cb2) == 2

    def test_send_shutdown(self):
        mock_pipe = MagicMock()
        ec3po_interface._send_shutdown(mock_pipe)
