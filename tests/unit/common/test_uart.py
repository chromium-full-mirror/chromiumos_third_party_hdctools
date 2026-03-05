# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import threading
import unittest.mock

import pytest

from servo.common.interface import uart


def test_uart_init():
    u = uart.Uart("test_logger")
    assert not u._capture_active
    assert not u._capture_paused
    assert not u._capture_buffer
    assert u._capture_thread is None
    assert u._parent_thread == threading.current_thread()


def test_uart_pause_resume():
    u = uart.Uart()
    u.pause_capture()
    assert u._capture_paused
    u.resume_capture()
    assert not u._capture_paused


def test_uart_set_capture_active():
    u = uart.Uart()

    mock_thread = unittest.mock.MagicMock()
    with unittest.mock.patch(
        "servo.common.interface.uart.threading.Thread"
    ) as mock_thread_class:
        mock_thread_class.return_value = mock_thread

        # Start capture
        u.set_capture_active(1)
        assert u._capture_active
        assert not u._capture_buffer
        mock_thread.start.assert_called_once()

        # Stop capture
        u.set_capture_active(0)
        assert not u._capture_active
        mock_thread.join.assert_called_once()
        assert u._capture_thread is None


def test_uart_get_capture_active():
    u = uart.Uart()
    res = u.get_capture_active()
    assert res == 0  # Default is False -> 0
    u._capture_active = True
    assert u.get_capture_active() == 1


def test_uart_get_stream():
    u = uart.Uart()
    u._capture_buffer = ["hello", "world"]
    res = u.get_stream()
    assert res == "'helloworld'"
    assert not u._capture_buffer  # Cleared after get


@unittest.mock.patch("servo.common.interface.uart.os.open")
@unittest.mock.patch("servo.common.interface.uart.os.read")
@unittest.mock.patch("servo.common.interface.uart.os.close")
@unittest.mock.patch("servo.common.interface.uart.termios.tcgetattr")
@unittest.mock.patch("servo.common.interface.uart.termios.tcsetattr")
@unittest.mock.patch("servo.common.interface.uart.tty.setraw")
@unittest.mock.patch("servo.common.interface.uart.time.sleep")
def test_uart_capture_function(
    mock_sleep,
    unused_mock_setraw,
    unused_mock_tcsetattr,
    unused_mock_tcgetattr,
    unused_mock_close,
    mock_read,
    mock_open,
):
    u = uart.Uart()
    u._capture_active = True
    u.get_pty = unittest.mock.MagicMock(return_value="/dev/null")

    mock_open.return_value = 10

    def read_side_effect(*unused_args):
        if mock_read.call_count == 1:
            return b"abc"
        if mock_read.call_count == 2:
            u._capture_paused = True
            return b"def"  # This shouldn't be read immediately
        if mock_read.call_count == 3:
            # We unpause it from the sleep mock side effect
            return b"ghi"
        if mock_read.call_count == 4:

            err = OSError("EWOULDBLOCK")
            err.errno = 11  # EWOULDBLOCK
            raise err
        if mock_read.call_count == 5:
            # Fill buffer to trigger overflow (extend it, don't overwrite)
            u._capture_buffer.extend(["A"] * uart.MAX_BUFFER_SIZE)
            return b"overflow"
        if mock_read.call_count == 6:
            u._capture_active = False
            return b"end"

    mock_read.side_effect = read_side_effect

    def sleep_side_effect(unused_val):
        if u._capture_paused:
            u._capture_paused = False

    mock_sleep.side_effect = sleep_side_effect

    u._capture_function()

    # We decode bytes to string in the buffer
    assert "abc" in u._capture_buffer
    assert "ghi" in u._capture_buffer
    assert "overflow" not in u._capture_buffer  # Dropped due to overflow


def test_uart_capture_function_oserror():
    u = uart.Uart()
    u._capture_active = True
    u.get_pty = unittest.mock.MagicMock(return_value="/dev/null")

    with unittest.mock.patch(
        "servo.common.interface.uart.os.open"
    ), unittest.mock.patch(
        "servo.common.interface.uart.os.read"
    ) as mock_read, unittest.mock.patch(
        "servo.common.interface.uart.os.close"
    ), unittest.mock.patch(
        "servo.common.interface.uart.termios.tcgetattr"
    ), unittest.mock.patch(
        "servo.common.interface.uart.termios.tcsetattr"
    ), unittest.mock.patch(
        "servo.common.interface.uart.tty.setraw"
    ):

        mock_read.side_effect = OSError("general error")
        with pytest.raises(OSError, match="general error"):
            u._capture_function()


def test_uart_not_implemented():
    u = uart.Uart()
    with pytest.raises(NotImplementedError):
        u.open()
    with pytest.raises(NotImplementedError):
        u.close()
    with pytest.raises(NotImplementedError):
        u.run()
    with pytest.raises(NotImplementedError):
        u.get_uart_props()
    with pytest.raises(NotImplementedError):
        u.set_uart_props({})
    with pytest.raises(NotImplementedError):
        u.get_pty()


def test_uart_props_validation():
    u = uart.Uart()

    # Valid
    assert (
        u._uart_props_validation(
            {"baudrate": 115200, "bits": 8, "parity": 0, "sbits": 1}
        )
        is None
    )

    # Invalid keys
    with pytest.raises(KeyError):
        u._uart_props_validation({"baudrate": 115200})

    # Invalid bits
    with pytest.raises(uart.UartDefaultException):
        u._uart_props_validation(
            {"baudrate": 115200, "bits": 9, "parity": 0, "sbits": 1}
        )

    # Invalid parity
    with pytest.raises(uart.UartDefaultException):
        u._uart_props_validation(
            {"baudrate": 115200, "bits": 8, "parity": 3, "sbits": 1}
        )

    # Invalid sbits
    with pytest.raises(uart.UartDefaultException):
        u._uart_props_validation(
            {"baudrate": 115200, "bits": 8, "parity": 0, "sbits": 3}
        )
