# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import threading
import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

from servo.core.grpc_server.grpc_server_setup import run_grpc_server


class TestGrpcServer(unittest.TestCase):
    @patch("servo.core.grpc_server.grpc_server_setup.grpc")
    @patch("servo.core.grpc_server.grpc_server_setup.servo_impl")
    def test_run_grpc_server(self, _mock_servo_impl, mock_grpc):
        # Create a mocked Servod instance
        mocked_servod = MagicMock()
        # Mock the server to avoid actual network operations
        mock_server = MagicMock()
        mock_grpc.server.return_value = mock_server

        # Make wait_for_termination block so the thread stays alive
        termination_event = threading.Event()
        mock_server.wait_for_termination.side_effect = termination_event.wait

        # Use a thread to run the server in the background
        # Pass a fake port 9999
        thread = threading.Thread(
            target=run_grpc_server, args=(mocked_servod, 9999), daemon=True
        )
        thread.start()
        thread.join(timeout=0.1)  # Wait briefly

        try:
            self.assertTrue(thread.is_alive())

            # Verify server was started
            mock_server.start.assert_called_once()
            # wait_for_termination is called and blocking
            mock_server.wait_for_termination.assert_called_once()
        finally:
            # Unblock the thread to let it finish
            termination_event.set()
            thread.join(timeout=1.0)
