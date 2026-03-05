# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest
from unittest import mock

from servo.common.interface import i2cbus


class TestI2CBus(unittest.TestCase):
    def setUp(self):
        self.interface_path = "/dev/i2c-0"
        self.patcher = mock.patch("io.open")
        self.mock_open = self.patcher.start()
        self.mock_file = self.mock_open.return_value
        # Setup fileno for ioctl
        self.mock_file.fileno.return_value = 10

    def tearDown(self):
        self.patcher.stop()

    def test_init_opens_file(self):
        bus = i2cbus.I2CBus(self.interface_path)
        self.mock_open.assert_called_once_with(
            self.interface_path, mode="r+b", buffering=0
        )
        self.assertEqual(bus._interface, self.mock_file)

    def test_close_closes_file(self):
        bus = i2cbus.I2CBus(self.interface_path)
        bus.close()
        self.mock_file.close.assert_called_once()
        self.assertIsNone(bus._interface)

    def test_context_manager(self):
        with i2cbus.I2CBus(self.interface_path) as bus:
            self.assertIsInstance(bus, i2cbus.I2CBus)
        self.mock_file.close.assert_called_once()

    def test_raw_wr_rd_write(self):
        bus = i2cbus.I2CBus(self.interface_path)
        with mock.patch("fcntl.ioctl") as mock_ioctl:
            bus._raw_wr_rd(0x48, [0x10, 0x20])
            mock_ioctl.assert_called_once_with(
                self.mock_file.fileno(), i2cbus.I2CBus._I2C_WORKER_FORCE, 0x48
            )
            # modern byte handling means we write bytes
            expected_write = bytes(bytearray([0x10, 0x20]))
            self.mock_file.write.assert_called_once_with(expected_write)

    def test_raw_wr_rd_read(self):
        bus = i2cbus.I2CBus(self.interface_path)
        self.mock_file.read.return_value = b"\x01\x02"
        with mock.patch("fcntl.ioctl") as unused_mock_ioctl:
            result = bus._raw_wr_rd(0x48, [], 2)
            self.assertEqual(result, [1, 2])
