# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for the hardware driver base class."""

import unittest
import unittest.mock

from servo.drv import hw_driver


class TestHwDriver(unittest.TestCase):
    """Tests for the HwDriver base class."""

    def test_prefix_assignment(self):
        """Test that interface_prefix is assigned to self._prefix."""
        # Setup mock params with an explicit interface prefix
        mock_params = {"interface_prefix": "ccd_gsc", "cmd": "get"}

        # Initialize the hw_driver
        drv = hw_driver.HwDriver(None, None, "mock_interface", mock_params)

        self.assertEqual(drv._prefix, "ccd_gsc")

    def test_no_prefix_assignment(self):
        """Test fallback when no prefix is provided."""
        mock_params = {"cmd": "get"}

        drv = hw_driver.HwDriver(None, None, "mock_interface", mock_params)

        self.assertIsNone(drv._prefix)
