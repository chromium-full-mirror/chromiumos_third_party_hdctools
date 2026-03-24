# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Power state driver for the reven board that doesn't use EC."""

import time

from servo.drv import hw_driver
from servo.drv import power_state


class RevenPowerError(hw_driver.HwDriverError):
    """Error class for RevenPower errors."""


class revenPower(power_state.PowerStateDriver):
    """Driver for power_state for reven boards.

    This class overrides functions in the PowerStateDriver and customizes them
    for Flex DUTs that use the servo_reven_overlay.xml overlay.
    This class implements power on, power off and reset by sending commands to the
    relay switch driver instead of the EC.
    """

    _POWER_OFF_TIME_CONTROL = "power_off_time"
    _DEFAULT_POWER_ON_PRESS_LENGTH_S = 0.3
    _DEFAULT_RESET_TIME_BUFFER_S = 3

    def _drv_init(self):
        """Driver specific initializer."""
        super()._drv_init()

    def _Get_power_off_time(self):
        """Get value of power_off_time.

        Returns:
          Time necessary to hold down power button to turn off dut

        Raises:
          RevenPowerError: if power_off_time is an invalid value
        """
        off_time_str = self._servod_get(self._POWER_OFF_TIME_CONTROL)
        try:
            off_time = float(off_time_str)
        except ValueError:
            raise RevenPowerError(
                "Control: %r is invalid when it's a string: %r"
                % (self._POWER_OFF_TIME_CONTROL, off_time_str)
            ) from None

        if off_time <= 0:
            raise RevenPowerError(
                "Control %r is invalid when it's less than 0: %r"
                % (self._POWER_OFF_TIME_CONTROL, off_time)
            )
        return off_time

    def _power_off(self, press_secs=-1):
        """Powers off the Reven DUT.

        Args:
          press_secs: int, how long to hold switch down
        """
        if press_secs < 0:
            press_secs = self._Get_power_off_time()
        # power off device by sending a command to the relay switch
        self._servod_set("relay_pwrbtn_press", press_secs)

    def _power_on(self, rec_mode, press_secs=-1):
        """Powers on the Reven DUT and returns an error message if recovery mode is enabled.

        Args:
          rec_mode: str, represents the recovery mode selected
          press_secs: int, how long to hold switch down

        Raises:
          RevenPowerError: if recovery mode is set to anything but off
        """
        if press_secs < 0:
            press_secs = self._DEFAULT_POWER_ON_PRESS_LENGTH_S
        # Confirm that recovery mode is correctly set to off,
        # as reven boards don't have recovery mode
        if rec_mode == self.REC_OFF:
            # power on device by sending a command to the relay switch
            self._servod_set("relay_pwrbtn_press", press_secs)
        else:
            raise RevenPowerError(
                f"Invalid, Flex doesn't have any recovery modes. "
                f"Try one of: {self._STATE_ON}, {self._STATE_OFF}, "
                f"{self._STATE_RESET_CYCLE}"
            )

    def _reset_cycle(self, time_buffer=-1):
        """Resets the Reven DUT."""
        if time_buffer < 0:
            time_buffer = self._DEFAULT_RESET_TIME_BUFFER_S

        self._power_off()
        time.sleep(time_buffer)
        self._power_on(self.REC_OFF)
        time.sleep(time_buffer)
