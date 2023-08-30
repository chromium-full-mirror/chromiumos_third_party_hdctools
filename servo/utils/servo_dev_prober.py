# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Probe servo device attached DUT's EC for information."""

import logging


class DeviceProber(object):
    """Class to probe servo attached DUT's EC for information."""

    RETRY_ATTEMPTS = 3

    def __init__(self):
        """Setup instance by creating a logger."""
        self._logger = logging.getLogger(type(self).__name__)

    def get_board_from_ec(self, dev):
        """Attempt to get ec_board output from |dev|.

        Args:
          dev: ServoDevice instance (ideally with an initialized EC console interface).

        Returns:
          output of dev.get('ec_board') or None after |RETRY_ATTEMPTS| failures.
        """
        return self._get_info_from_ec(dev=dev, cmd="ec_board")

    def get_model_from_ec(self, dev):
        """Attempt to get ec_model output from |dev|.

        Args:
          dev: ServoDevice instance (ideally with an initialized EC console interface).

        Returns:
          output of dev.get('ec_model') or None after |RETRY_ATTEMPTS| failures.
        """
        return self._get_info_from_ec(dev=dev, cmd="ec_model")

    def _get_info_from_ec(self, dev, cmd, attempts=None):
        """Try to get |cmd| from |dev| |attempts| times before giving up.

        Args:
          dev: ServoDevice instance (ideally with an initialized EC console interface).
          cmd: servod control to get from |dev|
          attempts: number of attempts of getting the info before erroring out

        Returns:
          output of dev.get(cmd) or None after |attempts| failures.
        """
        if attempts is None:
            attempts = self.RETRY_ATTEMPTS
        for i in range(attempts, 0, -1):
            try:
                result = dev.get(cmd)
                self._logger.info("Retrieved %r as %r for %s.", cmd, result, dev)
                return result
            except Exception:
                self._logger.warning(
                    "Failed to retrieve %r from %s. Attempting %d more times.",
                    cmd,
                    dev,
                    i - 1,
                )
        return None
