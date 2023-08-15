# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Unit-tests to ensure that servodtool logs works as intended."""

import argparse
import os
import shutil
import tarfile
import tempfile
import unittest
import unittest.mock

from servo.tools import logs


class TestLogs(unittest.TestCase):
    """Test logs.py."""

    def test_help(self):
        """Test help()."""
        self.assertEqual(logs.Logs().help, "Process servod logs.")

    @unittest.mock.patch(
        "servo.tools.logs._cleanup_output_dir", unittest.mock.MagicMock()
    )
    @unittest.mock.patch("servo.tools.logs._make_tarfile", unittest.mock.MagicMock())
    @unittest.mock.patch("os.path.exists", unittest.mock.MagicMock())
    def test_extract(self):
        """Test extract()."""
        args = argparse.Namespace()
        args.port = [9999]
        args.previous = True
        l = logs.Logs()
        l._extract_one_dir = unittest.mock.MagicMock(
            return_value=["/var/log/servod_9999"]
        )

        l.extract(args)

        logs._cleanup_output_dir.assert_called_once()
        l._extract_one_dir.assert_called_once_with("/var/log/servod_9999", True)
        logs._make_tarfile.assert_called_once_with(
            logs.OUTPUT_TAR, ["/var/log/servod_9999"]
        )

    def test_extract_one_dir(self):
        """Test _extract_one_dir()."""
        l = logs.Logs()
        l._group_logs = unittest.mock.MagicMock(return_value="group")
        l._combine_logs = unittest.mock.MagicMock(return_value=["subdir1", "subdir2"])
        l._extract_mcu_logs = unittest.mock.MagicMock()

        res = l._extract_one_dir("/var/log/servod_9999", True)

        l._group_logs.assert_called_once_with("/var/log/servod_9999", True)
        l._combine_logs.assert_called_once_with("/var/log/servod_9999", "group")
        l._extract_mcu_logs.assert_has_calls(
            [unittest.mock.call("subdir1"), unittest.mock.call("subdir2")]
        )
        self.assertEqual(res, ["subdir1", "subdir2"])

    @unittest.mock.patch(
        "os.listdir",
        unittest.mock.MagicMock(
            return_value=[
                "laste.DEBUG",
                "latest.INFO",
                "laste.WARNING",
                "log.2022-09-12--13-44-38.726.DEBUG",
                "log.2022-09-12--13-44-38.726.INFO",
                "log.2022-09-12--13-44-38.726.WARNING",
                "log.2022-09-12--16-41-07.824.DEBUG",
                "log.2022-09-12--16-41-07.824.DEBUG.1",
                "log.2022-09-12--16-41-07.824.DEBUG.2",
                "log.2022-09-12--16-41-07.824.INFO",
                "log.2022-09-12--16-41-07.824.WARNING",
            ]
        ),
    )
    def test_group_logs(self):
        """Test _group_logs()."""
        l = logs.Logs()
        self.assertEqual(
            l._group_logs("/var/log/servod_9999", True),
            {
                "2022-09-12--13-44-38.726": [
                    "log.2022-09-12--13-44-38.726.DEBUG",
                    "log.2022-09-12--13-44-38.726.INFO",
                    "log.2022-09-12--13-44-38.726.WARNING",
                ],
                "2022-09-12--16-41-07.824": [
                    "log.2022-09-12--16-41-07.824.DEBUG",
                    "log.2022-09-12--16-41-07.824.DEBUG.1",
                    "log.2022-09-12--16-41-07.824.DEBUG.2",
                    "log.2022-09-12--16-41-07.824.INFO",
                    "log.2022-09-12--16-41-07.824.WARNING",
                ],
            },
        )
        self.assertEqual(
            l._group_logs("/var/log/servod_9999", False),
            {
                "2022-09-12--16-41-07.824": [
                    "log.2022-09-12--16-41-07.824.DEBUG",
                    "log.2022-09-12--16-41-07.824.DEBUG.1",
                    "log.2022-09-12--16-41-07.824.DEBUG.2",
                    "log.2022-09-12--16-41-07.824.INFO",
                    "log.2022-09-12--16-41-07.824.WARNING",
                ]
            },
        )

    @unittest.mock.patch("os.makedirs", unittest.mock.MagicMock())
    @unittest.mock.patch("builtins.open", unittest.mock.mock_open())
    def test_combine_logs(self):
        """Test _combine_logs()."""
        l = logs.Logs()
        groups = {
            "2022-09-12--13-44-38.726": [
                "log.2022-09-12--13-44-38.726.DEBUG",
                "log.2022-09-12--13-44-38.726.INFO",
                "log.2022-09-12--13-44-38.726.WARNING",
            ],
            "2022-09-12--16-41-07.824": [
                "log.2022-09-12--16-41-07.824.DEBUG",
                "log.2022-09-12--16-41-07.824.DEBUG.1",
                "log.2022-09-12--16-41-07.824.DEBUG.2",
                "log.2022-09-12--16-41-07.824.INFO",
                "log.2022-09-12--16-41-07.824.WARNING",
            ],
        }

        res = l._combine_logs("/var/log/servod_9999", groups)

        self.assertEqual(
            res,
            [
                "/tmp/servodlog/servod_9999.2022-09-12--13-44-38.726",
                "/tmp/servodlog/servod_9999.2022-09-12--16-41-07.824",
            ],
        )

    @unittest.mock.patch("os.path.exists", unittest.mock.MagicMock(return_value=True))
    def test_extract_mcu_logs(self):
        """Test _extract_mcu_logs()."""
        temp_dir = tempfile.mkdtemp()
        with open(
            os.path.join(temp_dir, logs.OUTPUT_JOINT_DEBUG_LOG), "w+", encoding="utf-8"
        ) as file:
            file.write("testing\n")
            file.write(
                "2020-01-23 13:15:12,223 - servo_v4 - EC3PO.Console - DEBUG - "
                "console.py:219:LogConsoleOutput - /dev/pts/9 - cc polarity: cc1\n"
            )
            file.write("testing\n")

        l = logs.Logs()
        l._extract_mcu_logs(temp_dir)
        with open(
            os.path.join(temp_dir, "servo_v4.txt"), "r", encoding="utf-8"
        ) as mcu_f:
            self.assertEqual(mcu_f.read(), "cc polarity: cc1\n")
        shutil.rmtree(temp_dir)

    def test_add_args(self):
        """Test add_args()."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="tool")
        tparser = subparsers.add_parser("logs")
        logs.Logs().add_args(tparser)

        self.assertEqual(
            parser.parse_args(["logs", "extract", "-p", "9999", "9998"]).port,
            [9999, 9998],
        )
        self.assertEqual(
            parser.parse_args(["logs", "extract", "--port", "9999", "9998"]).port,
            [9999, 9998],
        )
        self.assertEqual(
            parser.parse_args(["logs", "extract", "-d", "dir", "dir2"]).directory,
            ["dir", "dir2"],
        )
        self.assertEqual(
            parser.parse_args(
                ["logs", "extract", "--directory", "dir", "dir2"]
            ).directory,
            ["dir", "dir2"],
        )
        self.assertEqual(
            parser.parse_args(["logs", "extract", "-d", "dir"]).previous, False
        )
        self.assertEqual(
            parser.parse_args(["logs", "extract", "-d", "dir", "--previous"]).previous,
            True,
        )

    @unittest.mock.patch("shutil.rmtree", unittest.mock.MagicMock())
    @unittest.mock.patch("os.makedirs", unittest.mock.MagicMock())
    @unittest.mock.patch("os.path.exists", unittest.mock.MagicMock(return_value=True))
    def test_cleanup_output_dir(self):
        """Test _cleanup_output_dir()."""
        logs._cleanup_output_dir()
        shutil.rmtree.assert_called_once_with(logs.OUTPUT_DIR)
        os.makedirs(logs.OUTPUT_DIR)

    @unittest.mock.patch("tarfile.TarFile.add", unittest.mock.MagicMock())
    def test_make_tarfile(self):
        """Test _make_tarfile()."""
        logs._make_tarfile("output", ["/path/source", "/path2/source2"])
        tarfile.TarFile.add.assert_has_calls(
            [
                unittest.mock.call("/path/source", arcname="source"),
                unittest.mock.call("/path2/source2", arcname="source2"),
            ]
        )


if __name__ == "__main__":
    unittest.main()
