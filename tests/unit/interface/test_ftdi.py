# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Test for ftdi_utils package."""

import unittest

from servo.common.interface import ftdi_utils


class TestFTDILoadLibs(unittest.TestCase):
    """
    Unit test class for ftdi_utils.load_libs()
    """

    def test_known_ftdi_libs(self):
        """Verify required libraries have been install and and can be loaded."""
        valid_libs = ["ftdi", "ftdii2c", "ftdigpio", "ftdiuart"]
        ftdi_utils.load_libs(*valid_libs)
        self.assertEqual(len(valid_libs), len(valid_libs))

    def test_invalid_ftdi_libs(self):
        """Verify invalid libraries are detected and raise exit."""
        with self.assertRaisesRegex(SystemExit, "1"):
            ftdi_utils.load_libs("ftdi", "invalid_ftdi", "ftdii2c")
