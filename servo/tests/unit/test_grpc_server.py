# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import threading
import unittest
from unittest.mock import MagicMock

from servo.grpc_server.grpc_server_setup import run_grpc_server


class TestGrpcServer(unittest.TestCase):
    def test_run_grpc_server(self):
        # Create a mocked Servod instance
        mocked_servod = MagicMock()
        # Create a mocked ServoImpl instance
        # Use a thread to run the server in the background
        thread = threading.Thread(
            target=run_grpc_server, args=(mocked_servod,), daemon=True
        )
        thread.start()
        thread.join(timeout=1)  # Wait for 1 second
        thread.join(timeout=1)  # Wait for an additional 1 second
        self.assertTrue(thread.is_alive())
