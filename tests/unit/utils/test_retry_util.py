# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for retry_util."""

import unittest
from unittest.mock import MagicMock

from servo.utils.retry_util import retry_hardware
from servo.utils.retry_util import retry_on_none


class TestRetryUtil(unittest.TestCase):
    """Unit tests for retry_util."""

    def test_retry_hardware_success(self):
        """Test retry_hardware with success on first try."""
        mock_func = MagicMock(return_value="success")
        mock_func.__name__ = "mock_func"
        decorated = retry_hardware(max_tries=3)(mock_func)

        result = decorated()

        self.assertEqual(result, "success")
        self.assertEqual(mock_func.call_count, 1)

    def test_retry_hardware_retry_then_success(self):
        """Test retry_hardware with failure then success."""
        mock_func = MagicMock(side_effect=[OSError("fail"), "success"])
        mock_func.__name__ = "mock_func"
        decorated = retry_hardware(max_tries=3)(mock_func)

        result = decorated()

        self.assertEqual(result, "success")
        self.assertEqual(mock_func.call_count, 2)

    def test_retry_hardware_fail_max_tries(self):
        """Test retry_hardware failing after max tries."""
        mock_func = MagicMock(side_effect=OSError("fail"))
        mock_func.__name__ = "mock_func"
        decorated = retry_hardware(max_tries=3)(mock_func)

        with self.assertRaises(OSError):
            decorated()

        self.assertEqual(mock_func.call_count, 3)

    def test_retry_on_none_success(self):
        """Test retry_on_none with success on first try."""
        mock_func = MagicMock(return_value="success")
        mock_func.__name__ = "mock_func"
        decorated = retry_on_none(max_tries=3)(mock_func)

        result = decorated()

        self.assertEqual(result, "success")
        self.assertEqual(mock_func.call_count, 1)

    def test_retry_on_none_retry_then_success(self):
        """Test retry_on_none with None then success."""
        mock_func = MagicMock(side_effect=[None, "success"])
        mock_func.__name__ = "mock_func"
        decorated = retry_on_none(max_tries=3)(mock_func)

        result = decorated()

        self.assertEqual(result, "success")
        self.assertEqual(mock_func.call_count, 2)


if __name__ == "__main__":
    unittest.main()
