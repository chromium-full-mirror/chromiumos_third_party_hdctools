# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# pylint: disable=unused-argument, pointless-statement, redefined-outer-name, unnecessary-dunder-call


import struct
import unittest.mock

import pytest

from servo.common.interface import stm32gpio


@pytest.fixture
def mock_susb():
    with unittest.mock.patch(
        "servo.common.interface.stm32gpio.stm32usb.Susb"
    ) as mock_susb_class:
        mock_inst = unittest.mock.MagicMock()
        mock_susb_class.return_value = mock_inst
        yield mock_inst


def test_sgpio_error():
    err = stm32gpio.SgpioError("test", 1)
    assert err.msg == "test"
    assert err.value == 1


def test_sgpio_init(mock_susb):
    sgpio = stm32gpio.Sgpio()
    assert sgpio._susb == mock_susb


def test_sgpio_build(mock_susb):
    sgpio = stm32gpio.Sgpio.build(
        vid=0x1234, pid=0x5678, sid="TESTSID", interface_data={"interface": 3}
    )
    assert sgpio._susb == mock_susb
    assert sgpio.name() == "stm32_gpio"


def test_sgpio_del(mock_susb):
    sgpio = stm32gpio.Sgpio()
    sgpio.__del__()


def test_sgpio_close(mock_susb):
    sgpio = stm32gpio.Sgpio()
    sgpio.close()
    with pytest.raises(AttributeError):
        sgpio._susb  # should be deleted


def test_sgpio_reinitialize(mock_susb):
    sgpio = stm32gpio.Sgpio()
    sgpio.reinitialize()
    mock_susb.reset_usb.assert_called_once()


def test_sgpio_get_device_info(mock_susb):
    sgpio = stm32gpio.Sgpio()
    mock_susb.get_device_info.return_value = "info"
    assert sgpio.get_device_info() == "info"


def test_sgpio_wr_rd(mock_susb):
    sgpio = stm32gpio.Sgpio()

    # Needs to return 4 bytes for read_ep
    # First call: read mask for debug
    # write_ep returns 8
    # Next two calls: read mask again
    mock_susb.read_ep.side_effect = [
        struct.pack("<I", 0x12345678),  # init
        struct.pack("<I", 0x12345678),  # first read
        struct.pack("<I", 0x87654321),  # second read mask -> output
    ]
    mock_susb.write_ep.return_value = 8

    # read value should be (0x87654321 >> 2) & 1 == (2271560481 >> 2) & 1
    # 0x87654321 = 0b10000111011001010100001100100001. bit 2 is 0.
    res = sgpio.wr_rd(offset=2, width=1, wr_val=1)
    assert res == 0
    assert mock_susb.write_ep.call_count == 1

    # check no wr_val logic
    mock_susb.read_ep.side_effect = [
        struct.pack("<I", 0x12345678),  # init
        struct.pack("<I", 0x12345678),  # first read
        struct.pack("<I", 0x87654321),  # second read mask -> output
    ]
    mock_susb.write_ep.reset_mock()
    res = sgpio.wr_rd(offset=2, width=1, wr_val=None)
    assert (
        mock_susb.write_ep.call_count == 1
    )  # it writes 0s because of `set_mask = 0, clear_mask = 0`!


def test_sgpio_wr_rd_errors(mock_susb):
    sgpio = stm32gpio.Sgpio()

    # write error
    mock_susb.read_ep.return_value = struct.pack("<I", 0x12345678)
    mock_susb.write_ep.return_value = 4  # expected 8

    with pytest.raises(stm32gpio.SgpioError, match="Wrote 4 bytes, expected 8"):
        sgpio.wr_rd(offset=2, width=1, wr_val=1)

    # read error
    mock_susb.write_ep.return_value = 8
    mock_susb.read_ep.side_effect = [
        struct.pack("<I", 0x12345678),  # init
        struct.pack("<I", 0x12345678),  # first read
        b"\x00\x00\x00",  # second read mask -> output -> 3 bytes
    ]
    with pytest.raises(stm32gpio.SgpioError, match="Read error: expected 4 bytes"):
        sgpio.wr_rd(offset=2, width=1, wr_val=1)
