# Copyright 2015 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import json

from servo.data.drv import hw_driver


class crosChip(hw_driver.HwDriver):
    """Driver for getting chip name of EC or PD."""

    def __init__(self, interface, params, servod):
        """Constructor.

        Args:
          interface: hardware interface for low-level communication; ignored here
          params: dictionary of params
        """
        super(crosChip, self).__init__(interface, params, servod)

    def _Get_chip(self):
        """Get the EC chip name."""
        return self._driver_client.GetCrosChip(name=json.dumps(self._params)).resposne
