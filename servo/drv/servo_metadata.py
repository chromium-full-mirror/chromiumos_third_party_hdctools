# Copyright 2017 The ChromiumOS Authors
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

    def _Get_type(self):
        """Gets the type of the servo device setups.

        NOTE: please avoid assuming the format of servo type string and parsing it.
        Use 'devices' control to fetch all servo devices of this servod instance instead.
        """
        return self._servod._get_version()

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
        """Gets the serialname of the root device, if exists, or the main device."""
        root_dev = self._servod.get_root_device()
        if root_dev is not None:
            return root_dev._serial
        return self._servod.get_main_device()._serial

    def _Get_serials(self):
        """Gets the all servo device's serialnames."""
        return json.dumps(self._servod.get_servo_serials(), sort_keys=True, indent=4)

    def _Get_config_files(self):
        """Gets the configuration files used for this servo server invocation"""
        return json.dumps(self._servod.get_config_files(), sort_keys=True, indent=4)

    def _Get_tagged_controls(self):
        """Retrieve all controls under a certain tag."""
        if "tag" not in self._params:
            raise metadataError("tag needs to be specified in params.")
        return self._servod.get_controls_for_tag(self._params["tag"])

    def _Set_rotate_logs(self, _unused):
        """Force a servo log rotation."""
        handlers = [
            h
            for h in logging.getLogger().handlers
            if isinstance(h, servo.servo_logging.ServodRotatingFileHandler)
        ]
        self._logger.info("Rotating out the log file per user request.")
        if not handlers:
            self._logger.warning(
                "No ServodRotatingFileHandlers on this instance. noop."
            )
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
        self._logger.info("%s", msg)

    def _Get_all_controls(self):
        """Return all controls supported by current servod instance."""
        return self._servod._controls
