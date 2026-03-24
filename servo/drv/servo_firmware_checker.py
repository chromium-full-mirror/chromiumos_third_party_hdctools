# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver to check whether the firmware is up to date."""

from __future__ import annotations

import os
import re

from packaging import version

from servo.common import sversion_util
from servo.drv import hw_driver
from servo_updater import servo_updater


# In some environments, like automated testing, it is likely by design if a
# channel that is not the stable channel is being run. If the user sets this
# environment variable, a warning will only print if the channel is unknown

WARN_ONLY_ON_UNKNOWN_ENV = "SERVO_FW_ALL_CHANNEL_OK"


class servoFirmwareCheckerError(hw_driver.HwDriverError):
    """Error class for his module."""

    pass


class servoFirmwareChecker(hw_driver.HwDriver):
    """class to handle checking and reporting on errors."""

    REQUIRED_GET_PARAMS = ["board"]
    REQUIRED_SET_PARAMS = REQUIRED_GET_PARAMS

    def _drv_init(self):
        """Driver specific initializer.

        Required params:
            board: the servo board name (*not* DUT board!)
        """
        super()._drv_init()

        # Set can be used by passing 'print' as an argument.
        self._choices = re.compile("^0$")
        self._board = self._params["board"]

        self._current_fw_cmd = "%s_version" % (self._board,)
        self._latest_fw_cmd = "%s_latest_version" % (self._board,)
        self._fw_channel_cmd = "%s_firmware_channel" % (self._board,)
        self._always_warn = WARN_ONLY_ON_UNKNOWN_ENV not in os.environ

    def _separate_dev_ver(self, firmware_version_string: str) -> str:
        return firmware_version_string.split("_")[-1].split("-")[0]

    def _fetch_versions(self) -> tuple[version.Version, version.Version]:
        current_raw = self._servod_get(self._current_fw_cmd)
        current_ver = sversion_util.normalize_version(current_raw)
        current = version.parse(current_ver)

        latest_raw = self._servod_get(self._latest_fw_cmd)
        latest_ver = sversion_util.normalize_version(latest_raw)
        latest = version.parse(latest_ver)

        return current, latest

    def _get(self) -> int:
        """Get available firmware version for |self._board| on |self._channel|.

        Returns:
            1 if |{self._board}_version| == |{self._board}_latest_version|
            0 otherwise
        """
        current, latest = self._fetch_versions()
        return int(latest == current)

    def _set(self, _unused):
        """Print what the current firmware is, what the latest available is."""
        current, latest = self._fetch_versions()
        if latest == current:
            self._logger.info("%s firmware up to date.", self._board)
        else:
            channel = self._servod_get(self._fw_channel_cmd)
            # Let the user know what channel they are currently running
            self._logger.info("current %r firmware: %s", self._board, current)
            self._logger.info("current firmware is from channel %r", channel)
            if channel == "unknown" or self._always_warn:
                # Send a more explicit warning and let the user know how to upgrade
                self._logger.info("latest %r firmware: %s", self._board, latest)
                # Check if the device's version is newer than the latest, and
                # demote warning to info in that case.
                if current > latest:
                    # Tell user that they're not using an official version
                    self._logger.info(
                        "The device runs a newer firmware version "
                        "than what is officially supported. Use "
                        "servo_updater if this is not desired."
                    )
                else:
                    # Warn the user to upgrade if needed.
                    self._logger.warning("======Warning======")
                    self._logger.warning("Not running latest stable firmware.")
                    self._logger.warning(
                        "Please run %r if desired to rectify.",
                        "sudo servo_updater --board %s" % self._board,
                    )
                    self._logger.warning("======Warning======")
