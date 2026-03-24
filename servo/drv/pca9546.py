# Copyright 2011 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
""" """
from servo.drv import hw_driver


CMD_MASK = 0xF


class Pca9546Error(hw_driver.HwDriverError):
    """Error class for PCA9546"""


class pca9546(hw_driver.HwDriver):
    """Object to access drv=pca9546 controls."""

    def _drv_init(self):
        """Driver specific initializer.

        Required params:
          child: integer, 7-bit i2c child address
        """
        super()._drv_init()

        self._child = int(self._params["child"], 0)

    def _get(self):
        """Get PCA9546 mux."""
        return self._interface.wr_rd(self._child, [], 1)[0]

    def _set(self, value):
        """Set PCA954 mux.

        Args:
          value: 4-bit unsigned integer to set mux output

        Raises:
          Pca9546Error: if value is out of bounds
        """
        self._logger.debug("value = %s" % str(value))
        if value & ~CMD_MASK:
            raise Pca9546Error(
                "command value 0x%x can't be greater than 0x%x" % (value, CMD_MASK)
            )
        self._interface.wr_rd(self._child, [CMD_MASK & value], 0)
