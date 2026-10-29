# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# pylint: disable=line-too-long

import ast
from unittest.mock import MagicMock
from unittest.mock import patch

from ec3po import console
from servo.common.interface import ec3po_interface
from servo.common.interface import uart


class TestEC3PO:
    @patch("ec3po.console.sys_interface")
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
        unused_mock_console_sys,
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

    @patch("servo.common.interface.ec3po_interface.EC3PO.__init__", return_value=None)
    @patch("servo.common.interface.ec3po_interface.InterfaceUtils")
    @patch("servo.common.interface.ec3po_interface.servo_dev_templates")
    def test_reinitialize_reinit_capable(
        self, mock_templates, mock_utils, unused_mock_init
    ):
        # Setup EC3PO instance
        ec3po_instance = ec3po_interface.EC3PO()
        ec3po_instance._logger = MagicMock()
        ec3po_instance._raw_ec_uart = "/dev/pts/1"
        ec3po_instance._source = "servo_v4p1"
        ec3po_instance._device_info = MagicMock(
            vid=0x18D1, pid=0x520D, serialname="123"
        )  # servo_v4p1

        # Mock template class to be reinit capable
        mock_template = MagicMock()
        mock_template.TYPE = "servo_v4p1"
        mock_templates.get_template_class.return_value = mock_template
        mock_templates.REINIT_CAPABLE_TYPES = {"servo_v4p1"}

        # Mock InterfaceUtils
        mock_utils.get_interface_key.return_value = "key"
        mock_interface = MagicMock()
        mock_interface.name.return_value = "stm32_uart"
        mock_interface.get_pty.return_value = "/dev/pts/1"
        mock_utils._interface_dict = {"key": {"interface_list": [mock_interface]}}

        # Call reinitialize with reset_device=True
        ec3po_instance.reinitialize(reset_device=True)

        # Verify interface.reinitialize was called with reset_device=True
        mock_interface.reinitialize.assert_called_once_with(reset_device=True)

    @patch("servo.common.interface.ec3po_interface.EC3PO.__init__", return_value=None)
    @patch("servo.common.interface.ec3po_interface.InterfaceUtils")
    @patch("servo.common.interface.ec3po_interface.servo_dev_templates")
    def test_reinitialize_non_reinit_capable(
        self, mock_templates, mock_utils, unused_mock_init
    ):
        # Setup EC3PO instance
        ec3po_instance = ec3po_interface.EC3PO()
        ec3po_instance._logger = MagicMock()
        ec3po_instance._raw_ec_uart = "/dev/pts/1"
        ec3po_instance._source = "servo_v4p1"
        ec3po_instance._device_info = MagicMock(
            vid=0x18D1, pid=0x5020, serialname="123"
        )  # sweetberry (not reinit capable)

        # Mock template class to be non-reinit-capable
        mock_template = MagicMock()
        mock_template.TYPE = "sweetberry"
        mock_templates.get_template_class.return_value = mock_template
        mock_templates.REINIT_CAPABLE_TYPES = {"servo_v4p1"}

        # Mock InterfaceUtils
        mock_utils.get_interface_key.return_value = "key"
        mock_interface = MagicMock()
        mock_interface.name.return_value = "stm32_uart"
        mock_interface.get_pty.return_value = "/dev/pts/1"
        mock_utils._interface_dict = {"key": {"interface_list": [mock_interface]}}

        # Call reinitialize with reset_device=True
        ec3po_instance.reinitialize(reset_device=True)

        # Verify interface.reinitialize was called with reset_device=False (overridden)
        mock_interface.reinitialize.assert_called_once_with(reset_device=False)

    @patch("servo.common.interface.ec3po_interface.EC3PO.__init__", return_value=None)
    @patch("servo.common.interface.ec3po_interface.InterfaceUtils")
    @patch("servo.common.interface.ec3po_interface.servo_dev_templates")
    def test_reinitialize_dut_uart_source_disables_reset_device(
        self, mock_templates, mock_utils, unused_mock_init
    ):
        for source in ("PD/Cr50", "Cr50", "H1", "EC", "CPU", "FPMCU"):
            ec3po_instance = ec3po_interface.EC3PO()
            ec3po_instance._logger = MagicMock()
            ec3po_instance._raw_ec_uart = "/dev/pts/1"
            ec3po_instance._source = source
            ec3po_instance._device_info = MagicMock(
                vid=0x18D1, pid=0x501A, serialname="MICRO-123"
            )

            mock_template = MagicMock()
            mock_template.TYPE = "servo_micro"
            mock_templates.get_template_class.return_value = mock_template
            mock_templates.REINIT_CAPABLE_TYPES = {"servo_micro"}

            mock_utils.get_interface_key.return_value = "key"
            mock_interface = MagicMock()
            mock_interface.name.return_value = "stm32_uart"
            mock_interface.get_pty.return_value = "/dev/pts/1"
            mock_utils._interface_dict = {"key": {"interface_list": [mock_interface]}}

            ec3po_instance.reinitialize(reset_device=True)

            mock_interface.reinitialize.assert_called_once_with(reset_device=False)

    @patch("servo.common.interface.ec3po_interface.EC3PO.__init__", return_value=None)
    @patch("servo.common.interface.ec3po_interface.InterfaceUtils")
    @patch("servo.common.interface.ec3po_interface.servo_dev_templates")
    def test_reinitialize_servo_console_source_allows_reset_device(
        self, mock_templates, mock_utils, unused_mock_init
    ):
        for source in ("servo_v4", "servo_v4p1", "servo_micro", "c2d2"):
            ec3po_instance = ec3po_interface.EC3PO()
            ec3po_instance._logger = MagicMock()
            ec3po_instance._raw_ec_uart = "/dev/pts/1"
            ec3po_instance._source = source
            ec3po_instance._device_info = MagicMock(
                vid=0x18D1, pid=0x501A, serialname="MICRO-123"
            )

            mock_template = MagicMock()
            mock_template.TYPE = "servo_micro"
            mock_templates.get_template_class.return_value = mock_template
            mock_templates.REINIT_CAPABLE_TYPES = {"servo_micro"}

            mock_utils.get_interface_key.return_value = "key"
            mock_interface = MagicMock()
            mock_interface.name.return_value = "stm32_uart"
            mock_interface.get_pty.return_value = "/dev/pts/1"
            mock_utils._interface_dict = {"key": {"interface_list": [mock_interface]}}

            ec3po_instance.reinitialize(reset_device=True)

            mock_interface.reinitialize.assert_called_once_with(reset_device=True)


class TestEC3POCapture:
    """UART capture behaviour of EC3PO (b/451584953, b/575738169)."""

    @staticmethod
    def _make():
        # Bypass __init__, which spawns the console/interpreter threads.
        inst = ec3po_interface.EC3PO.__new__(ec3po_interface.EC3PO)
        inst._logger = MagicMock()
        inst._capture = console.CaptureState(ec3po_interface.CAPTURE_LIMIT_CHARS)
        return inst

    def test_capture_readback(self):
        # Regression for b/451584953: autotest and DTS UartCapture read the
        # control back after setting it and skip the UART if it isn't 'on'.
        inst = self._make()
        assert inst.get_capture_active() == 0
        inst.set_capture_active(1)
        assert inst.get_capture_active() == 1
        inst.set_capture_active(0)
        assert inst.get_capture_active() == 0

    def test_get_stream_is_repr_str(self):
        inst = self._make()
        inst.set_capture_active(1)
        inst._capture.append(b"Chip: H1\r\n'quote'")
        stream = inst.get_stream()
        assert isinstance(stream, str)
        assert ast.literal_eval(stream) == "Chip: H1\r\n'quote'"
        assert ast.literal_eval(inst.get_stream()) == ""

    def test_get_stream_returns_tail_after_capture_off(self):
        # autotest Servo.close() stops capture before dumping the stream.
        inst = self._make()
        inst.set_capture_active(1)
        inst._capture.append(b"tail")
        inst.set_capture_active(0)
        assert ast.literal_eval(inst.get_stream()) == "tail"

    def test_get_stream_inactive_empty(self):
        inst = self._make()
        assert inst.get_stream() == repr("")

    def test_get_stream_overflow_marker(self):
        inst = self._make()
        inst._capture.limit = 3
        inst.set_capture_active(1)
        inst._capture.append(b"abc")
        inst._capture.append(b"d")
        assert ast.literal_eval(inst.get_stream()) == "abc" + uart.BUFFER_OVERFLOW_STR
