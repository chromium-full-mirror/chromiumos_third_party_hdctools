# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Echo servod driver that can be used to store constants for overlays."""

from servo.drv import hw_driver


class echo(hw_driver.HwDriver):
    """Driver to echo values back."""

    def _drv_init(self):
        """Driver specific initializer."""
        # pylint: disable=invalid-name
        # Class name format needed for drv class routing in servod.
        super()._drv_init()
        self._val = self._params.get("value", "unknown")

    def _get(self):
        """Return the value."""
        return self._val
