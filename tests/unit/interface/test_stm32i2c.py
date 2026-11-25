#!/usr/bin/env python3
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# pylint: disable=unused-argument
import errno
import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

import usb

from servo.common.interface.stm32i2c import Si2cBus
from servo.common.interface.stm32i2c import Si2cError
from servo.common.interface.stm32usb import SusbError


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

    def test_raw_wr_rd_rediscovers_when_endpoints_missing(self) -> None:
        """Verifies endpoint rediscovery when sibling reset wiped endpoints."""
        self.mock_susb_instance.needs_rediscovery.return_value = True
        self.mock_susb_instance.read_ep.return_value = [0, 0, 0, 0, 0xAB]

        result = self.susb_bus._raw_wr_rd(0x78, [0x00], 1)

        self.assertEqual(result, [0xAB])
        self.mock_susb_instance.reset_usb.assert_called_once_with()
        self.mock_susb_instance.write_ep.assert_called_once()

    def test_raw_wr_rd_rediscovers_on_enodev(self) -> None:
        """Verifies forced rediscovery and retry on stale USB handle ENODEV."""
        self.mock_susb_instance.needs_rediscovery.return_value = False
        self.mock_susb_instance._vendor = 0x18D1
        self.mock_susb_instance._product = 0x5014
        self.mock_susb_instance.write_ep.side_effect = [
            OSError(errno.ENODEV, "No such device"),
            None,
        ]
        self.mock_susb_instance.read_ep.return_value = [0, 0, 0, 0]

        result = self.susb_bus._raw_wr_rd(0x78, [0x00], 0)

        self.assertEqual(result, [])
        self.mock_susb_instance.reset_usb.assert_called_once_with(force=True)
        self.assertEqual(self.mock_susb_instance.write_ep.call_count, 2)

    def test_raw_wr_rd_release_does_not_mask_original_error(self) -> None:
        """Verifies cleanup release ignores SusbError when endpoints missing."""
        self.mock_susb_instance.needs_rediscovery.return_value = True
        self.mock_susb_instance.reset_usb.side_effect = RuntimeError("No device found")
        self.mock_susb_instance.release.side_effect = SusbError(
            "has no endpoints setup for interface 5"
        )

        with self.assertRaisesRegex(RuntimeError, "No device found"):
            self.susb_bus._raw_wr_rd(0x78, [0x00], 0)

    def test_is_endpoint_responsive_drains_stale_packet_and_succeeds(self) -> None:
        self.mock_susb_instance.needs_rediscovery.return_value = False
        self.mock_susb_instance.TIMEOUT_MS = 100
        self.mock_susb_instance.release.reset_mock()
        self.mock_susb_instance.read_ep.side_effect = [
            [0x00, 0x00, 0x00, 0x00],
            usb.core.USBTimeoutError("drain complete"),
            [0x05, 0x00, 0x00, 0x00, 0x00],
        ]

        self.assertTrue(self.susb_bus.is_endpoint_responsive())
        self.mock_susb_instance.write_ep.assert_called_once_with(
            b"\x0f\x00\x00\x01", 100
        )
        self.mock_susb_instance.release.assert_called_once_with()

    def test_is_endpoint_responsive_accepts_disabled_status(self) -> None:
        self.mock_susb_instance.needs_rediscovery.return_value = False
        self.mock_susb_instance.TIMEOUT_MS = 100
        self.mock_susb_instance.read_ep.side_effect = [
            usb.core.USBTimeoutError("drain complete"),
            [0x06, 0x00, 0x00, 0x00, 0x00],
        ]

        self.assertTrue(self.susb_bus.is_endpoint_responsive())

    def test_is_endpoint_responsive_returns_false_on_write_timeout(self) -> None:
        self.mock_susb_instance.needs_rediscovery.return_value = False
        self.mock_susb_instance.release.reset_mock()
        self.mock_susb_instance.read_ep.side_effect = usb.core.USBTimeoutError(
            "drain complete"
        )
        self.mock_susb_instance.write_ep.side_effect = usb.core.USBTimeoutError(
            "bulk out wedged"
        )

        self.assertFalse(self.susb_bus.is_endpoint_responsive())
        self.mock_susb_instance.release.assert_called_once_with()

    def test_is_endpoint_responsive_returns_false_on_unexpected_status(self) -> None:
        self.mock_susb_instance.needs_rediscovery.return_value = False
        self.mock_susb_instance.read_ep.side_effect = [
            usb.core.USBTimeoutError("drain complete"),
            [0x00, 0x00, 0x00, 0x00, 0xFF],
        ]

        self.assertFalse(self.susb_bus.is_endpoint_responsive())


if __name__ == "__main__":
    unittest.main()
