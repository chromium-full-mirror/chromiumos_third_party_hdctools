# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# pylint: disable=line-too-long, redefined-outer-name

import unittest.mock

import pytest

from servo.common.interface import ftdii2c


@pytest.fixture
def mock_ftdi_utils():
    with unittest.mock.patch("servo.common.interface.ftdii2c.ftdi_utils") as mock_utils:
        mock_flib = unittest.mock.MagicMock()
        mock_lib = unittest.mock.MagicMock()
        mock_gpiolib = unittest.mock.MagicMock()
        mock_utils.load_libs.return_value = (mock_flib, mock_lib, mock_gpiolib)
        mock_utils.get_interface_and_pid.return_value = (2, 0x1234)
        yield mock_utils, mock_flib, mock_lib, mock_gpiolib


def test_fi2c_error():
    err = ftdii2c.Fi2cError("test", 1)
    assert err.msg == "test"
    assert err.value == 1


def test_fi2c_init(mock_ftdi_utils):
    unused_x, mock_flib, mock_lib, unused_x = mock_ftdi_utils
    mock_flib.ftdi_init.return_value = 0
    mock_lib.fi2c_init.return_value = 0

    fobj = ftdii2c.Fi2c(serialname="12345")
    mock_flib.ftdi_init.assert_called_once()
    mock_lib.fi2c_init.assert_called_once()

    assert fobj._is_closed is True
    assert fobj.name() == "ftdi_i2c"


def test_fi2c_init_errors(mock_ftdi_utils):
    unused_x, mock_flib, mock_lib, unused_x = mock_ftdi_utils
    mock_flib.ftdi_init.return_value = 1

    with pytest.raises(ftdii2c.Fi2cError, match="ftdi_init"):
        ftdii2c.Fi2c(serialname="12345")

    mock_flib.ftdi_init.return_value = 0
    mock_lib.fi2c_init.return_value = 1
    with pytest.raises(ftdii2c.Fi2cError, match="fi2c_init"):
        ftdii2c.Fi2c(serialname="12345")


def test_fi2c_open_close(mock_ftdi_utils):
    unused_x, mock_flib, mock_lib, unused_x = mock_ftdi_utils
    mock_flib.ftdi_init.return_value = 0
    mock_lib.fi2c_init.return_value = 0

    fobj = ftdii2c.Fi2c(serialname="12345")

    mock_lib.fi2c_open.return_value = 0
    fobj.open()
    assert fobj._is_closed is False
    mock_lib.fi2c_open.assert_called_once()

    mock_lib.fi2c_close.return_value = 0
    fobj.close()
    assert fobj._is_closed is True
    mock_lib.fi2c_close.assert_called_once()


def test_fi2c_open_close_errors(mock_ftdi_utils):
    unused_x, mock_flib, mock_lib, unused_x = mock_ftdi_utils
    mock_flib.ftdi_init.return_value = 0
    mock_lib.fi2c_init.return_value = 0

    fobj = ftdii2c.Fi2c(serialname="12345")
    mock_lib.fi2c_open.return_value = 1
    with pytest.raises(ftdii2c.Fi2cError, match="fi2c_open"):
        fobj.open()

    fobj._is_closed = False
    mock_lib.fi2c_close.return_value = 1
    with pytest.raises(ftdii2c.Fi2cError, match="fi2c_close"):
        fobj.close()
    fobj._is_closed = True


def test_fi2c_del(mock_ftdi_utils):
    unused_x, mock_flib, mock_lib, unused_x = mock_ftdi_utils
    mock_flib.ftdi_init.return_value = 0
    mock_lib.fi2c_init.return_value = 0
    mock_lib.fi2c_close.return_value = 0

    fobj = ftdii2c.Fi2c(serialname="12345")
    fobj._is_closed = False

    # We call __del__ explicitly but we need to mock close properly so it doesn't fail
    # We did this by mocking fi2c_close to 0.
    # Since __del__ ignores return we just verify close was called.
    del fobj

    fobj2 = ftdii2c.Fi2c(serialname="12345")
    fobj2._is_closed = True
    del fobj2

    # Test parent__del__ being called if exists
    # Cannot patch __bases__ directly easily, let's skip
    mock_lib.fi2c_close.assert_called_once()


def test_fi2c_build(mock_ftdi_utils):
    mock_utils, mock_flib, mock_lib, unused_x = mock_ftdi_utils
    mock_flib.ftdi_init.return_value = 0
    mock_lib.fi2c_init.return_value = 0
    mock_lib.fi2c_open.return_value = 0
    mock_lib.fi2c_setclock.return_value = 0

    # Let's cleanly patch open and setclock to avoid __del__ issues on test teardown
    with unittest.mock.patch(
        "servo.common.interface.ftdii2c.Fi2c.open"
    ), unittest.mock.patch("servo.common.interface.ftdii2c.Fi2c.setclock"):

        fobj = ftdii2c.Fi2c.build(
            index=1,
            vid=0x1234,
            pid=0x5678,
            sid="TESTSID",
            interface_data={"interface": 3},
        )

        mock_utils.get_interface_and_pid.assert_called_once_with(1, 0x5678)
        assert fobj._is_closed is True  # since we mocked open, it wasn't set to False


def test_fi2c_setclock_error(mock_ftdi_utils):
    unused_x, mock_flib, mock_lib, unused_x = mock_ftdi_utils
    mock_flib.ftdi_init.return_value = 0
    mock_lib.fi2c_init.return_value = 0

    fobj = ftdii2c.Fi2c(serialname="12345")
    mock_lib.fi2c_setclock.return_value = 1
    with pytest.raises(ftdii2c.Fi2cError, match="fi2c_setclock"):
        fobj.setclock()


def test_fi2c_raw_wr_rd(mock_ftdi_utils):
    unused_x, mock_flib, mock_lib, unused_x = mock_ftdi_utils
    mock_flib.ftdi_init.return_value = 0
    mock_lib.fi2c_init.return_value = 0

    fobj = ftdii2c.Fi2c(serialname="12345")

    def wr_rd_side_effect(
        unused_fic, unused_wbuf, unused_wcnt, unused_rbuf, unused_rcnt
    ):
        # the type is _ctypes.CArgObject which is a wrapper. We can't access rbuf[i].
        # We just return 0 to indicate success, the result will just be a list of 0s.
        return 0

    mock_lib.fi2c_wr_rd.side_effect = wr_rd_side_effect

    res = fobj._raw_wr_rd(0x50, [1, 2, 3], 2)
    assert res == [0, 0]
    mock_lib.fi2c_wr_rd.assert_called_once()


def test_fi2c_raw_wr_rd_error(mock_ftdi_utils):
    unused_x, mock_flib, mock_lib, unused_x = mock_ftdi_utils
    mock_flib.ftdi_init.return_value = 0
    mock_lib.fi2c_init.return_value = 0

    fobj = ftdii2c.Fi2c(serialname="12345")
    mock_lib.fi2c_wr_rd.return_value = 1

    with pytest.raises(ftdii2c.Fi2cError, match="fi2c_wr_rd"):
        fobj._raw_wr_rd(0x50, None, None)


def test_fi2c_gpio_wr_rd(mock_ftdi_utils):
    unused_x, mock_flib, mock_lib, mock_gpiolib = mock_ftdi_utils
    mock_flib.ftdi_init.return_value = 0
    mock_lib.fi2c_init.return_value = 0

    fobj = ftdii2c.Fi2c(serialname="12345")
    fobj._i2c_mask = 0b00000000  # Make sure no collision

    def gpio_side_effect(unused_fic, unused_gpio, unused_rd_val, unused_type_val):
        # We can't easily set rd_val because it's a byref wrapper, we just let it return 0
        # which means the masked result will be 0
        return 0

    mock_gpiolib.fgpio_wr_rd.side_effect = gpio_side_effect

    res = fobj.gpio_wr_rd(1, 2, dir_val=1, wr_val=1)
    assert res == 0
    mock_gpiolib.fgpio_wr_rd.assert_called_once()

    mock_gpiolib.fgpio_wr_rd.reset_mock()
    res = fobj.gpio_wr_rd(1, 2)  # Read only
    assert res == 0
    mock_gpiolib.fgpio_wr_rd.assert_called_once()


def test_fi2c_gpio_wr_rd_mask_violation(mock_ftdi_utils):
    unused_x, mock_flib, mock_lib, unused_x = mock_ftdi_utils
    mock_flib.ftdi_init.return_value = 0
    mock_lib.fi2c_init.return_value = 0

    fobj = ftdii2c.Fi2c(serialname="12345")
    fobj._i2c_mask = 0b11111111  # Total collision

    with pytest.raises(ftdii2c.Fi2cError, match="gpio mask violates i2c mask"):
        fobj.gpio_wr_rd(1, 2)
