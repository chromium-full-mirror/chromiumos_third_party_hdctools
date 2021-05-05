# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Programmer for host side facing usb hub on v4p1 (genesys GL3590)."""

import os
import re

from servo_mfg import device_util
from servo_mfg import exec_util
from servo_mfg import programmer
from servo_mfg import util


class GenesysHubProgrammerError(programmer.ProgrammerError):
  """Genesys hub (GL3590) error class."""


class GenesysHubProgrammer(programmer.Programmer):
  """Class to program the genesys hub."""

  NAME = 'USB Hub (GL3590)'

  HUB_VID = 0x05e3
  HUB_PID = 0x0610

  PROGRAMMER_BIN = 'hubFwUpdaterCLI'

  # This is the file to program.
  FW_BIN = 'GL3590-OV7S1_Google_Servo_FW6414.bin'

  READ_CMD = [PROGRAMMER_BIN, 'version']

  WRITE_CMD = [PROGRAMMER_BIN, 'isp', '-t', 'single', '-n', '0', '-b']

  VERSION_REGEX = re.compile(r'version:(\d+)$')

  FW_VERSION = 6414

  def __init__(self, force):
    """Initialize the programmer.

    Args:
      force: whether to force programming if chip already appears programmed
    """
    programmer.Programmer.__init__(self, force=force)
    self._vid = self.HUB_VID
    self._pid = self.HUB_PID

  def _program(self, **_):
    """Helper to perform actual programming."""
    # This needs to run in the binfiles directory for the tool to work
    # properly.
    wd = os.getcwd()
    program_dir = util.get_bindir()
    os.chdir(program_dir)
    # At this stage, we have already validated that |FW_BIN| exists. So create
    # the full command.
    write_cmd = self.WRITE_CMD + [util.find_binfile(self.FW_BIN)]
    ret, _, _ = exec_util.exec_blocking(write_cmd, hint='writing')
    # Switch back to the regular wd.
    os.chdir(wd)
    if ret:
      self.throw_error('Issue on write. Giving up.')
    # After the hub is programmed, it needs to be unplugged, and then plugged
    # back in, we need to reenumerate the device.
    # on usb so that |_verify()| can read the new serial number.
    device_util.wait_for_usb_disconnect(self._vid, self._pid,
                                        message='Unplug and then replug the '
                                        'host cable to power cycle the servo')
    # Wait for the device to come back.
    device_util.wait_for_usb_device(vid=self._vid, pid=self._pid)

  def _verify(self, **_):
    """Helper to verify that programming succeeded."""
    # This needs to run in the binfiles directory for the tool to work
    # properly.
    wd = os.getcwd()
    program_dir = util.get_bindir()
    os.chdir(program_dir)
    # At this stage, we have already validated that |FW_BIN| exists. So create
    # the full command.
    ret, stdout, _ = exec_util.exec_blocking(self.READ_CMD, hint='reading')
    # Switch back to the regular wd.
    os.chdir(wd)
    if ret:
      self.throw_error('Issue on read. Giving up.')
    match = re.search(self.VERSION_REGEX, stdout.decode())
    return match and int(match.group(1)) == self.FW_VERSION

  def _verify_programming_env(self):
    """Helper to validate that programming tools are available."""
    # find the programming tool
    if not util.validate_exec_available(self.PROGRAMMER_BIN):
      self.exec_missing(self.PROGRAMMER_BIN)
    # find the template text file in binary
    if not util.find_binfile(self.FW_BIN):
      self.bin_file_missing(self.FW_BIN)
