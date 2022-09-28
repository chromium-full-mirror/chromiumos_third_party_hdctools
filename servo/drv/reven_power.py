# Copyright (c) 2023 The Chromium OS Authors. All rights reserved.
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

  This class overrides functions in the PowerStateDriver and customizes them for Flex DUTs
  that use the servo_reven_overlay.xml overlay.
  This class implements power on, power off and reset by sending commands to the relay
  switch driver instead of the EC.
  """
  _DEFAULT_POWER_ON_PRESS_LENGTH_S = 0.3
  _DEFAULT_POWER_OFF_PRESS_LENGTH_S = 8
  _DEFAULT_RESET_TIME_BUFFER_S = 3

  def __init__(self, interface, params, servod):
    """Initialize driver by initializing HwDriver."""
    super(revenPower, self).__init__(interface, params, servod)

  def _power_off(self, press_secs=-1):
    """Powers off the Reven DUT
    Args:
      press_secs: int, how long to hold switch down
    """
    if press_secs < 0:
        press_secs = self._DEFAULT_POWER_OFF_PRESS_LENGTH_S
    # power off device by sending a command to the relay switch
    self._servod_set('relay_pwrbtn_press', press_secs)

  def _power_on(self, rec_mode, press_secs=-1):
    """Powers on the Reven DUT and returns an error message if recovery mode is enabled

    Args:
      rec_mode: str, represents the recovery mode selected
      press_secs: int, how long to hold switch down

    Raises:
      RevenPowerError if recovery mode is set to anything but off
    """
    if press_secs < 0:
      press_secs = self._DEFAULT_POWER_ON_PRESS_LENGTH_S
    # Confirm that recovery mode is correctly set to off, as reven boards don't have recovery mode
    if rec_mode == self.REC_OFF:
      # power on device by sending a command to the relay switch
      self._servod_set('relay_pwrbtn_press', press_secs)
    else:
        raise RevenPowerError(f"Invalid, Flex doesn't have any recovery modes. Try one of: "
                              f"{self._STATE_ON}, {self._STATE_OFF}, {self._STATE_RESET_CYCLE}")

  def _reset_cycle(self, time_buffer= -1):
    """Resets the Reven DUT"""
    if time_buffer < 0:
        time_buffer = self._DEFAULT_RESET_TIME_BUFFER_S

    self._power_off()
    time.sleep(time_buffer)
    self._power_on(self.REC_OFF)
    time.sleep(time_buffer)
