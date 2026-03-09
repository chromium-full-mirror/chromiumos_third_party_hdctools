# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# pylint: disable=redefined-outer-name
import unittest.mock

import pytest
import usb.core
import usb.util

from servo_updater.ecusb import stm32usb


@pytest.fixture
def mock_usb():
    with unittest.mock.patch(
        "servo_updater.ecusb.stm32usb.usb.core.find"
    ) as mock_find, unittest.mock.patch(
        "servo_updater.ecusb.stm32usb.usb.util.get_string"
    ) as mock_get_string, unittest.mock.patch(
        "servo_updater.ecusb.stm32usb.usb.util.find_descriptor"
    ) as mock_find_descriptor, unittest.mock.patch(
        "servo_updater.ecusb.stm32usb.usb.util.dispose_resources"
    ) as mock_dispose:
        yield mock_find, mock_get_string, mock_find_descriptor, mock_dispose


def test_susb_error():
    err = stm32usb.SusbError("test", 1)
    assert err.msg == "test"
    assert err.value == 1


def test_susb_init_no_devices(mock_usb):
    mock_find, unused_x, unused_x, unused_x = mock_usb
    mock_find.return_value = iter([])

    with pytest.raises(stm32usb.SusbError, match="USB device not found"):
        stm32usb.Susb()


def test_susb_init_with_serialname_found(mock_usb):
    mock_find, mock_get_string, mock_find_descriptor, unused_x = mock_usb

    mock_dev1 = unittest.mock.MagicMock()
    mock_dev2 = unittest.mock.MagicMock()
    mock_find.return_value = iter([mock_dev1, mock_dev2])

    # Let's say dev2 has the matching serial
    mock_get_string.side_effect = lambda dev, i: (
        "SERIAL2" if dev == mock_dev2 else "SERIAL1"
    )

    mock_cfg = unittest.mock.MagicMock()
    mock_dev2.get_active_configuration.return_value = mock_cfg
    mock_dev2.is_kernel_driver_active.return_value = True

    mock_intf = unittest.mock.MagicMock()
    mock_intf.bInterfaceNumber = 1

    mock_read_ep = unittest.mock.MagicMock()
    mock_write_ep = unittest.mock.MagicMock()

    # find_descriptor gets called 3 times:
    # 1. find interface
    # 2. find read ep
    # 3. find write ep
    mock_find_descriptor.side_effect = [mock_intf, mock_read_ep, mock_write_ep]

    susb = stm32usb.Susb(serialname="SERIAL2")

    assert susb._dev == mock_dev2
    assert susb._intf == mock_intf
    assert susb._read_ep == mock_read_ep
    assert susb._write_ep == mock_write_ep
    mock_dev2.set_configuration.assert_called_once()
    mock_dev2.detach_kernel_driver.assert_called_once_with(1)


def test_susb_init_with_serialname_not_found(mock_usb):
    mock_find, mock_get_string, unused_x, unused_x = mock_usb

    mock_dev = unittest.mock.MagicMock()
    mock_find.return_value = iter([mock_dev])
    mock_get_string.return_value = "WRONG_SERIAL"

    with pytest.raises(
        stm32usb.SusbError, match="USB device\\(TARGET_SERIAL\\) not found"
    ):
        stm32usb.Susb(serialname="TARGET_SERIAL")


def test_susb_init_first_device_fallback(mock_usb):
    mock_find, unused_x, mock_find_descriptor, unused_x = mock_usb

    mock_dev = unittest.mock.MagicMock()
    mock_find.return_value = iter([mock_dev])

    # Mock finding nothing for interface
    mock_find_descriptor.return_value = None

    with pytest.raises(stm32usb.SusbError, match="Interface .* not found"):
        stm32usb.Susb()


def test_susb_set_configuration_error(mock_usb):
    mock_find, unused_x, mock_find_descriptor, unused_x = mock_usb
    mock_dev = unittest.mock.MagicMock()
    mock_find.return_value = iter([mock_dev])
    mock_dev.set_configuration.side_effect = usb.core.USBError("test")

    mock_intf = unittest.mock.MagicMock()
    mock_intf.bInterfaceNumber = 1
    mock_find_descriptor.side_effect = [
        mock_intf,
        unittest.mock.MagicMock(),
        unittest.mock.MagicMock(),
    ]

    # Should catch and ignore USBError during set_configuration
    susb = stm32usb.Susb()
    assert susb._dev == mock_dev


def test_susb_close(mock_usb):
    mock_find, unused_x, mock_find_descriptor, mock_dispose = mock_usb
    mock_dev = unittest.mock.MagicMock()
    mock_find.return_value = iter([mock_dev])
    mock_intf = unittest.mock.MagicMock()
    mock_find_descriptor.side_effect = [
        mock_intf,
        unittest.mock.MagicMock(),
        unittest.mock.MagicMock(),
    ]

    susb = stm32usb.Susb()
    susb.close()
    mock_dispose.assert_called_once_with(mock_dev)
