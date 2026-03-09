# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import io
import json
import struct
from unittest.mock import MagicMock
from unittest.mock import patch

from servo_updater import fw_update


class TestFwUpdate:
    def test_debuglog(self, capsys):
        fw_update.DEBUG = True
        fw_update.debuglog("test")
        assert "test" in capsys.readouterr().out
        fw_update.DEBUG = False

    def test_log(self, capsys):
        fw_update.log("test log")
        assert "test log" in capsys.readouterr().out

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
        # vid/pid MUST be integers for %x formatting
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

    def test_supdate_load_board(self, tmp_path):
        updater = fw_update.Supdate()
        board_file = tmp_path / "test_board.json"
        board_data = {
            "board": "test_board",
            "vid": "0x1234",
            "pid": "0x5678",
            "flash": "0x1000",
            "regions": {"RW": ["0x1000", "0x2000"]},
        }
        board_file.write_text(json.dumps(board_data))
        updater.load_board(str(board_file))
        assert updater._brdcfg["vid"] == 0x1234
        assert updater._brdcfg["pid"] == 0x5678
        assert updater._flashsize == 0x2000

    def test_supdate_load_file(self, tmp_path):
        updater = fw_update.Supdate()
        bin_file = tmp_path / "test_fw.bin"
        bin_file.write_bytes(b"\x01\x02\x03\x04")

        # Flash size must match file size
        updater._flashsize = 4

        updater.load_file(str(bin_file))
        assert updater._filesize == 4
        assert updater._binfile is not None

    def test_supdate_wr_command(self):
        updater = fw_update.Supdate()
        updater._write_ep = MagicMock()
        updater._read_ep = MagicMock()
        # read(512, ...)
        updater._read_ep.read.return_value = b"\x01\x02\x03"

        res = updater.wr_command([0xAA, 0xBB], read_count=3)
        updater._write_ep.write.assert_called_once_with([0xAA, 0xBB], 100)
        updater._read_ep.read.assert_called_once_with(512, 2000)
        assert res == b"\x01\x02\x03"

    def test_supdate_stop(self):
        updater = fw_update.Supdate()
        updater._write_ep = MagicMock()
        updater._read_ep = MagicMock()
        updater._read_ep.read.return_value = b"\x00\x00\x00\x00"
        updater._dev = MagicMock()
        updater._brdcfg = {"iface": 0}

        updater.stop()
        # stop uses wr_command internally
        updater._write_ep.write.assert_called()

    def test_supdate_start(self):
        updater = fw_update.Supdate()
        updater._write_ep = MagicMock()
        updater._read_ep = MagicMock()
        # Returns 8 bytes: base=0x2000, version=1
        updater._read_ep.read.return_value = struct.pack(">II", 0x2000, 1)
        updater._brdcfg = {"flash": 0x1000, "regions": {"RW": [0x1000, 0x2000]}}

        with patch("time.sleep", create=True):
            updater.start()

        assert updater._base == 0x2000
        assert updater._region == "RW"

    @patch("sys.stdout.write", create=True)
    @patch("sys.stdout.flush", create=True)
    def test_supdate_write_file(self, unused_mock_flush, unused_mock_write):
        updater = fw_update.Supdate()
        updater._write_ep = MagicMock()
        updater._read_ep = MagicMock()

        updater._brdcfg = {"flash": 0x1000, "regions": {"RW": [0x1000, 0x100]}}
        updater._region = "RW"
        updater._base = 0x2000
        # offset = base - flash = 0x2000 - 0x1000 = 0x1000
        # matches regions["RW"][0]

        # Buffer must be at least offset + length = 0x1000 + 0x100 = 0x1100
        updater._binfile = io.BytesIO(b"\x00" * 0x2000)

        # Mocking an ack for each chunk and then the success check
        # ack (read_count=0 returns None in wr_command)
        # result check (read_count=4 returns 4 bytes)
        updater._read_ep.read.side_effect = [
            b"\x00\x00\x00\x00",  # success check for first 128-byte packet
            b"\x00\x00\x00\x00",  # success check for second 128-byte packet
        ]

        updater.write_file()

        # Total length 0x100 = 256 bytes.
        # Two 128-byte packets.
        # Per packet: 1 cmd write, 4 data writes (32*4=128).
        # Success check wr_command("", read_count=4) does NOT call write
        # because write_list is empty.
        # Total: (1 + 4) * 2 = 10 writes.
        assert updater._write_ep.write.call_count == 10
