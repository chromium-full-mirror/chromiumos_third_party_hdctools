# Copyright 2016 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from servo.drv import cr50
from servo.drv import fw_wp_state

from servo.drv import hw_driver

class fwWpCcdError(hw_driver.HwDriverError):
  """Exception class for fwWpCcd."""


class fwWpCcd(fw_wp_state.FwWpStateDriver, cr50.cr50):
  """Driver for fw_wp_state for boards with CCD."""

  def _force_on(self):
    """Force the firmware to write-protected."""
    self._issue_cmd('wp on')

  def _force_off(self):
    """Force the firmware to not write-protected."""
    self._issue_cmd('wp off')

  def _reset(self):
    """Reset the firmware write-protection state to the system value."""
    self._issue_cmd('wp follow_batt_pres')

  @cr50.restricted_command
  def _get_state(self):
    """Get the firmware write-protection state."""
    # The output string is defined in ec/board/cr50/wp.c
    result = self._issue_cmd_get_results(
        'wp', [r'Flash WP:([ A-z]*(enabled|disabled))'])[0]
    if result is None:
      raise fwWpCcdError('Cannot retrieve wp result on CCD console.')

    if 'fwmp' in result[1]:
        self._logger.warning('FWMP is forcing WP enable.')
        self._logger.warning('Clear the FWMP to reset wp.')
    forced = 'forced' in result[1]
    if 'enabled' in result[1]:
      return self._STATE_FORCE_ON if forced else self._STATE_ON
    return self._STATE_FORCE_OFF if forced else self._STATE_OFF
