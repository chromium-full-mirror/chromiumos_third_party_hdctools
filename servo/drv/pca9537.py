# Copyright 2011 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for board config controls pca9537, a 4-bit ioexpander."""
from servo.drv import hw_driver
from servo.drv import tca6416


class pca9537(tca6416.tca6416):
    """Object to access drv=pca9537 controls.

    Note, This gpio expander is compatible to the tca6416 driver.  Only
    difference being it has a single port and consequently different register
    indexes (REG_x below).
    """

    # base indexes of the input, output, polarity and direction registers
    # respectively.
    REG_INP = 0
    REG_OUT = 1
    REG_POL = 2
    REG_DIR = 3

    def _drv_init(self):
        """Driver specific initializer.

        Required params:
          child: integer, 7-bit i2c child address
        """
        self._params = self._params.copy()
        self._params["port"] = "0"
        super()._drv_init()
