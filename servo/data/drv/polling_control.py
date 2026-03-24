# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import time

import grpc

from servo.data.drv.hw_driver import HwDriverError


DEFAULT_POLLING_INTERVAL = 0.0
DEFAULT_POLLING_TIMEOUT = None  # meaning no timeout


class PollingControl:
    """Object to poll a control on a servo until it reaches an expected result"""

    def _found_expected_result(self, hw_driver, control, expected_results, logger):
        """
        Get a control from a servod and compare it to the expected results

        Args:
          hw_driver: a hwDriver object
          control: the control to get
          expected_results: a list of the expected values for the control
        """
        try:
            value = hw_driver._servod_get(control)
        except (HwDriverError, grpc.RpcError) as hw_error:
            # If a HwDriverError or RpcError is raised during the get command, just continue
            # polling until the timeout.
            # It can be expected as when polling for `ec_system_powerstate` and the
            # ec is temporarily not accessible.
            if logger is not None:
                logger.debug(
                    "Error raised while trying to get control '%s': %s"
                    % (control, hw_error)
                )
            return False
        return value in expected_results

    def _start_polling_timer(self):
        """Get the start time of polling to be able to know when to timeout"""
        self.start_polling_time = time.time()

    def _get_polling_timer(self):
        """Return the time since the beginning of the polling"""
        return time.time() - self.start_polling_time

    def _polling_timeout(self, polling_timeout):
        """Return whether or not we have timeout while polling"""
        return (
            self._get_polling_timer() > polling_timeout
            if polling_timeout is not None
            else False
        )

    def poll(
        self,
        hw_driver,
        control,
        expected_results,
        logger=None,
        polling_interval=DEFAULT_POLLING_INTERVAL,
        polling_timeout=DEFAULT_POLLING_TIMEOUT,
    ):
        """
        Poll a control until either the control is at the expected values or it timeouts

        Args:
          control: the control to get
          expected_results: a list of the expected outputs for the control
          logger: an object to log errors when trying to get the control
          polling_interval: the time to wait between 2 polling (default: 0s)
          polling_timeout: the time after which to timeout (default: do not timeout)

        Returns:
          True when the expected result is found
          False when timeout
        """
        self._start_polling_timer()
        while True:
            if self._found_expected_result(hw_driver, control, expected_results, logger):
                return True
            if self._polling_timeout(polling_timeout):
                return False
            time.sleep(polling_interval)
