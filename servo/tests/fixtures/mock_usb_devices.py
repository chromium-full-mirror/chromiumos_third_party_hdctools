# Copyright 2022 The ChromiumOS Authors.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

from functools import partial

import pytest
from servo.tests.data import mocked_pty_data

_logger = logging.getLogger("mock_servos")


@pytest.fixture(scope="function")
def mock_v4p1_configuration(mocker, mock_interface):
    def generate_mock_v4p1_configuration():
        mock_cfg = mocker.Mock(name="Servo V4.1 Configuration")

        mock_cfg.interfaces = {
            0: mock_interface(
                0,
                [1, 129],
                "[servo console stm32_uart]",
                mock_cfg,
                mocked_pty_data.MOCKED_SERVO41_CONSOLE_DATA,
                b"",
            ),  # servo console stm32_uart
            2: mock_interface(
                2,
                [3, 131],
                "[servo v4 i2c stm32_i2c]",
                mock_cfg,
                mocked_pty_data.MOCKED_SERVO41_I2C_DATA,
                b"",
            ),  # i2c, stm32_i2c
            3: mock_interface(
                3, [4, 132], "[dut sbu uart stm32_uart]", mock_cfg, {}, b""
            ),  # dut sbu uart stm32_uart
            4: mock_interface(
                4,
                [5, 133],
                "[atmega uart stm32_uart]",
                mock_cfg,
                mocked_pty_data.MOCKED_SERVO41_ATMEGA_DATA,
                b"",
            ),  # atmega uart stm32_uart
        }

        def find_interface(mock_cfg, find_all, custom_match, args):
            return mock_cfg.interfaces[args["bInterfaceNumber"]]

        mock_cfg.find_descriptor.side_effect = partial(find_interface, mock_cfg)

        return mock_cfg

    return generate_mock_v4p1_configuration


@pytest.fixture(scope="function")
def mock_cr50_configuration(mocker, mock_interface):
    def generate_mock_cr50_configuration():
        mock_cfg = mocker.Mock(name="Servo V4.1 Configuration")

        mock_cfg.interfaces = {
            0: mock_interface(
                0,
                [1, 129],
                "[CR50 console, stm32_uart]",
                mock_cfg,
                mocked_pty_data.MOCKED_CR50_CONSOLE_DATA,
                None,
            ),  # CR50 console, stm32_uart
            1: mock_interface(
                1,
                [2, 130],
                "[AP, stm32_uart]",
                mock_cfg,
                mocked_pty_data.MOCKED_CR50_AP_DATA,
                b"",
            ),  # AP, stm32_uart
            2: mock_interface(
                2,
                [3, 131],
                "[EC/PD, stm32_uart]",
                mock_cfg,
                mocked_pty_data.MOCKED_EC_PD_CONSOLE_DATA,
                b"",
            ),  # EC/PD, stm32_uart
            5: mock_interface(
                5,
                [6, 134],
                "[cr50 i2c, stm32_i2c]",
                mock_cfg,
                mocked_pty_data.MOCKED_CR50_I2C_DATA,
                b"",
            ),  # i2c, stm32_i2c
        }

        def find_interface(mock_cfg, find_all, custom_match, args):
            return mock_cfg.interfaces[args["bInterfaceNumber"]]

        mock_cfg.find_descriptor.side_effect = partial(find_interface, mock_cfg)

        return mock_cfg

    return generate_mock_cr50_configuration


@pytest.fixture(scope="function")
def mock_v4p1_usb_device(mock_usb_device, mock_v4p1_configuration):
    def create_device(mock_usb_device, iSerial, bus, address):
        mock_device = mock_usb_device(
            "Servo V4.1 Device", 0x18D1, 0x520D, mock_v4p1_configuration
        )
        mock_device.iSerial = iSerial
        mock_device.bus = bus
        mock_device.address = address
        return mock_device

    return partial(create_device, mock_usb_device)


@pytest.fixture(scope="function")
def mock_cr50_usb_device(mock_usb_device, mock_cr50_configuration):
    def create_device(mock_usb_device, iSerial, bus, address):
        mock_device = mock_usb_device(
            "CR50 Device", 0x18D1, 0x5014, mock_cr50_configuration
        )
        mock_device.iSerial = iSerial
        mock_device.bus = bus
        mock_device.address = address
        return mock_device

    return partial(create_device, mock_usb_device)


@pytest.fixture(scope="function")
def mock_usb_device(mocker):
    """Generic mock for a USB device.

    Args:
        mocker (): Mocker module injected by pytest.
    """

    def create_device(name, idVendor, idProduct, configuration):
        """Create a new mock USB device

        Args:
            name (string): Name of the device, used for debug/logging.
            idVendor (integer): vendor id of the usb device
            idProduct (integer): product id of the usb device
            configuration (Mock): Mock configuration for the usb device.

        Returns:
            Mock: A mock that represents a USB device in PyUSB.
        """
        mock_device = mocker.Mock(name=name)
        mock_device.idProduct = idProduct
        mock_device.idVendor = idVendor
        mock_device.configuration = configuration()
        mock_device.get_active_configuration.return_value = mock_device.configuration
        return mock_device

    return create_device
