# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Programmer to write serial number to the servo EC."""

import time

import servo.utils.usb_hierarchy as usb_hierarchy
from servo_mfg import device_util
from servo_mfg import programmer


class SerialProgrammerError(programmer.ProgrammerError):
  """SerialProgrammer error class."""


class SerialProgrammer(programmer.Programmer):
  """Write a serialname to the servo EC."""

  NAME = 'Servo Serialname'

  # The command and regex needed to write and validate that the right
  # serial was written to the EC.
  SERIAL_CMD_STUB = r'serialno set %s'
  SERIAL_RE = r'Serial number: ([^\r\n]+)[\n\r]+'

  def __init__(self, force, servo_vid, servo_pid,
               parent_hub_vid=None, parent_hub_pid=None):
    """Initialize the logger.

    Args:
      force: whether to force programming if chip already appears programmed
      servo_vid: vid for the servo device (after flashing)
      servo_pid: pid for the servo device (after flashing)
      parent_hub_vid: vid for the hub the dongle is hanging on
      parent_hub_pid: pid for the hub the dongle is hanging on

    """
    programmer.Programmer.__init__(self, force=force)
    self._parent_hub_vid = parent_hub_vid
    self._parent_hub_pid = parent_hub_pid
    self._vid = servo_vid
    self._pid = servo_pid

  def _get_current_serial(self):
    """Retrieve the current serialname from sysfs.

    Returns:
      serial name of the |self._vid|:|self._pid| device in sysfs
    """
    return usb_hierarchy.Hierarchy.SerialFromSysfs(self._find())

  def _program(self, serial, tiny_servod, **_):
    """Program by connecting to servo console and writing the |serial|."""
    serial_cmd = self.SERIAL_CMD_STUB % serial
    self.info('Writing serial to be %r', serial)
    # pylint: disable=protected-access
    # private function access pattern required by API
    results = tiny_servod.pty._issue_cmd_get_results(serial_cmd,
                                                     [self.SERIAL_RE])
    sn = results[0][1].strip().strip('\n\r')
    if sn != serial:
      raise SerialProgrammerError('Firmware failed to set serial to %r '
                                  'instead got %r' % (serial, sn))
    try:
      # After the serialname is written, we need to reenumerate the device
      # on usb so that |_verify()| can read the new serial number.
      usb_hierarchy.Hierarchy.ResetDeviceSysfs(self._find())
    except usb_hierarchy.HierarchyError as e:
      self.debug(e)
      # The device sometimes drops off even before issuing the reset. Skip
      # for now, if it's a real issue _verify() will fails.
      # TODO(coconutruben): figure out why the device sometimes drops off
      # even before we issue the reset.
    # Wait for the device to come back.
    device_util.wait_for_usb_device(vid=self._vid, pid=self._pid)
    # The device was just reset. The usb and uart threads need to be
    # reinitialized.
    time.sleep(2)
    tiny_servod.reinitialize()

  def _verify(self, serial, **_):
    """Check whether the serial stored in sysfs is the same as |serial|.

    Args:
      serial: serial number to check

    Returns:
      True if the serial shown in sysfs matches |serial|, False otherwise
    """
    current_serial = self._get_current_serial()
    if current_serial == serial:
      self.debug('Serial is already %r', serial)
      return True
    self.debug('Serial is %r, not %r.', current_serial, serial)
    return False

  def _verify_programming_env(self):
    """No special tools needed for serial programming - just skip."""
    pass
