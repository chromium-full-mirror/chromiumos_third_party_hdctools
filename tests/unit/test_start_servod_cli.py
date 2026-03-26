# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys
import unittest
from unittest.mock import MagicMock
from unittest.mock import patch


# Append development_environment to path so start_servod can be imported
sys.path.append(
    os.path.join(os.path.dirname(__file__), "../../development_environment")
)
# pylint: disable=import-error,wrong-import-position
import start_servod


class TestStartServod(unittest.TestCase):
    def setUp(self):
        # Set up common patches
        self.mock_docker_env = patch("start_servod.docker.from_env").start()
        self.mock_exists = patch(
            "start_servod.os.path.exists", return_value=True
        ).start()
        self.mock_needs_update = patch(
            "start_servod.needs_update_check", return_value=False
        ).start()
        self.mock_get_image = patch(
            "start_servod.get_image", return_value="servod:dev"
        ).start()
        self.mock_makedirs = patch("start_servod.os.makedirs").start()
        self.mock_exit = patch("sys.exit").start()
        self.mock_thread = patch("start_servod.threading.Thread").start()

        # Mock docker client and container
        self.mock_client = MagicMock()
        self.mock_docker_env.return_value = self.mock_client
        self.mock_container = MagicMock(status="created")
        self.mock_container.exec_run.return_value = (0, b"")
        self.mock_client.containers.run.return_value = self.mock_container

    def tearDown(self):
        patch.stopall()

    def test_dump_xml_argument_passthrough(self):
        test_args = [
            "start-servod",
            "--dump-xml",
            "/tmp/host_file.xml",
            "-b",
            "brask",
            "--",
            "--usbkm232",
            "/dev/ttyUSB0",
        ]
        with patch.object(sys, "argv", test_args):
            args = start_servod.parse_args()

            # Verify argparse captured it correctly
            self.assertEqual(args.dump_xml, "/tmp/host_file.xml")
            self.assertIn("--usbkm232", args.passthrough)

            # Run the main logic
            start_servod.main()

            # Assert docker container run was called with correct volumes and command
            self.mock_client.containers.run.assert_called_once()
            call_kwargs = self.mock_client.containers.run.call_args[1]

            # Check volumes
            volumes = call_kwargs.get("volumes", [])
            self.assertTrue(
                any("/tmp/dump_xml/" in v for v in volumes),
                "dump_xml volume should be mounted",
            )

            # Check command
            command = " ".join(call_kwargs.get("command", []))
            self.assertIn("--dump-xml /tmp/dump_xml/host_file.xml", command)
            self.assertNotIn("-- --usbkm232", command)  # "--" should be stripped
            self.assertIn("--usbkm232 /dev/ttyUSB0", command)

    def test_noboard_argument_passthrough(self):
        test_args = ["start-servod", "--noboard"]
        with patch.object(sys, "argv", test_args):
            args = start_servod.parse_args()
            self.assertTrue(args.noboard)

            start_servod.main()

            self.mock_client.containers.run.assert_called_once()
            call_kwargs = self.mock_client.containers.run.call_args[1]
            command = " ".join(call_kwargs.get("command", []))
            self.assertIn("--noboard", command)

    def test_logs_dir_mounting(self):
        test_args = ["start-servod", "--logs", "/my/custom/logs/dir"]
        with patch.object(sys, "argv", test_args):
            start_servod.main()

            self.mock_client.containers.run.assert_called_once()
            call_kwargs = self.mock_client.containers.run.call_args[1]
            volumes = call_kwargs.get("volumes", [])

            # The host logs dir should be mounted to
            # /var/log/servod_9999 inside container
            self.assertTrue(
                any(
                    v.startswith("/my/custom/logs/dir") and "/var/log/servod_9999" in v
                    for v in volumes
                ),
                f"Expected logs directory in volumes: {volumes}",
            )


if __name__ == "__main__":
    unittest.main()
