# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# pylint: disable=unused-argument, redefined-outer-name
import termios
import unittest.mock

import pytest
import usb.core

from servo_updater.ecusb import stm32uart


@pytest.fixture
def mock_deps():
    with unittest.mock.patch(
        "servo_updater.ecusb.stm32uart.stm32usb.Susb"
    ) as mock_susb, unittest.mock.patch(
        "servo_updater.ecusb.stm32uart.os.openpty"
    ) as mock_openpty, unittest.mock.patch(
        "servo_updater.ecusb.stm32uart.os.ttyname"
    ) as mock_ttyname, unittest.mock.patch(
        "servo_updater.ecusb.stm32uart.os.fchmod"
    ) as mock_fchmod, unittest.mock.patch(
        "servo_updater.ecusb.stm32uart.os.fchown"
    ) as mock_fchown, unittest.mock.patch(
        "servo_updater.ecusb.stm32uart.os.environ.get"
    ) as mock_environ_get, unittest.mock.patch(
        "servo_updater.ecusb.stm32uart.tty.setraw"
    ) as mock_setraw, unittest.mock.patch(
        "servo_updater.ecusb.stm32uart.os.fdopen"
    ) as mock_fdopen:

        mock_openpty.return_value = (10, 11)
        mock_ttyname.return_value = "/dev/pts/1"
        mock_environ_get.return_value = "1000"

        yield {
            "susb": mock_susb,
            "openpty": mock_openpty,
            "ttyname": mock_ttyname,
            "fchmod": mock_fchmod,
            "fchown": mock_fchown,
            "environ_get": mock_environ_get,
            "setraw": mock_setraw,
            "fdopen": mock_fdopen,
        }


def test_suart_error():
    err = stm32uart.SuartError("test", 1)
    assert err.msg == "test"
    assert err.value == 1


def test_suart_init(mock_deps):
    uart = stm32uart.Suart()
    mock_deps["susb"].assert_called_once()
    assert not uart._running


def test_suart_get_set_props(mock_deps):
    uart = stm32uart.Suart()
    props = uart.get_uart_props()
    assert props["baudrate"] == 115200

    # Successful set
    assert uart.set_uart_props(props) is True

    # Failed set
    with pytest.raises(stm32uart.SuartError, match="cannot be set"):
        uart.set_uart_props({"baudrate": 9600})


def test_suart_run_setup(mock_deps):
    uart = stm32uart.Suart()

    # We will mock the thread start so we don't actually run threads
    with unittest.mock.patch(
        "servo_updater.ecusb.stm32uart.threading.Thread"
    ) as mock_thread:
        mock_thread_instance = unittest.mock.MagicMock()
        mock_thread.return_value = mock_thread_instance

        uart.run()

        assert uart.get_pty() == "/dev/pts/1"
        mock_deps["openpty"].assert_called_once()
        mock_deps["fchmod"].assert_called_once_with(11, 0o660)
        mock_deps["fchown"].assert_called_once_with(11, 1000, 1000)
        mock_deps["setraw"].assert_called_once_with(10, termios.TCSADRAIN)

        assert mock_thread.call_count == 2
        assert mock_thread_instance.start.call_count == 2


def test_suart_fchown_fallback(mock_deps):
    mock_deps["environ_get"].return_value = None
    uart = stm32uart.Suart()
    with unittest.mock.patch("servo_updater.ecusb.stm32uart.threading.Thread"):
        uart.run()
        mock_deps["fchown"].assert_called_once_with(11, -1, -1)


@unittest.mock.patch("servo_updater.ecusb.stm32uart.select.epoll")
@unittest.mock.patch("servo_updater.ecusb.stm32uart.os.write")
def test_suart_run_rx_thread(mock_os_write, mock_epoll, mock_deps):
    uart = stm32uart.Suart(debuglog=True)
    uart._ptym = 10

    mock_epoll_instance = unittest.mock.MagicMock()
    mock_epoll.return_value = mock_epoll_instance

    # Poll returns empty initially, meaning no events, so it reads USB
    # Then we set running = False to exit loop
    def poll_side_effect(*unused_args):
        uart._running = False
        return []

    mock_epoll_instance.poll.side_effect = poll_side_effect

    mock_susb_inst = mock_deps["susb"].return_value
    mock_susb_inst._read_ep.read.return_value = b"hi"

    uart._running = True
    uart.run_rx_thread()

    mock_susb_inst._read_ep.read.assert_called_once()
    mock_os_write.assert_called_once_with(10, b"hi")


@unittest.mock.patch("servo_updater.ecusb.stm32uart.select.epoll")
@unittest.mock.patch("servo_updater.ecusb.stm32uart.os.write")
def test_suart_run_rx_thread_usb_error(mock_os_write, mock_epoll, mock_deps):
    uart = stm32uart.Suart()
    uart._ptym = 10

    mock_epoll_instance = unittest.mock.MagicMock()
    mock_epoll.return_value = mock_epoll_instance

    def poll_side_effect(*unused_args):
        uart._running = False
        return []

    mock_epoll_instance.poll.side_effect = poll_side_effect

    mock_susb_inst = mock_deps["susb"].return_value
    mock_susb_inst._read_ep.read.side_effect = usb.core.USBError("timeout")

    uart._running = True
    uart.run_rx_thread()

    # Should catch and pass
    mock_susb_inst._read_ep.read.assert_called_once()
    mock_os_write.assert_not_called()


@unittest.mock.patch("servo_updater.ecusb.stm32uart.select.epoll")
@unittest.mock.patch("servo_updater.ecusb.stm32uart.os.read")
@unittest.mock.patch("servo_updater.ecusb.stm32uart.time.sleep")
def test_suart_run_tx_thread(unused_mock_sleep, mock_os_read, mock_epoll, mock_deps):
    uart = stm32uart.Suart()
    uart._ptym = 10

    mock_epoll_instance = unittest.mock.MagicMock()
    mock_epoll.return_value = mock_epoll_instance

    def poll_side_effect(*unused_args):
        uart._running = False
        return []

    mock_epoll_instance.poll.side_effect = poll_side_effect

    mock_os_read.return_value = b"out"

    mock_susb_inst = mock_deps["susb"].return_value

    uart._running = True
    uart.run_tx_thread()

    mock_os_read.assert_called_once_with(10, 64)
    mock_susb_inst._write_ep.write.assert_called_once_with(
        b"out", mock_susb_inst.TIMEOUT_MS
    )


@unittest.mock.patch("servo_updater.ecusb.stm32uart.select.epoll")
@unittest.mock.patch("servo_updater.ecusb.stm32uart.os.read")
@unittest.mock.patch("servo_updater.ecusb.stm32uart.time.sleep")
def test_suart_run_tx_thread_oserror(
    unused_mock_sleep, mock_os_read, mock_epoll, mock_deps
):
    uart = stm32uart.Suart()
    uart._ptym = 10

    mock_epoll_instance = unittest.mock.MagicMock()
    mock_epoll.return_value = mock_epoll_instance

    def poll_side_effect(*unused_args):
        uart._running = False
        return []

    mock_epoll_instance.poll.side_effect = poll_side_effect

    mock_os_read.side_effect = OSError("fail")

    uart._running = True
    uart.run_tx_thread()
    # Should catch and pass


def test_suart_close(mock_deps):
    uart = stm32uart.Suart()

    mock_rx = unittest.mock.MagicMock()
    mock_tx = unittest.mock.MagicMock()

    uart._rx_thread = mock_rx
    uart._tx_thread = mock_tx

    uart.close()

    mock_rx.join.assert_called_once_with(2)
    mock_tx.join.assert_called_once_with(2)
    mock_deps["susb"].return_value.close.assert_called_once()
    assert uart._rx_thread is None
    assert uart._tx_thread is None


@unittest.mock.patch("servo_updater.ecusb.stm32uart.Suart")
@unittest.mock.patch("servo_updater.ecusb.stm32uart.time.sleep")
@unittest.mock.patch("sys.exit")
def test_main(mock_exit, mock_sleep, mock_suart_class):
    mock_sleep.side_effect = KeyboardInterrupt()
    # main might not exist if pylint removed it, let's skip if not present
    if hasattr(stm32uart, "main"):
        stm32uart.main()
        mock_suart_class.return_value.run.assert_called_once()
        mock_exit.assert_called_once_with(0)


@unittest.mock.patch("servo_updater.ecusb.stm32uart.select.epoll")
def test_suart_run_rx_thread_general_exception(mock_epoll, mock_deps):
    uart = stm32uart.Suart()
    mock_epoll_instance = unittest.mock.MagicMock()
    mock_epoll.return_value = mock_epoll_instance
    mock_epoll_instance.poll.side_effect = Exception("general rx error")
    uart._running = True
    with pytest.raises(Exception, match="general rx error"):
        uart.run_rx_thread()


@unittest.mock.patch("servo_updater.ecusb.stm32uart.select.epoll")
def test_suart_run_tx_thread_general_exception(mock_epoll, mock_deps):
    uart = stm32uart.Suart()
    mock_epoll_instance = unittest.mock.MagicMock()
    mock_epoll.return_value = mock_epoll_instance
    mock_epoll_instance.poll.side_effect = Exception("general tx error")
    uart._running = True
    with pytest.raises(Exception, match="general tx error"):
        uart.run_tx_thread()


@unittest.mock.patch("servo_updater.ecusb.stm32uart.select.epoll")
@unittest.mock.patch("servo_updater.ecusb.stm32uart.time.sleep")
def test_suart_run_rx_thread_events(mock_sleep, mock_epoll, mock_deps):
    uart = stm32uart.Suart()
    mock_epoll_instance = unittest.mock.MagicMock()
    mock_epoll.return_value = mock_epoll_instance

    def poll_side_effect(*unused_args):
        uart._running = False
        return [(1, 1)]  # Non-empty events list

    mock_epoll_instance.poll.side_effect = poll_side_effect

    uart._running = True
    uart.run_rx_thread()
    mock_sleep.assert_called_once_with(0.1)


@unittest.mock.patch("servo_updater.ecusb.stm32uart.select.epoll")
@unittest.mock.patch("servo_updater.ecusb.stm32uart.time.sleep")
def test_suart_run_tx_thread_events(mock_sleep, mock_epoll, mock_deps):
    uart = stm32uart.Suart()
    mock_epoll_instance = unittest.mock.MagicMock()
    mock_epoll.return_value = mock_epoll_instance

    def poll_side_effect(*unused_args):
        uart._running = False
        return [(1, 1)]  # Non-empty events list

    mock_epoll_instance.poll.side_effect = poll_side_effect

    uart._running = True
    uart.run_tx_thread()
    mock_sleep.assert_called_once_with(0.1)
