# Copyright 2019 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Driver for power button servo feature."""

from servo.common.utils import keyboard_handlers
from servo.drv import hw_driver


class PowerKbError(hw_driver.HwDriverError):
    """Error class for powerKb class."""


# pylint: disable=invalid-name
# Servod requires camel-case class names
class powerKb(hw_driver.HwDriver):
    """HwDriver wrapper around servod's power key functions."""

    def _drv_init(self):
        """Driver specific initializer."""
        super()._drv_init()
        # pylint: disable=protected-access
        self._handler = keyboard_handlers._BaseHandler(self.grpc_core_addr)

    def _set(self, duration):
        """Press power button for |duration| seconds.

        Args:
          duration: seconds to hold the key pressed.
        """
        self._handler.power_key(press_secs=duration)
