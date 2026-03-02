# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Type-safe gRPC unit tests for ServoImpl."""

import unittest
from unittest.mock import MagicMock

import grpc
import grpc_testing

from servo.common.proto import servo_dev_pb2
from servo.core.grpc_server.impl.servo_impl import ServoImpl


class TestServoImplGrpc(unittest.TestCase):
    """Type-safe gRPC unit tests for ServoImpl."""

    def setUp(self):
        self._servod = MagicMock()
        self._servo_impl = ServoImpl(("localhost", 9999), self._servod)

        # Create a real gRPC server from the implementation
        self._test_server = grpc_testing.server_from_dictionary(
            {
                servo_dev_pb2.DESCRIPTOR.services_by_name[
                    "ServoService"
                ]: self._servo_impl
            },
            grpc_testing.strict_real_time(),
        )

    def test_get_servo_success(self):
        """Test GetServo with a valid request."""
        self._servod.get.return_value = "some_value"
        request = servo_dev_pb2.GetRequest(control_name="test_control")

        # Call the method via the test server's stub-like interface
        rpc = self._test_server.invoke_unary_unary(
            servo_dev_pb2.DESCRIPTOR.services_by_name["ServoService"].methods_by_name[
                "GetServo"
            ],
            {},
            request,
            None,
        )

        response, _metadata, code, _details = rpc.termination()

        self.assertEqual(code, grpc.StatusCode.OK)
        self.assertEqual(response.response, "some_value")
        self._servod.get.assert_called_once_with("test_control")

    def test_set_servo_success(self):
        """Test SetServo with a valid request."""
        request = servo_dev_pb2.SetServoRequest(control_name="test_control")
        request.value.string_value = "test_value"

        rpc = self._test_server.invoke_unary_unary(
            servo_dev_pb2.DESCRIPTOR.services_by_name["ServoService"].methods_by_name[
                "SetServo"
            ],
            {},
            request,
            None,
        )

        _response, _metadata, code, _details = rpc.termination()

        self.assertEqual(code, grpc.StatusCode.OK)
        self._servod.set.assert_called_once_with("test_control", "test_value")


if __name__ == "__main__":
    unittest.main()
