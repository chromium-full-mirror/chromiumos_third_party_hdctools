#!/usr/bin/env python
# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import struct
import unittest
from unittest import mock

from servo_updater import fw_update


class TestFwUpdateLoadFile(unittest.TestCase):

    @mock.patch("builtins.open", new_callable=mock.mock_open)
    @mock.patch("os.path.getsize")
    def test_load_file_success(self, mock_getsize, mock_open):
        """Test load_file with matching file size."""
        updater = fw_update.Supdate()
        updater._flashsize = 1024
        mock_getsize.return_value = 1024

        updater.load_file("test.bin")

        mock_getsize.assert_called_once_with("test.bin")
        mock_open.assert_called_once_with("test.bin", "rb")
        self.assertEqual(updater._filesize, 1024)

    @mock.patch("builtins.open", new_callable=mock.mock_open)
    @mock.patch("os.path.getsize")
    def test_load_file_size_mismatch(self, mock_getsize, mock_open):
        """Test load_file with mismatched file size."""
        updater = fw_update.Supdate()
        updater._flashsize = 1024
        mock_getsize.return_value = 512

        with self.assertRaises(fw_update.FwUpdaterException):
            updater.load_file("test.bin")

        mock_getsize.assert_called_once_with("test.bin")
        mock_open.assert_called_once_with("test.bin", "rb")

    @mock.patch("os.path.getsize")
    def test_load_file_not_found(self, mock_getsize):
        """Test load_file with a non-existent file."""
        updater = fw_update.Supdate()
        mock_getsize.side_effect = FileNotFoundError

        with self.assertRaises(FileNotFoundError):
            updater.load_file("nonexistent.bin")

        mock_getsize.assert_called_once_with("nonexistent.bin")


class TestFwUpdateLoadBoard(unittest.TestCase):

    @mock.patch(
        "builtins.open",
        new_callable=mock.mock_open,
        read_data=(
            '{"board": "test board", "vid": "0x18d1", "pid": "0x5022", '
            '"flash": "0x8000000", "regions": {"RW": ["0x10000", "0x10000"]}}'
        ),
    )
    def test_load_board_success(self, mock_open):
        """Test load_board with valid JSON data."""
        updater = fw_update.Supdate()
        updater.load_board("test.json")

        mock_open.assert_called_once_with("test.json", encoding="utf-8")
        self.assertEqual(updater._brdcfg["board"], "test board")
        self.assertEqual(updater._brdcfg["vid"], 0x18D1)
        self.assertEqual(updater._brdcfg["pid"], 0x5022)
        self.assertEqual(updater._brdcfg["flash"], 0x8000000)
        self.assertEqual(updater._brdcfg["regions"]["RW"][0], 0x10000)
        self.assertEqual(updater._brdcfg["regions"]["RW"][1], 0x10000)
        self.assertEqual(updater._flashsize, 0x10000)


class TestFwUpdateWriteFile(unittest.TestCase):

    @mock.patch("servo_updater.fw_update.Supdate.wr_command")
    def test_write_file(self, mock_wr_command):
        """Test the write_file method."""
        updater = fw_update.Supdate()
        updater._region = "RW"
        updater._base = 0x8010000
        updater._brdcfg = {
            "flash": 0x8000000,
            "regions": {"RW": [0x10000, 0x1000]},  # Offset and length
        }
        # Create a test binary file content
        bin_content = b"\x00" * 0x1000
        mock_binfile = mock.MagicMock()

        # Mock the read function to return data from bin_content
        read_pos = 0

        def mock_read(size):
            nonlocal read_pos
            end_pos = min(read_pos + size, len(bin_content))
            data = bin_content[read_pos:end_pos]
            read_pos = end_pos
            return data

        mock_binfile.read.side_effect = mock_read

        updater._binfile = mock_binfile

        # Mock the return value for the validation read
        mock_wr_command.return_value = b"\x00\x00\x00\x00"

        updater.write_file()

        # Assertions to check the calls made to wr_command
        self.assertTrue(mock_wr_command.called)
        # Example: Check the first command packet
        first_cmd_call = mock_wr_command.call_args_list[0]
        args, kwargs = first_cmd_call
        cmd_packet = args[0]

        pagesize, cmd_val, base_addr = struct.unpack(">III", cmd_packet)
        self.assertEqual(pagesize, 128 + 12)
        self.assertEqual(cmd_val, 0)
        self.assertEqual(base_addr, 0x8010000)
        self.assertEqual(kwargs["read_count"], 0)

        # Check that data is sent in 32-byte chunks
        data_calls = [
            call
            for call in mock_wr_command.call_args_list
            if call[0] and len(call[0][0]) == 32
        ]
        self.assertEqual(len(data_calls), 0x1000 // 32)

        # Check for validation calls (empty write, read_count=4)
        validation_calls = [
            call
            for call in mock_wr_command.call_args_list
            if call == mock.call("".encode(), read_count=4)
        ]
        self.assertEqual(len(validation_calls), 0x1000 // 128)


if __name__ == "__main__":
    unittest.main()
