# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Unit-tests to ensure that servodtool works as intended."""

import argparse
import unittest
import unittest.mock

from servo.core import servodtool
from servo.tools import instance


class TestServodTool(unittest.TestCase):
    """Test servodtool.py."""

    @unittest.mock.patch(
        "servo.tools.instance.Instance.add_args", unittest.mock.MagicMock()
    )
    @unittest.mock.patch("servo.tools.instance.Instance.run", unittest.mock.MagicMock())
    @unittest.mock.patch(
        "argparse.ArgumentParser.parse_args",
        unittest.mock.MagicMock(return_value=argparse.Namespace()),
    )
    def test_servodutil(self):
        """Test servodutil()."""
        servodtool.servodutil(cmdline=["something"])
        instance.Instance.add_args.assert_called_once()
        instance.Instance.run.assert_called_once()

    @unittest.mock.patch("servo.tools.instance.Instance.run", unittest.mock.MagicMock())
    def test_main(self):
        """Test main()."""
        args = argparse.Namespace()
        args.debug = False
        args.tool = "instance"
        with unittest.mock.patch(
            "argparse.ArgumentParser.parse_args",
            unittest.mock.MagicMock(return_value=args),
        ):
            servodtool.servodutil(cmdline=["something"])
        instance.Instance.run.assert_called_once_with(args)


if __name__ == "__main__":
    unittest.main()
