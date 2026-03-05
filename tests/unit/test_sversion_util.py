# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest


# We need to mock servo.sversion before importing sversion_util if we want to
# test the try-except block.
# But here we just want to verify it works when sversion is present.


class TestSversionUtil(unittest.TestCase):
    def test_import_sversion(self):
        """Test that sversion_util can import sversion and use it."""
        # pylint: disable=import-outside-toplevel
        from servo.common import sversion_util

        # If the fix works, sversion_util.vdict should not be the fallback
        # 'unknown' dict provided that we ran 'make ver' and
        # servo/sversion.py exists.
        self.assertNotEqual(sversion_util.vdict["vbase"], "unknown")

    def test_extended_version(self):
        """Test that extended_version returns a string with actual data."""
        # pylint: disable=import-outside-toplevel
        from servo.common import sversion_util

        version_str = sversion_util.extended_version()
        self.assertIn("Date:", version_str)
        self.assertIn("Builder:", version_str)
        self.assertNotIn("unknownunknown", version_str)


if __name__ == "__main__":
    unittest.main()
