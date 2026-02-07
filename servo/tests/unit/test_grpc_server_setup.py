# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import unittest
from unittest.mock import patch

from servo.core.grpc_server.grpc_server_setup import run_grpc_server


class TestRunGRPCServer(unittest.TestCase):
    @patch("servo.core.grpc_server.impl.servo_impl.ServoImpl")
    @patch("servo.common.proto.servo_dev_grpc.add_ServoServiceServicer_to_server")
    @patch("grpc.server")
    def test_run_grpc_server(
        self, mock_grpc_server, mock_add_servo_service, mock_servo_impl
    ):
        servod_mock = "mock_servod_instance"
        mock_servo_instance = mock_servo_impl.return_value
        mock_grpc_server_instance = mock_grpc_server.return_value

        run_grpc_server(servod_mock, 50052)

        mock_grpc_server.assert_called_once()
        args = mock_grpc_server.call_args
        self.assertEqual(args[0][0]._max_workers, 10)

        mock_add_servo_service.assert_called_once_with(
            mock_servo_instance, mock_grpc_server_instance
        )
        mock_grpc_server_instance.add_insecure_port.assert_called_once_with(
            "[::]:50052"
        )
        mock_grpc_server_instance.start.assert_called_once_with()
        mock_grpc_server_instance.wait_for_termination.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
