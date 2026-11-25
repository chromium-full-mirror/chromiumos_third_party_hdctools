# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Driver for STM32 USB I2C interface diagnostics."""

from servo.drv import hw_driver


# pylint: disable=invalid-name
class stm32I2c(hw_driver.HwDriver):
    """Driver for drv=stm32_i2c controls."""

    def _Get_usb_endpoint_responsive(self) -> int:
        """Checks whether the STM32 USB I2C bulk endpoint is responsive."""
        return int(self._interface.is_endpoint_responsive())
