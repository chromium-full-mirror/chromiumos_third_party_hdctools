# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# pylint: disable=unused-argument
# pylint: disable=unused-variable
import unittest
from unittest.mock import Mock
from unittest.mock import patch

from servo.utils.watchdog_util import get_device_from_type
from servo.utils.watchdog_util import WatchdogUtilError


class TestWatchdogUtil(unittest.TestCase):
    @patch("servo.tools.device.Device")  # Adjust the import path accordingly
    def test_get_device_from_type(self, mock_device_class):
        # Arrange
        servod_mock = Mock()
        device_type = "some_device_type"
        main_device_mock = Mock()
        other_device_mock = Mock()
        servod_mock.get_main_device.return_value = main_device_mock
        servod_mock.get_devices.return_value = [other_device_mock]

        main_device_mock.template.TYPE = ["main_device_type"]
        other_device_mock.template.TYPE = ["some_device_type"]

        # Act
        result = get_device_from_type(servod_mock, device_type)

        # Assert
        self.assertEqual(result, other_device_mock)
        servod_mock.get_main_device.assert_called()
        servod_mock.get_devices.assert_called()

    @patch("servo.tools.device.Device")  # Adjust the import path accordingly
    def test_get_device_from_type_multiple_candidates(self, mock_device_class):
        # Arrange
        servod_mock = Mock()
        device_type = "some_device_type"
        main_device_mock = Mock()
        other_device_mock1 = Mock()
        other_device_mock2 = Mock()
        servod_mock.get_main_device.return_value = main_device_mock
        servod_mock.get_devices.return_value = [other_device_mock1, other_device_mock2]

        main_device_mock.template.TYPE = ["main_device_type"]
        other_device_mock1.template.TYPE = ["some_device_type"]
        other_device_mock2.template.TYPE = ["some_device_type"]

        # Act and Assert
        with self.assertRaises(WatchdogUtilError) as context:
            get_device_from_type(servod_mock, device_type)


if __name__ == "__main__":
    unittest.main()
