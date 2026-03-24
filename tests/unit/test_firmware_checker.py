# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Test the firmware version check works as intended."""

import unittest
import unittest.mock

from packaging import version

from servo.drv.servo_firmware_checker import servoFirmwareChecker


class TestServoFirmwareChecker(unittest.TestCase):
    """Test ServoFirmwareChecker."""

    def setUp(self):
        """Set up for each unit test."""
        unittest.TestCase.setUp(self)
        self.patcher_grpc_client = unittest.mock.patch("servo.drv.hw_driver.GrpcClient")
        self.patcher_servo_dev_grpc = unittest.mock.patch(
            "servo.drv.hw_driver.servo_dev_grpc"
        )
        self.patcher_grpc_client.start()
        self.patcher_servo_dev_grpc.start()

        self.checker = servoFirmwareChecker(
            ("localhost", 1234),
            ("localhost", 1235),
            interface=None,
            params={"board": "servo_v4p1", "cmd": "set"},
        )
        self.device = "servo_v4p1"
        self.version = "2.0.20646"
        self.fullversion = f"v{self.version}-1fb66a343"
        self.full_devstring = f"{self.device}_{self.fullversion}"

    def tearDown(self):
        """Tear down for each unit test."""
        self.patcher_grpc_client.stop()
        self.patcher_servo_dev_grpc.stop()
        unittest.TestCase.tearDown(self)

    def test_fetch_versions(self):
        """Test that _fetch_versions returns a reasonably formed version report."""
        self.checker._servod_get = unittest.mock.MagicMock(
            return_value=self.full_devstring
        )
        current, latest = self.checker._fetch_versions()
        self.assertEqual(current, latest)
        self.assertEqual(current, version.parse(self.version))

    def test_comparison(self):
        """Test that _get returns the right results for comparisons"""
        self.checker._servod_get = unittest.mock.MagicMock(
            return_value=self.full_devstring
        )
        self.assertEqual(self.checker._get(), 1)
        x = 1

        def string_incrementer(_unused: str) -> str:
            nonlocal x
            x = x + 1
            return f"string_incrementer_v{x}.0.0-1234"

        self.checker._servod_get = unittest.mock.MagicMock(
            side_effect=string_incrementer
        )
        self.assertEqual(self.checker._get(), 0)


if __name__ == "__main__":
    unittest.main()
