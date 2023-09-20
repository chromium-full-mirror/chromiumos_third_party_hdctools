# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Unit-tests to ensure that servodtool tool works as intended."""

import argparse
import unittest
import unittest.mock

from servo.tools import tool


class TestTool(unittest.TestCase):
    """Test tool.py."""

    def test_error(self):
        """Test error()."""
        t = tool.Tool()
        t._logger.info = unittest.mock.MagicMock()

        with self.assertRaises(SystemExit) as cm:
            t.error("message %s", "msg")

        self.assertEqual(cm.exception.code, 1)
        t._logger.info.assert_called_once_with("message %s", "msg")

    def test_run(self):
        """Test run()."""
        t = tool.Tool()
        t.error = unittest.mock.MagicMock()
        t.add_args = unittest.mock.MagicMock()
        args = argparse.Namespace()
        args.command = "add-args"

        t.run(args)

        t.add_args.assert_called_once_with(args)
        t.error.assert_not_called()

    def test_run_failure(self):
        """Test run()."""
        t = tool.Tool()
        t.error = unittest.mock.MagicMock(side_effect=SystemExit(1))
        args = argparse.Namespace()
        args.command = "testing-testing"

        with self.assertRaises(SystemExit) as cm:
            t.run(args)

        self.assertEqual(cm.exception.code, 1)
        t.error.assert_called_once_with(
            "Tool does not recognize command %r. It should be implemented "
            "as a method called %r.",
            "testing-testing",
            "testing_testing",
        )


if __name__ == "__main__":
    unittest.main()
