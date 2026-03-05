from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
import usb.core

from servo.common.interface import stm32uart


# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# pylint: disable=import-outside-toplevel


class TestSuart:
    @patch("servo.common.interface.stm32uart.stm32usb.Susb")
    @patch("servo.common.interface.stm32uart.sys_interface", create=True)
    @patch("servo.common.interface.stm32uart.tty")
    @patch("servo.common.interface.stm32uart.threading.Thread")
    def test_init(self, mock_thread, unused_mock_tty, mock_sys, mock_susb):
        mock_sys.openpty.return_value = (3, 4)
        mock_sys.ttyname.return_value = "/dev/pts/1"
        mock_susb.return_value = MagicMock()

        suart = stm32uart.Suart()
        suart._susb = mock_susb.return_value

        mock_susb.assert_called_once()

        suart.run()
        assert mock_thread.call_count == 2

        suart.close()

    @patch("servo.common.interface.stm32uart.stm32usb.Susb")
    @patch("servo.common.interface.stm32uart.sys_interface", create=True)
    @patch("servo.common.interface.stm32uart.tty")
    def test_build(self, unused_mock_tty, mock_sys, unused_mock_susb):
        mock_sys.openpty.return_value = (3, 4)
        mock_sys.ttyname.return_value = "/dev/pts/1"
        res = stm32uart.Suart.build(
            0x18D1, 0x501A, "serial123", {"interface": 1, "endpoints": [1, 2]}
        )
        assert res.__class__.__name__ == "Suart"

    def test_name(self):
        assert stm32uart.Suart.name() == "stm32_uart"

    @patch("servo.common.interface.stm32uart.stm32usb.Susb")
    @patch("servo.common.interface.stm32uart.sys_interface", create=True)
    @patch("servo.common.interface.stm32uart.tty")
    def test_properties(self, unused_mock_tty, unused_mock_sys, mock_susb):
        suart = stm32uart.Suart()
        suart._susb = mock_susb.return_value
        suart._susb = MagicMock()

        suart._susb.get_device_info.return_value = {"vendor": "google"}
        assert suart.get_device_info() == {"vendor": "google"}

        suart._ptyname = "/dev/pts/1"
        assert suart.get_pty() == "/dev/pts/1"

        props = {"baudrate": 115200, "bits": 8, "parity": 0, "sbits": 1}
        suart.set_uart_props(props)
        assert suart.get_uart_props() == props

        suart.reinitialize()

    def test_error(self):
        err = stm32uart.SuartError("test error", 5)
        assert "test error" in str(err) and "5" in str(err)

    @patch("servo.common.interface.stm32uart.stm32usb.Susb")
    @patch("servo.common.interface.stm32uart.select")
    @patch("servo.common.interface.stm32uart.sys_interface", create=True)
    def test_run_rx_thread(self, mock_sys, mock_select, mock_susb):
        suart = stm32uart.Suart()
        suart._ptym = 3
        suart._ptyname = "/dev/pts/1"
        suart._susb = mock_susb.return_value

        # Test basic run and read logic
        suart._done = MagicMock()
        suart._done.is_set.side_effect = [False, True, True, True]
        mock_epoll = MagicMock()
        mock_epoll.poll.return_value = []  # no events
        mock_select.epoll.return_value = mock_epoll
        suart._susb.read_ep.return_value = b"test"

        suart.run_rx_thread()
        mock_sys.write.assert_called_with(3, b"test")

        # Test event wait
        suart._done = MagicMock()
        suart._done.is_set.side_effect = [False, True, True, True]
        mock_epoll.poll.return_value = [(3, 1)]  # events found
        suart.run_rx_thread()
        suart._done.wait.assert_called()

    @patch("servo.common.interface.stm32uart.stm32usb.Susb")
    @patch("servo.common.interface.stm32uart.select")
    @patch("servo.common.interface.stm32uart.sys_interface", create=True)
    def test_run_tx_thread(self, mock_sys, mock_select, mock_susb):
        suart = stm32uart.Suart()
        suart._ptym = 3
        suart._ptyname = "/dev/pts/1"
        suart._susb = mock_susb.return_value

        # Test basic run and write logic
        suart._done = MagicMock()
        suart._done.is_set.side_effect = [False, True, True, True]
        mock_epoll = MagicMock()
        mock_epoll.poll.return_value = []  # no events
        mock_readp = MagicMock()
        mock_readp.poll.return_value = [(3, 1)]  # readp poll says data ready

        mock_select.epoll.side_effect = [mock_epoll, mock_readp]
        mock_sys.read.return_value = b"test"

        with patch("servo.common.interface.stm32uart.time.sleep"):
            suart.run_tx_thread()

        suart._susb.write_ep.assert_called_with(b"test", suart._susb.TIMEOUT_MS)

        # Test Exception catching logic in tx thread (e.g. ENODEV)
        import errno

        e = IOError(errno.ENODEV, "ENODEV")

        suart._done = MagicMock()
        suart._done.is_set.side_effect = [False, True, True, True]
        mock_select.epoll.side_effect = [mock_epoll, mock_readp]
        mock_sys.read.return_value = b"test2"
        suart._susb.write_ep.side_effect = e

        with patch("servo.common.interface.stm32uart.time.sleep"):
            suart.run_tx_thread()

        suart._susb.release.assert_called_once()

    @patch("servo.common.interface.stm32uart.stm32usb.Susb")
    def test_set_uart_props(self, mock_susb):
        suart = stm32uart.Suart()
        suart._props = {"baudrate": 115200, "bits": 8, "parity": 0, "sbits": 1}
        suart._susb = mock_susb.return_value

        # Valid change
        suart.set_uart_props({"baudrate": 9600, "bits": 8, "parity": 1, "sbits": 1})
        assert suart.get_uart_props()["baudrate"] == 9600
        assert suart.get_uart_props()["parity"] == 1

        # Invalid change
        with pytest.raises(stm32uart.SuartError):
            suart.set_uart_props({"bits": 7})

    @patch("servo.common.interface.stm32uart.stm32usb.Susb")
    @patch("servo.common.interface.stm32uart.select")
    @patch("servo.common.interface.stm32uart.sys_interface", create=True)
    def test_run_rx_thread_errors(self, unused_mock_sys, mock_select, mock_susb):
        suart = stm32uart.Suart()
        suart._ptym = 3
        suart._ptyname = "/dev/pts/1"
        suart._susb = mock_susb.return_value
        suart._done = MagicMock()
        suart._done.is_set.side_effect = [False, True, True, True, True]
        mock_epoll = MagicMock()
        mock_epoll.poll.return_value = []
        mock_select.epoll.return_value = mock_epoll

        # Test USBError

        suart._susb.read_ep.side_effect = usb.core.USBError("test")
        suart.run_rx_thread()  # Should catch and continue

        # Test generic Exception
        suart._done.is_set.side_effect = [False, True, True, True, True]
        suart._susb.read_ep.side_effect = Exception("test")
        suart.run_rx_thread()  # Should log and continue

    @patch("servo.common.interface.stm32uart.stm32usb.Susb")
    @patch("servo.common.interface.stm32uart.select")
    @patch("servo.common.interface.stm32uart.sys_interface", create=True)
    def test_run_tx_thread_errors(self, mock_sys, mock_select, mock_susb):
        suart = stm32uart.Suart()
        suart._ptym = 3
        suart._ptyname = "/dev/pts/1"
        suart._susb = mock_susb.return_value
        suart._done = MagicMock()
        suart._done.is_set.side_effect = [False, True, True, True, True]
        mock_epoll = MagicMock()
        mock_epoll.poll.return_value = []
        mock_readp = MagicMock()
        mock_readp.poll.return_value = [(3, 1)]
        mock_select.epoll.side_effect = [mock_epoll, mock_readp]

        mock_sys.read.side_effect = Exception("test")
        with patch("servo.common.interface.stm32uart.time.sleep"):
            suart.run_tx_thread()  # Should log exception and continue
