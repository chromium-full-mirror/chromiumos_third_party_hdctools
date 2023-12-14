# Copyright 2019 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for controlling the watchdog."""

from servo import servo_dev_templates
from servo.data.drv import hw_driver


class servoWatchdogError(hw_driver.HwDriverError):
    """Exception class for servo watchdog."""


class servoWatchdog(hw_driver.HwDriver):
    """Class to control the watchdog."""

    def __init__(self, interface, params):
        """Initialize all information needed by servo watchdog."""
        super(servoWatchdog, self).__init__(interface, params)

    def _Get_watchdog(self):
        """Get the connected state of all devices."""
        return self._driver_client.GetWatchdog().response

    def _Set_watchdog_add(self, val):
        """Signal a device may not be disconnected."""
        self._driver_client.UpdateDeviceDisconnectOk(name=val, disconnect_ok=False)

    def _Set_watchdog_remove(self, val):
        """Signal a device may be disconnected."""
        self._driver_client.UpdateDeviceDisconnectOk(name=val, disconnect_ok=True)

    def _Get_ccd_state(self):
        """Check the watchdog to see if ccd is enabled.

        Returns:
          0: ccd is off.
          1: ccd is on.
        """
        return self._driver_client.GetCcdState().state
