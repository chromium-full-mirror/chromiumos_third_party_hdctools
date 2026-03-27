# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for PollingControl."""

import logging
import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

import grpc

from servo.drv.hw_driver import HwDriverError
from servo.drv.polling_control import DEFAULT_POLLING_INTERVAL
from servo.drv.polling_control import DEFAULT_POLLING_TIMEOUT
from servo.drv.polling_control import PollingControl


class TestPollingControl(unittest.TestCase):
    def setUp(self):
        self.polling_control = PollingControl()
        self.hw_driver = MagicMock()
        self.logger = logging.getLogger(__name__)

    def test_found_expected_result_success(self):
        self.hw_driver._servod_get.return_value = "on"
        result = self.polling_control._found_expected_result(
            self.hw_driver, "power_state", ["on"], self.logger
        )
        self.assertTrue(result)
        self.hw_driver._servod_get.assert_called_once_with("power_state")

    def test_found_expected_result_failure(self):
        self.hw_driver._servod_get.return_value = "off"
        result = self.polling_control._found_expected_result(
            self.hw_driver, "power_state", ["on"], self.logger
        )
        self.assertFalse(result)

    def test_found_expected_result_hwdriver_error(self):
        self.hw_driver._servod_get.side_effect = HwDriverError("Mock error")
        result = self.polling_control._found_expected_result(
            self.hw_driver, "power_state", ["on"], self.logger
        )
        self.assertFalse(result)

    def test_found_expected_result_grpc_error(self):
        class MockRpcError(grpc.RpcError):
            pass

        self.hw_driver._servod_get.side_effect = MockRpcError("Mock gRPC error")
        result = self.polling_control._found_expected_result(
            self.hw_driver, "power_state", ["on"], self.logger
        )
        self.assertFalse(result)

    @patch("time.sleep")
    @patch("time.time")
    def test_poll_for_expected_result_immediate_success(self, mock_time, mock_sleep):
        mock_time.side_effect = [0, 0, 1]
        self.hw_driver._servod_get.return_value = "on"

        result = self.polling_control.poll_for_expected_result(
            self.hw_driver, "power_state", ["on"], timeout=1, poll_interval=0.1
        )

        self.assertTrue(result)
        mock_sleep.assert_not_called()

    @patch("time.sleep")
    @patch("time.time")
    def test_poll_for_expected_result_timeout(self, mock_time, mock_sleep):
        # time.time() is called to get timeout_time, and then in the loop.
        mock_time.side_effect = [0, 0, 1.1]
        self.hw_driver._servod_get.return_value = "off"

        result = self.polling_control.poll_for_expected_result(
            self.hw_driver, "power_state", ["on"], timeout=1, poll_interval=0.1
        )

        self.assertFalse(result)
        mock_sleep.assert_called_once_with(0.1)

    @patch("time.sleep")
    @patch("time.time")
    def test_poll_for_expected_result_success_after_retries(
        self, mock_time, mock_sleep
    ):
        mock_time.side_effect = [0, 0, 0.5, 1.0]
        self.hw_driver._servod_get.side_effect = ["off", "off", "on"]

        result = self.polling_control.poll_for_expected_result(
            self.hw_driver, "power_state", ["on"], timeout=2, poll_interval=0.1
        )

        self.assertTrue(result)
        self.assertEqual(mock_sleep.call_count, 2)
        self.assertEqual(self.hw_driver._servod_get.call_count, 3)

    def test_legacy_poll_method(self):
        with patch.object(
            self.polling_control, "poll_for_expected_result", return_value=True
        ) as mock_poll:
            result = self.polling_control.poll(
                self.hw_driver,
                "power_state",
                ["on"],
                polling_timeout=2.0,
                polling_interval=0.5,
                logger=self.logger,
            )
            self.assertTrue(result)
            mock_poll.assert_called_once_with(
                self.hw_driver,
                "power_state",
                ["on"],
                timeout=2.0,
                poll_interval=0.5,
                logger=self.logger,
            )


if __name__ == "__main__":
    unittest.main()
