# Copyright 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for determining which type of servo is being used."""

import json
import logging
import os

from servo.drv import hw_driver
import servo.servo_logging


class metadataError(hw_driver.HwDriverError):
  """Error class for metadata information."""


class servoMetadata(hw_driver.HwDriver):
  """Class to access loglevel controls."""

  def __init__(self, interface, params, servod):
    """Initializes the ServoType driver.

    Args:
      interface: hardware interface for low-level communication; ignored here
      params: A dictionary of parameters, but is ignored.
      servod: Servod that is used for cross-servo-device communication
    """
    super(servoMetadata, self).__init__(interface, params, servod)

  def _Get_type(self):
    """Gets the type of the servo device setups."""
    main_device = self._servod.get_main_device()
    root_device = self._servod.get_root_device()
    type = main_device.template.TYPE
    if root_device:
      type = root_device.template.TYPE + '_with_' + type
      for dev in root_device.get_child_devices():
        if dev.template.DUT_CONTROLLER and dev != main_device:
          type += '_and_' + dev.template.TYPE
    return type

  def _Get_devices(self):
    """Gets detailed information about the devices set up for the servod instance."""
    devices_json = []
    for device in self._servod.get_devices():
      devices_json.append(json.loads(device.to_json()))
    return json.dumps(devices_json, indent=4)

  def _Get_pid(self):
    """Return servod instance pid"""
    return os.getpid()

  def _Get_serial(self):
    """Gets the current servo serial."""
    return json.dumps(self._servod.get_serials(), sort_keys=True, indent=4)

  def _Get_config_files(self):
    """Gets the configuration files used for this servo server invocation"""
    return json.dumps(self._servod.get_config_files(), sort_keys=True, indent=4)

  def _Get_tagged_controls(self):
    """Retrieve all controls under a certain tag."""
    if 'tag' not in self._params:
      raise metadataError('tag needs to be specified in params.')
    return self._servod.get_controls_for_tag(self._params['tag'])

  def _Set_rotate_logs(self, _):
    """Force a servo log rotation."""
    handlers = [h for h in logging.getLogger().handlers if
                isinstance(h, servo.servo_logging.ServodRotatingFileHandler)]
    self._logger.info('Rotating out the log file per user request.')
    if not handlers:
      self._logger.warning('No ServodRotatingFileHandlers on this instance. noop.')
    for h in handlers:
      h.doRollover()

  def _Get_servod_logs_active(self):
    """Return whether servod file logging is turned on."""
    for h in logging.getLogger().handlers:
      if isinstance(h, servo.servo_logging.ServodRotatingFileHandler):
    # Automatically converted to the 'yes/no' by servod.
        return 1
    return 0

  def _Set_log_msg(self, msg):
    """Log |msg| into info."""
    self._logger.info('%s', msg)
