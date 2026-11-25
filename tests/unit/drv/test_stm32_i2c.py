# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest
from unittest import mock

from servo.common.interface import stm32i2c
from servo.drv import stm32_i2c


class TestStm32I2cDrv(unittest.TestCase):
    def test_get_usb_endpoint_responsive_returns_one_when_healthy(self) -> None:
        bus_mock = mock.create_autospec(stm32i2c.Si2cBus, instance=True)
        bus_mock.is_endpoint_responsive.return_value = True
        driver = stm32_i2c.stm32I2c(
            None,
            None,
            bus_mock,
            {"cmd": "get", "subtype": "usb_endpoint_responsive"},
        )

        self.assertEqual(driver.get(), 1)
        bus_mock.is_endpoint_responsive.assert_called_once_with()

    def test_get_usb_endpoint_responsive_returns_zero_when_wedged(self) -> None:
        bus_mock = mock.create_autospec(stm32i2c.Si2cBus, instance=True)
        bus_mock.is_endpoint_responsive.return_value = False
        driver = stm32_i2c.stm32I2c(
            None,
            None,
            bus_mock,
            {"cmd": "get", "subtype": "usb_endpoint_responsive"},
        )

        self.assertEqual(driver.get(), 0)
        bus_mock.is_endpoint_responsive.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
