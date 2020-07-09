# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Programmer to perform DFU flashing on servo devices."""

import os
import time

from servo_mfg import exec_util
from servo_mfg import programmer
from servo_mfg import util
import servo_updater


class ServoProgrammer(programmer.Programmer):
  """Class to perform DFU flashing on the servo stm."""

  NAME = 'Servo Firmware'

  # The default logger uses 'Programmer' but this is technically a flasher.
  LOGGER_SUFFIX = 'Flasher'

  PROGRAMMER_BIN = 'dfu-util'

  BASE_CMD = [PROGRAMMER_BIN, '-a', '0']

  ADDR = 0x08000000

  # Timeout after which to kill the subprocess. 2 minutes here.
  # Note: this is used twice. one, then a warning is printed, then once again.
  PROCESS_TIMEOUT_S = 2 * 60

  def __init__(self, board, dfu_vid, dfu_pid):
    """Initialize the logger.

    Args:
      board: servo board name
      dfu_vid: servo VID in DFU mode
      dfu_pid: servo PID in DFU mode
    """
    programmer.Programmer.__init__(self, force=False)
    self._vid = dfu_vid
    self._pid = dfu_pid
    self._board = board
    # |_bin| and |_size| get populated during the env verification.
    self._bin = None
    self._size = None
    # By setting this we avoid our `return True` _verify() from
    # stopping us from flashing.
    self._no_precheck = True

  def _program(self, **_):
    """Helper to perform actual programming."""
    # At this stage, we have already validated that |FW_BIN| exists. So create
    # the full command.

    id_cmd = ['-d', '%04x:%04x' % (self._vid, self._pid)]
    file_cmd = ['-D', self._bin]

    image_address = '0x%08x:%d' % (self.ADDR, self._size)
    erase_address = '%s:force:unprotect' % image_address

    erase_cmd = self.BASE_CMD + id_cmd + ['-s', erase_address] + file_cmd
    write_cmd = self.BASE_CMD + id_cmd + ['-s', image_address] + file_cmd

    ret, _, _ = exec_util.exec_blocking(erase_cmd, hint='erasing')
    if ret:
      self.throw_error('Failed to erase.')
    time.sleep(1)
    ret, _, _ = exec_util.exec_blocking(write_cmd, hint='writing')
    if ret:
      self.throw_error('Failed to write.')

  def _verify(self, **_):
    """Helper to verify that programming succeeded."""
    # There is not really a way for us to verify if this succeeded
    # or not. Just return true always.
    return True

  def _verify_programming_env(self):
    """Helper to validate that programming tools are available."""
    # Find the binary file and get the full path, and the size
    # find the programming tool
    _, self._bin, _ = servo_updater.get_files_and_version(self._board, None)
    self._size = os.path.getsize(self._bin)
    if not util.validate_exec_available(self.PROGRAMMER_BIN):
      self.exec_missing(self.PROGRAMMER_BIN)
