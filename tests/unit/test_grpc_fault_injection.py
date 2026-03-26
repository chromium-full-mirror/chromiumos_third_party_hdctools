# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

import grpc

from servo.core.servo_server import Servod


class MockRpcError(grpc.RpcError):
    """Mock gRPC error for testing fault injection."""

    def code(self):
        return grpc.StatusCode.DEADLINE_EXCEEDED

    def details(self):
        return "Deadline Exceeded"


class TestGRPCFaultInjection(unittest.TestCase):
    def setUp(self):
        # Mock dependencies for Servod
        self.mock_logger = MagicMock()
        with patch(
            "servo.core.servo_server.logging.getLogger", return_value=self.mock_logger
        ):
            self.servod = Servod()

            # Setup a mock device
            self.mock_dev = MagicMock()
            self.servod._devices = {"main": self.mock_dev}
            self.servod._unique_devices = {"12345": self.mock_dev}

            # Mock get_dev_and_name
            self.servod._get_dev_and_name = MagicMock(
                return_value=(self.mock_dev, "power_state")
            )

    def test_get_grpc_timeout_handling(self):
        """Test that servod handles a gRPC deadline exceeded error during get()"""

        # The device's get() call over gRPC times out
        self.mock_dev.get.side_effect = MockRpcError("Timeout")

        # servod.get() should raise an Exception rather than crashing
        with self.assertRaises(Exception) as context:
            self.servod.get("power_state")

        # The exception should wrap the grpc error cleanly
        # servo_server.py does: `raise` for any exception
        # that doesn't start with GRPC_EXC_MSG
        # Ensure it catches and wraps it to bubble up without crashing.
        # XMLRPC handles Exceptions by returning a Fault.
        self.assertIsInstance(context.exception, grpc.RpcError)

    def test_set_grpc_timeout_handling(self):
        """Test that servod handles a gRPC deadline exceeded error during set()"""

        self.mock_dev.set.side_effect = MockRpcError("Timeout")

        with self.assertRaises(Exception) as context:
            self.servod.set("power_state", "off")

        self.assertIsInstance(context.exception, grpc.RpcError)


if __name__ == "__main__":
    unittest.main()
