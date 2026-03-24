# Copyright 2017 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for determining which type of servo is being used."""

import json
import logging
import os

from servo.common.utils import servo_logging
from servo.drv import hw_driver


class metadataError(hw_driver.HwDriverError):
    """Error class for metadata information."""


class servoMetadata(hw_driver.HwDriver):
    """Class to access loglevel controls."""

    def _drv_init(self):
        """Driver specific initializer."""
        super()._drv_init()

    def _Get_type(self):
        """Gets the type of the servo device setups.

        NOTE: please avoid assuming the format of servo type string and parsing it.
        Use 'devices' control to fetch all servo devices of this servod instance instead.
        """
        service = self._driver_client.GetVersion()
        return service.response

    def _Get_devices(self):
        """Gets detailed information about the devices set up for the servod instance."""
        return self._driver_client.GetDevices().response

    def _Get_pid(self):
        """Return servod instance pid"""
        return os.getpid()

    def _Get_serial(self):
        """Gets the serialname of the root device, if exists, or the main device."""
        return self._driver_client.GetSerial().get_value

    def _Get_serials(self):
        """Gets the all servo device's serialnames."""
        try:
            serials = json.loads(self._driver_client.GetSerials().get_value)
        except Exception as exc:
            self._logger.error(exc)
            serials = {}
        return json.dumps(serials, sort_keys=True, indent=4)

    def _Get_config_files(self):
        """Gets the configuration files used for this servo server invocation"""
        return self._driver_client.GetFileConfig().response

    def _Get_tagged_controls(self):
        """Retrieve all controls under a certain tag."""
        try:
            tagged_controls = self._driver_client.GetTaggedControls(
                name=json.dumps(self._params)
            )
            return json.loads(tagged_controls.response)
        except metadataError:
            raise metadataError("tag needs to be specified in params.")

    def _Set_rotate_logs(self, _unused):
        """Force a servo log rotation."""
        handlers = [
            h
            for h in logging.getLogger().handlers
            if isinstance(h, servo_logging.ServodRotatingFileHandler)
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
            if isinstance(h, servo_logging.ServodRotatingFileHandler):
                # Automatically converted to the 'yes/no' by servod.
                return 1
        return 0

    def _Set_log_msg(self, msg):
        """Log |msg| into info."""
        self._logger.info("%s", msg)

    def _Get_all_controls(self):
        """Return all controls supported by current servod instance."""
        # GetAllControls returns a flat list of strings e.g. "ccd_cr50.gsc_uart_pty"
        controls = json.loads(self._driver_client.GetAllControls().get_value)
        groups = {}
        for control in sorted(controls):
            if "." in control:
                prefix, name = control.split(".", 1)
            else:
                prefix, name = "main", control
            groups.setdefault(prefix, []).append(name)

        # Format out a nice string showing controls grouped by their prefix
        out = []
        for prefix, cmds in groups.items():
            if prefix == "main":
                out.append("\n=== Main Controls ===")
            else:
                out.append(f"\n=== {prefix} Controls ===")
            # Join up to 4 controls per line for readability
            for i in range(0, len(cmds), 4):
                out.append("  " + ", ".join(cmds[i : i + 4]))

        return "\n".join(out)
