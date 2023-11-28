# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Echo servod driver that can be used to store constants for overlays."""

from servo.data.drv import hw_driver


class echo(hw_driver.HwDriver):
    """Driver to echo values back."""

    # pylint: disable=invalid-name
    # naming convention needed for servod driver query.

    def __init__(self, interface, params, servod):
        """Constructor.

        Args:
          interface: hardware interface for low-level communication; ignored here
          params: dictionary of params
          servod: Servod that is used for cross-servo-device communication
        """
        # pylint: disable=invalid-name
        # Class name format needed for drv class routing in servod.
        super(echo, self).__init__(interface, params, servod)
        self._val = self._params.get("value", "unknown")

    def _get(self):
        """Return the value."""
        return self._val
