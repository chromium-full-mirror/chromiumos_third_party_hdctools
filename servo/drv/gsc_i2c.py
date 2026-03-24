# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Driver for GSC I2C interface
This is for the special-purpose commands that GSC can handle.
"""

from servo.drv import hw_driver


CMD_MASK = 0xFF


class gscI2cError(hw_driver.HwDriverError):
    """Error class for gscI2c"""


class gscI2c(hw_driver.HwDriver):
    """Object to access gsc via i2c."""

    def _drv_init(self):
        """Driver specific initializer.

        Required params:
            child: integer, 7-bit i2c child address
        """
        super()._drv_init()

        self._child = int(self._params["child"], 0)

    def _set(self, logical_value):
        """send a special command to GSC.

        Args:
        logical_value: a special command in 8-bit unsigned integer

        Raises:
        gscI2cError: if logical_value is out of bounds
        """
        if logical_value & ~CMD_MASK:
            raise gscI2cError(
                f"command value 0x{logical_value:02X} does not match 0x{CMD_MASK:02X}"
            )
        self._interface.wr_rd(self._child, [logical_value], 0)
