# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver to find which channel the latest firmware is running."""

from servo.drv import hw_driver
import servo_updater

class servoUpdaterChannelParserError(hw_driver.HwDriverError):
  """Error class for his module."""
  pass

class servoUpdaterChannelParser(hw_driver.HwDriver):
  """class to handle information retrieval from servo_updater"""

  REQUIRED_GET_PARAMS = ['board']

  def __init__(self, interface, params, servod):
    """Constructor.

    Args:
      interface: hardware interface for low-level communication; ignored here
      params: control params, of which we actively care about:
        - board: the servo board name
      servod: Servod that is used for cross-servo-device communication
    """
    super(servoUpdaterChannelParser, self).__init__(interface, params, servod)

    self._board = self._params['board']
    self._logger.debug('')
    self._current_fw_cmd = '%s_version' % (self._board,)

  def _get(self):
    """Get available firmware version for |self._board| on |self._channel|.

    Returns:
        the channel the current firmware is from or 'unknown'
    """
    current = self._servod_get(self._current_fw_cmd)
    try:
      channel = servo_updater.get_firmware_channel(self._board, current)
      return channel if channel is not None else 'unknown'
    except servo_updater.ServoUpdaterException as e:
      msg = 'Failed to find out the channel of the current firmware'
      raise servoUpdaterChannelParserError(msg)
