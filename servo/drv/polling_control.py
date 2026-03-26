# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import time

import grpc

from servo.drv.hw_driver import HwDriverError


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
            res = hw_driver._servod_get(control)
            if res in expected_results:
                return True
        except HwDriverError as e:
            logger.debug(
                "PollingControl encountered HwDriverError "
                "while getting control %s: %s",
                control,
                str(e),
            )
        except grpc.RpcError as e:
            logger.debug(
                "PollingControl encountered gRPC error " "while getting control %s: %s",
                control,
                str(e),
            )
        return False

    def poll_for_expected_result(
        self,
        hw_driver,
        control,
        expected_results,
        timeout=DEFAULT_POLLING_TIMEOUT,
        poll_interval=DEFAULT_POLLING_INTERVAL,
        logger=None,
    ):
        """
        Polls a servod control until it reaches one of the expected results

        Args:
          hw_driver: a hwDriver object
          control: the control to poll
          expected_results: a list of the expected values for the control
          timeout: time in seconds to stop polling and return False.
                   A value of None means the polling will never time out
                   A value of 0 means the polling will only check the value once
          poll_interval: time in seconds to wait between polling
          logger: a logger object
        """
        import logging

        if logger is None:
            logger = logging.getLogger(__name__)

        logger.debug(
            "PollingControl waiting %ss for %s to reach %s",
            timeout,
            control,
            expected_results,
        )

        poll_indefinitely = False
        if timeout is None:
            poll_indefinitely = True
            timeout = 0

        timeout_time = time.time() + timeout
        while poll_indefinitely or time.time() <= timeout_time:
            if self._found_expected_result(
                hw_driver, control, expected_results, logger
            ):
                return True
            time.sleep(poll_interval)

        return False

    def poll(
        self,
        hw_driver,
        control,
        expected_results,
        polling_timeout=DEFAULT_POLLING_TIMEOUT,
        polling_interval=DEFAULT_POLLING_INTERVAL,
        logger=None,
    ):
        """Legacy backwards-compatible method."""
        return self.poll_for_expected_result(
            hw_driver,
            control,
            expected_results,
            timeout=polling_timeout,
            poll_interval=polling_interval,
            logger=logger,
        )
