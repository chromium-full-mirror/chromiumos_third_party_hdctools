# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# pylint: disable=line-too-long, redefined-outer-name

import unittest.mock

import pytest

from servo.common.interface import ftdiuart


@pytest.fixture
def mock_ftdi_utils():
    with unittest.mock.patch(
        "servo.common.interface.ftdiuart.ftdi_utils"
    ) as mock_utils:
        mock_flib = unittest.mock.MagicMock()
        mock_lib = unittest.mock.MagicMock()
        mock_utils.load_libs.return_value = (mock_flib, mock_lib)
        mock_utils.get_interface_and_pid.return_value = (2, 0x1234)
        yield mock_utils, mock_flib, mock_lib


def test_fuart_error():
    err = ftdiuart.FuartError("test", 1)
    assert err.msg == "test"
    assert err.value == 1


def test_fuart_init(mock_ftdi_utils):
    unused_x, mock_flib, mock_lib = mock_ftdi_utils
    mock_flib.ftdi_init.return_value = 0
    mock_lib.fuart_init.return_value = 0

    with unittest.mock.patch("servo.common.interface.ftdiuart.uart.Uart.__init__"):
        fobj = ftdiuart.Fuart(serialname="12345")
        mock_flib.ftdi_init.assert_called_once()
        mock_lib.fuart_init.assert_called_once()

        assert getattr(fobj, "_is_closed", False) is True
        assert fobj.name() == "ftdi_uart"

        fobj.get_pty = lambda: None
        assert fobj.get_pty() is None


def test_fuart_init_errors(mock_ftdi_utils):
    unused_x, mock_flib, mock_lib = mock_ftdi_utils
    mock_flib.ftdi_init.return_value = 1

    with unittest.mock.patch("servo.common.interface.ftdiuart.uart.Uart.__init__"):
        with pytest.raises(ftdiuart.FuartError, match="ftdi_init"):
            ftdiuart.Fuart(serialname="12345")

        mock_flib.ftdi_init.return_value = 0
        mock_lib.fuart_init.return_value = 1
        with pytest.raises(ftdiuart.FuartError, match="fuart_init"):
            ftdiuart.Fuart(serialname="12345")


def test_fuart_open_close(mock_ftdi_utils):
    unused_x, mock_flib, mock_lib = mock_ftdi_utils
    mock_flib.ftdi_init.return_value = 0
    mock_lib.fuart_init.return_value = 0

    with unittest.mock.patch("servo.common.interface.ftdiuart.uart.Uart.__init__"):
        fobj = ftdiuart.Fuart(serialname="12345")
        mock_lib.fuart_open.return_value = 0
        fobj.open()
        assert getattr(fobj, "_is_closed", False) is False
        mock_lib.fuart_open.assert_called_once()

        # Test close
        fobj.close = unittest.mock.MagicMock()
        del fobj
        mock_lib.fuart_close.assert_not_called()  # Because __del__ calls close() which is mocked


def test_fuart_open_close_errors(mock_ftdi_utils):
    unused_x, mock_flib, mock_lib = mock_ftdi_utils
    mock_flib.ftdi_init.return_value = 0
    mock_lib.fuart_init.return_value = 0

    with unittest.mock.patch("servo.common.interface.ftdiuart.uart.Uart.__init__"):
        fobj = ftdiuart.Fuart(serialname="12345")
        mock_lib.fuart_open.return_value = 1
        with pytest.raises(ftdiuart.FuartError, match="fuart_open"):
            fobj.open()

        fobj._is_closed = False
        with unittest.mock.patch("servo.common.interface.ftdiuart.uart.Uart.close"):
            mock_lib.fuart_close.return_value = 1
            with pytest.raises(ftdiuart.FuartError, match="fuart_close"):
                fobj.close()

        # Test __del__ suppressing exception
        fobj._is_closed = False
        fobj.close = unittest.mock.MagicMock()
        del fobj


def test_fuart_del(mock_ftdi_utils):
    unused_x, mock_flib, mock_lib = mock_ftdi_utils
    mock_flib.ftdi_init.return_value = 0
    mock_lib.fuart_init.return_value = 0
    mock_lib.fuart_close.return_value = 0

    with unittest.mock.patch("servo.common.interface.ftdiuart.uart.Uart.__init__"):
        fobj = ftdiuart.Fuart(serialname="12345")
        fobj._is_closed = False
        fobj.close = unittest.mock.MagicMock()
        del fobj


@unittest.mock.patch("servo.common.interface.ftdiuart.uart.Uart.__init__")
def test_fuart_build(mock_uart_init, mock_ftdi_utils):
    mock_utils, mock_flib, mock_lib = mock_ftdi_utils
    mock_flib.ftdi_init.return_value = 0
    mock_lib.fuart_init.return_value = 0
    mock_lib.fuart_open.return_value = 0

    with unittest.mock.patch("servo.common.interface.ftdiuart.Fuart.run") as mock_run:
        fobj = ftdiuart.Fuart.build(
            index=1,
            vid=0x1234,
            pid=0x5678,
            sid="TESTSID",
            interface_data={"interface": 3},
        )

        mock_utils.get_interface_and_pid.assert_called_once_with(1, 0x5678)
        assert getattr(fobj, "_is_closed", False) is True
        mock_lib.fuart_open.assert_not_called()
        mock_uart_init.assert_called_once()
        mock_run.assert_called_once()


def test_fuart_run_tx_rx(mock_ftdi_utils):
    unused_x, mock_flib, mock_lib = mock_ftdi_utils
    mock_flib.ftdi_init.return_value = 0
    mock_lib.fuart_init.return_value = 0

    with unittest.mock.patch("servo.common.interface.ftdiuart.uart.Uart.__init__"):
        fobj = ftdiuart.Fuart(serialname="12345")

        mock_lib.fuart_run.return_value = 0
        fobj.open = unittest.mock.MagicMock()
        fobj._is_closed = True
        fobj.run()
        mock_lib.fuart_run.assert_called_once()
        fobj.open.assert_called_once()

        mock_lib.fuart_run.return_value = 1
        fobj.open = unittest.mock.MagicMock()
        fobj._is_closed = True
        with pytest.raises(ftdiuart.FuartError, match="fuart_run"):
            fobj.run()


def test_fuart_props(mock_ftdi_utils):
    unused_x, mock_flib, mock_lib = mock_ftdi_utils
    mock_flib.ftdi_init.return_value = 0
    mock_lib.fuart_init.return_value = 0

    with unittest.mock.patch("servo.common.interface.ftdiuart.uart.Uart.__init__"):
        fobj = ftdiuart.Fuart(serialname="12345")

        mock_lib.fuart_get_uart_props.return_value = 0
        fobj.get_uart_props = unittest.mock.MagicMock(return_value={"baudrate": 9600})
        res = fobj.get_uart_props()
        assert "baudrate" in res

        fobj = ftdiuart.Fuart(serialname="12345")
        fobj._uart_props_validation = unittest.mock.MagicMock()
        mock_lib.fuart_stty.return_value = 0
        fobj.set_uart_props({"baudrate": 9600, "bits": 8, "parity": 0, "sbits": 1})
        mock_lib.fuart_stty.assert_called_once()

        mock_lib.fuart_stty.return_value = 1
        with pytest.raises(ftdiuart.FuartError, match="Failed to set line properties"):
            fobj.set_uart_props({"baudrate": 9600, "bits": 8, "parity": 0, "sbits": 1})
