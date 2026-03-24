# Copyright 2015 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import json

from servo.drv import hw_driver


class crosChip(hw_driver.HwDriver):
    """Driver for getting chip name of EC or PD."""

    def _drv_init(self):
        """Driver specific initializer."""
        super()._drv_init()

    def _Get_chip(self):
        """Get the EC chip name."""
        return self._driver_client.GetCrosChip(name=json.dumps(self._params)).response
