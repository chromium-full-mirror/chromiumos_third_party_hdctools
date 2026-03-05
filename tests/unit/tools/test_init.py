# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Test tools package is initiated properly."""

import unittest

from servo import tools
from servo.tools import device
from servo.tools import instance
from servo.tools import logs


class TestDutControl(unittest.TestCase):
    """Test __init__.py."""

    def test_init(self):
        """Test tools package is initiated properly."""
        self.assertTrue(device.Device in tools.REGISTERED_TOOLS)
        self.assertTrue(instance.Instance in tools.REGISTERED_TOOLS)
        self.assertTrue(logs.Logs in tools.REGISTERED_TOOLS)


if __name__ == "__main__":
    unittest.main()
