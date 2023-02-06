# Copyright 2019 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for controlling the watchdog."""

import logging

from servo.drv import hw_driver
from servo import servo_dev_templates


class servoWatchdogError(hw_driver.HwDriverError):
  """Exception class for servo watchdog."""

class servoWatchdog(hw_driver.HwDriver):
  """Class to control the watchdog."""
  def __init__(self, interface, params, servod):
    """Initialize all information needed by servo watchdog."""
    super(servoWatchdog, self).__init__(interface, params, servod)

  def _update_device_disconnect_ok(self, name, disconnect_ok):
    """Update if it's ok for the device to disconnect.

    If it's not ok for the device to disconnect, the watchdog may kill servod.
    If you know you're going to disconnect a device, you should update let servo
    know.

    Args:
      name: String of the interface name or serial number.
      disconnect_ok: True if it's ok if the device can disconnect.

    Raises:
      servoWatchdogError: if the device isn't found.
    """
    serialnames = self._servod.get_servo_serials()
    devices = self._servod.get_devices()
    if name in devices:
      device = devices.get(name)
    # If the name isn't a device prefix, then it might be the serialname
    elif name in serialnames.values():
      for dev in devices:
        if name in dev.get_id():
          device = dev
          break
    # If the name isn't a device prefix or serialname, it could be
    # just the device type
    else:
      device = self._get_device_from_type(name)
      if device is None:
        raise servoWatchdogError('Invalid device %s' % name)

    device.set_disconnect_ok(disconnect_ok)

  def _get_device_state(self, device):
    """String of the current device state."""
    connected_str = '' if device.is_connected() else 'dis'
    disconnect_ok_str = ' (disconnect ok)' if device.disconnect_is_ok() else ''
    name = ', '.join(device.get_prefixes())
    return '%s: %sconnected%s' % (name, connected_str, disconnect_ok_str)

  def _Get_watchdog(self):
    """Get the connected state of all devices."""
    # add blank line at start, so formatting looks a bit better
    states = ['']
    for device in self._servod.get_devices():
      states.append(self._get_device_state(device))
    return '\n'.join(states)

  def _Set_watchdog_add(self, val):
    """Signal a device may not be disconnected."""
    self._update_device_disconnect_ok(val, False)

  def _Set_watchdog_remove(self, val):
    """Signal a device may be disconnected."""
    self._update_device_disconnect_ok(val, True)

  def _get_device_from_type(self, type):
    """Returns the device with the given type."""
    if type:
      # Check main device before checking other devices
      main_device = self._servod.get_main_device()
      if type in self._servod.get_main_device().template.TYPE:
        return main_device

      # If the name matches with multiple devices, error out.
      candidates = []
      for device in self._servod.get_devices():
        if type in device.template.TYPE:
          candidates.append(device)
      if len(candidates) == 1:
        return candidates[0]
      if len(candidates) > 1:
        raise servoWatchdogError('Multiple devices %s matching with type %s' % (candidates, type))
    return None

  def _Get_ccd_state(self):
    """Check the watchdog to see if ccd is enabled.

    Returns:
      0: ccd is off.
      1: ccd is on.
    """
    ccd_device = self._get_device_from_type('ccd')
    return int(ccd_device.is_connected()) if ccd_device else 0
