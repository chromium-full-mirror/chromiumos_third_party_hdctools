#!/usr/bin/env python3
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# pylint: disable=unused-argument
import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

from servo.common.interface.stm32i2c import Si2cBus
from servo.common.interface.stm32i2c import Si2cError


class TestSi2cBus(unittest.TestCase):
    @patch("servo.common.interface.stm32usb.Susb")
    def setUp(self, mock_Susb):
        self.mock_susb_instance = MagicMock()
        mock_Susb.return_value = self.mock_susb_instance

        self.susb_bus = Si2cBus(
            vendor=0x18D1, product=0x501A, interface=1, port=0, serialname="SERIAL"
        )

    def test_reinitialize(self):
        self.susb_bus.reinitialize()
        self.mock_susb_instance.reset_usb.assert_called_once()

    @patch("servo.common.interface.stm32usb.Susb.write_ep")
    def test_raw_wr_rd(self, mock_write_ep):
        expected_read_data = [0, 0, 0, 0x01, 0x02, 0x02, 0x02]
        self.susb_bus._susb.read_ep = MagicMock(return_value=expected_read_data)
        child_address = 0x48
        write_list = [0x20, 0x01, 0x02]
        read_count = 2

        result = self.susb_bus._raw_wr_rd(child_address, write_list, read_count)
        self.assertEqual(result, expected_read_data[4:])

    def test_raw_wr_rd_with_raise_exception_read_status_failed(self):
        child_address = 0x48
        write_list = [0x20, 0x01, 0x02]
        read_count = 2
        with self.assertRaisesRegex(Si2cError, "Read status failed."):
            self.susb_bus._raw_wr_rd(child_address, write_list, read_count)

    @patch("servo.common.interface.stm32usb.Susb.write_ep")
    def test_raw_wr_rd_with_raise_exception_read_status_failed_with_data(
        self, mock_write_ep
    ):
        expected_read_data = [1, 1, 0, 0x01, 0x02, 0x02, 0x02]
        self.susb_bus._susb.read_ep = MagicMock(return_value=expected_read_data)
        child_address = 0x48
        write_list = [0x20, 0x01, 0x02]
        read_count = 2
        with self.assertRaisesRegex(
            Si2cError,
            "Read status failed: 0x%02x%02x"
            % (expected_read_data[1], expected_read_data[0]),
        ):
            self.susb_bus._raw_wr_rd(child_address, write_list, read_count)


if __name__ == "__main__":
    unittest.main()
