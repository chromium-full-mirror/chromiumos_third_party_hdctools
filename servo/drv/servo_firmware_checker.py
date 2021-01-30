# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver to check whether the firmware is up to date."""

from servo.drv import hw_driver
import servo_updater

class servoFirmwareCheckerError(hw_driver.HwDriverError):
  """Error class for his module."""
  pass

class servoFirmwareChecker(hw_driver.HwDriver):
  """class to handle checking and reporting on errors."""

  REQUIRED_PARAMS = ['board']

  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: servod instance
      params: control params, of which we actively care about:
        - board: the servo board name
    """
    super(servoFirmwareChecker, self).__init__(interface, params)

    # Set can be used by passing 'print' as an argument.
    self._choices = {0}
    self._board = self._params['board']
    self._logger.debug('')
    self._current_fw_cmd = '%s_version' % (self._board,)
    self._latest_fw_cmd = '%s_latest_version' % (self._board,)

  def get(self):
    """Get available firmware version for |self._board| on |self._channel|.

    Returns:
        True if |{self._board}_version| == |{self._board}_latest_version|
        False otherwise
    """
    current = self._interface.get(self._current_fw_cmd)
    latest = self._interface.get(self._latest_fw_cmd)
    return int(latest == current)

  def set(self, _):
    """Print what the current firmware is, what the latest available is."""
    current = self._interface.get(self._current_fw_cmd)
    latest = self._interface.get(self._latest_fw_cmd)
    if self.get():
      self._logger.info('%s firmware up to date.', self._board)
    else:
      self._logger.info('current %r firmware: %s', self._board, current)
      self._logger.info('latest %r firmware: %s', self._board, latest)
      # Warn the user to upgrade if needed.
      self._logger.warn('======Warning======')
      self._logger.warn('Not running latest stable firmware.')
      self._logger.warn('Please run %r if desired to rectify.',
                        'sudo servo_updater --board %s' % self._board)
      self._logger.warn('======Warning======')
