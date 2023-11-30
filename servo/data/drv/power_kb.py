# Copyright 2019 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Driver for power button servo feature."""

from servo.data.drv import hw_driver
from servo.data.drv import keyboard_handlers


class PowerKbError(hw_driver.HwDriverError):
    """Error class for powerKb class."""


# pylint: disable=invalid-name
# Servod requires camel-case class names
class powerKb(hw_driver.HwDriver):
    """HwDriver wrapper around servod's power key functions."""

    def __init__(self, interface, params, servod):
        """Constructor.

        Args:
          interface: hardware interface for low-level communication; ignored here
          params: dictionary of params;
          servod: Servod that is used for cross-servo-device communication
        """
        super(powerKb, self).__init__(interface, params.copy(), servod)
        # pylint: disable=protected-access
        self._handler = keyboard_handlers._BaseHandler(self._servod)

    def _set(self, duration):
        """Press power button for |duration| seconds.

        Args:
          duration: seconds to hold the key pressed.
        """
        self._handler.power_key(press_secs=duration)
