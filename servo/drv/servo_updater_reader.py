# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver to query information from servo_updater."""

from servo.drv import hw_driver
from servo_updater import servo_updater


class servoUpdaterReaderError(hw_driver.HwDriverError):
    """Error class for his module."""

    pass


class servoUpdaterReader(hw_driver.HwDriver):
    """class to handle information retrieval from servo_updater"""

    REQUIRED_GET_PARAMS = ["board", "channel"]

    def _drv_init(self):
        """Driver specific initializer.

        Required params:
            board: the servo board name (*not* DUT board!)
            channel: the servo firmware channel in question
        """
        super()._drv_init()

        self._board = self._params["board"]
        self._channel = self._params["channel"]

    def _get(self):
        """Get available firmware version for |self._board| on |self._channel|.

        Returns:
            The version string
        """
        try:
            # Pass None for the |fname| argument to let the updater get the default
            # files for |self._board|.
            _unused, _unused, vers = servo_updater.get_files_and_version(
                self._board, None, self._channel
            )
            return vers
        except servo_updater.ServoUpdaterException as e:
            msg = "Failed to read latest available %r firmware for %r. %s" % (
                self._channel,
                self._board,
                e,
            )
            raise servoUpdaterReaderError(msg)
