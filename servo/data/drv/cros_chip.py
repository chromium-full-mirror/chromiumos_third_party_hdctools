# Copyright 2015 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from servo.data.drv import hw_driver


class crosChip(hw_driver.HwDriver):
    """Driver for getting chip name of EC or PD."""

    def _drv_init(self):
        """Driver specific initializer."""
        super(crosChip, self)._drv_init()
        default_chip = self._params.get("chip", "unknown")
        devices = self._servod.get_devices()
        default_device = self._servod.get_main_device()
        self._chips = {}
        for device in devices:
            self._chips[device] = self._params.get(
                "chip_for_" + device.template.TYPE, default_chip
            )
        self._chip = self._chips[default_device]

    def _Get_chip(self):
        """Get the EC chip name."""
        return self._chip
