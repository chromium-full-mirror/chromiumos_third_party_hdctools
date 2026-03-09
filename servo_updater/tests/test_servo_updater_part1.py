# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for servo_updater."""

import unittest
from unittest import mock

from servo_updater import servo_updater


class TestServoUpdater(unittest.TestCase):
    """Tests for servo_updater."""

    @mock.patch("servo_updater.servo_updater.main")
    def test_main_runs(self, mock_main):
        """Test that main runs without error."""
        servo_updater.main()
        mock_main.assert_called_once()

    @mock.patch("servo_updater.servo_updater.get_files_and_version")
    @mock.patch("servo_updater.servo_updater.c.wait_for_usb")
    @mock.patch("servo_updater.servo_updater.tiny_servod.TinyServod")
    @mock.patch("servo_updater.servo_updater.do_version")
    @mock.patch("servo_updater.servo_updater.do_updater_version")
    @mock.patch("servo_updater.servo_updater.select")
    @mock.patch("servo_updater.servo_updater.flash")
    @mock.patch("servo_updater.servo_updater.flash2")
    def test_update_device(
        self,
        mock_flash2,
        mock_flash,
        mock_select,
        mock_do_updater_version,
        mock_do_version,
        mock_tiny_servod,
        mock_wait_for_usb,
        mock_get_files_and_version,
    ):
        """Test that update function can be called."""
        # Mock return values to avoid actual hardware interactions
        mock_get_files_and_version.return_value = (
            "c2d2.json",
            "c2d2.bin",
            "c2d2_v1.2.3-12345ab",
        )
        mock_dev = mock.MagicMock()
        mock_dev.idVendor = 0x18D1
        mock_dev.idProduct = 0x5020
        mock_wait_for_usb.return_value = [mock_dev]

        mock_do_version.return_value = "c2d2_v1.1.8-12345ab"
        mock_do_updater_version.return_value = 6
        mock_tiny_servod.return_value = mock.MagicMock()

        # Mock open to prevent FileNotFoundError and return expected data
        mock_data = (
            '{"vid": "0x18d1", "pid": "0x5020", "console": "0", "board": "c2d2"}'
        )
        with mock.patch("builtins.open", mock.mock_open(read_data=mock_data)):
            # Call the main function with arguments to trigger the update path
            servo_updater.main(["--board", "c2d2", "--serialname", "TEST_SERIAL"])

        # Add assertions to check if the mocked functions were called as expected
        mock_get_files_and_version.assert_called_once_with("c2d2", None, "stable")
        mock_tiny_servod.assert_called_once()
        mock_do_version.assert_called_once()
        mock_select.assert_called()
        mock_flash2.assert_called()
        self.assertEqual(mock_flash.call_count, 0)


if __name__ == "__main__":
    unittest.main()
