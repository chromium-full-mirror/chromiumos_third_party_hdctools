#!/usr/bin/env python3
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import unittest

from servo.common.interface.empty import Empty


class TestEmptyInterface(unittest.TestCase):
    def test_build_method(self):
        # Test the build method of the Empty class
        instance = Empty.build()
        self.assertIsInstance(instance, Empty)

    def test_name_method(self):
        # Test the name method of the Empty class
        name = Empty.name()
        self.assertEqual(name, "empty")


if __name__ == "__main__":
    unittest.main()
