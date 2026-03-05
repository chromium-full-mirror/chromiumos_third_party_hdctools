# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
from unittest.mock import MagicMock
from unittest.mock import patch

from servo_updater import fw_update


class TestFwUpdate:
    def test_debuglog(self, capsys):
        fw_update.DEBUG = True
        fw_update.debuglog("test")
        assert "test" in capsys.readouterr().out
        fw_update.DEBUG = False

    @patch("servo_updater.fw_update.usb.core.find")
    @patch("servo_updater.fw_update.usb.util.get_string")
    @patch("servo_updater.fw_update.usb.util.find_descriptor")
    def test_supdate_connect(self, mock_find_desc, mock_get_string, mock_find):
        mock_find.return_value = None

        mock_dev = MagicMock()
        mock_find.return_value = [mock_dev]
        mock_desc = MagicMock()
        mock_desc.bInterfaceNumber = 1
        mock_find_desc.return_value = mock_desc
        mock_get_string.return_value = "12345"
        updater = fw_update.Supdate()
        updater._brdcfg = {"vid": 0x18D1, "pid": 0x501A}
        updater.connect_usb("12345")
        assert updater._dev == mock_dev

    @patch("servo_updater.fw_update.Supdate")
    @patch("servo_updater.fw_update.json.load")
    @patch("servo_updater.fw_update.sys.exit")
    def test_main_exit(
        self, unused_mock_exit, unused_mock_json, unused_mock_supdate, tmp_path
    ):
        board_file = tmp_path / "servo_v4"
        board_file.write_text("{}")
        with patch(
            "servo_updater.fw_update.argparse.ArgumentParser.parse_args"
        ) as mock_parse:
            mock_parse.return_value = argparse.Namespace(
                file=None,
                version=True,
                pid="501a",
                vid="18d1",
                board=str(board_file),
                dev="12345",
                serial="12345",
                verbose=False,
                list=False,
            )
            fw_update.main()
