#!/usr/bin/env python3
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# pylint: disable=unused-argument
# pylint: disable=unused-variable
import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

from servo.common.interface.stm32usb import DeviceInfo
from servo.common.interface.stm32usb import EPInfo
from servo.common.interface.stm32usb import Susb
from servo.common.interface.stm32usb import SusbError


class TestSusbClass(unittest.TestCase):
    @patch("servo.utils.usb_hierarchy.Hierarchy.get_usb_device")
    @patch("usb.util.find_descriptor")
    def setUp(self, mock_find_descriptor, mock_get_usb_device):
        self.susb = Susb(
            vendor=0x18D1,
            product=0x500F,
            interface_id=1,
            serialname="SERIAL",
            logger=MagicMock(),
        )

    @patch("servo.utils.usb_hierarchy.Hierarchy.get_usb_device")
    @patch("usb.util.find_descriptor")
    def test_susb_constructor(self, mock_find_descriptor, mock_get_usb_device):
        susb = Susb(
            vendor=0x18D1,
            product=0x500F,
            interface_id=1,
            serialname="SERIAL",
            logger=MagicMock(),
        )
        mock_get_usb_device.assert_called()
        self.assertIsInstance(susb, Susb)

    @patch("servo.utils.usb_hierarchy.Hierarchy.get_usb_device")
    @patch("usb.util.claim_interface")
    @patch("usb.util.find_descriptor")
    def test_susb_find_device(
        self, mock_find_descriptor, mock_claim_interface, mock_get_usb_device
    ):
        susb = Susb(
            vendor=0x18D1,
            product=0x500F,
            interface_id=1,
            serialname="SERIAL",
            logger=MagicMock(),
        )
        mock_find_descriptor.return_value = MagicMock()
        mock_get_usb_device.assert_called_once()
        mock_claim_interface.assert_called()

    @patch("servo.utils.usb_hierarchy.Hierarchy.get_usb_device")
    @patch("usb.util.claim_interface")
    @patch("usb.util.find_descriptor")
    def test_susb_find_device_existing_config(
        self, mock_find_descriptor, mock_claim_interface, mock_get_usb_device
    ):
        susb = Susb(
            vendor=0x18D1,
            product=0x500F,
            interface_id=1,
            serialname="SERIAL",
            logger=MagicMock(),
        )
        susb.DEV_CONFIG_MAP[susb.get_device_info()] = 123
        susb._find_device()
        mock_claim_interface.assert_called()

    @patch("servo.utils.usb_hierarchy.Hierarchy.get_usb_device")
    @patch("usb.util.claim_interface")
    @patch("usb.util.find_descriptor")
    def test_susb_reset_usb(
        self, mock_find_descriptor, mock_claim_interface, mock_get_usb_device
    ):
        susb = Susb(
            vendor=0x18D1,
            product=0x500F,
            interface_id=1,
            serialname="SERIAL",
            logger=MagicMock(),
        )
        susb._find_device = MagicMock()
        susb.reset_usb()
        susb._find_device.assert_called_once()

    @patch("servo.utils.usb_hierarchy.Hierarchy.get_usb_device")
    @patch("usb.util.find_descriptor")
    @patch("usb.util.claim_interface")
    def test_susb_get_device_info(
        self, mock_claim_interface, mock_find_descriptor, mock_get_usb_device
    ):
        susb = Susb(
            vendor=0x18D1,
            product=0x500F,
            interface_id=1,
            serialname="SERIAL",
            logger=MagicMock(),
        )
        info = susb.get_device_info()
        self.assertEqual(info, DeviceInfo(0x18D1, 0x500F, "SERIAL"))

    @patch("servo.utils.usb_hierarchy.Hierarchy.get_usb_device")
    @patch("usb.util.find_descriptor")
    @patch("usb.util.claim_interface")
    def test_susb_control(
        self, mock_claim_interface, mock_find_descriptor, mock_get_usb_device
    ):
        susb = Susb(
            vendor=0x18D1,
            product=0x500F,
            interface_id=1,
            serialname="SERIAL",
            logger=MagicMock(),
        )
        susb.control(request=0x01, value=0x1234)
        susb._dev.ctrl_transfer.assert_called_once_with(
            bmRequestType=0x41,
            bRequest=0x01,
            wIndex=1,
            wValue=0x1234,
        )

    def test_get_ep_read(self):
        devid = self.susb.get_device_info()
        self.susb.DEV_EP_STORE = {
            devid: {
                self.susb._interface: EPInfo(write_ep=MagicMock(), read_ep=MagicMock())
            }
        }

        result = self.susb._get_ep(write=False)

        self.assertEqual(
            result, self.susb.DEV_EP_STORE[devid][self.susb._interface].read_ep
        )

    def test_get_ep_write(self):
        devid = self.susb.get_device_info()
        self.susb.DEV_EP_STORE = {
            devid: {
                self.susb._interface: EPInfo(write_ep=MagicMock(), read_ep=MagicMock())
            }
        }

        result = self.susb._get_ep(write=True)

        self.assertEqual(
            result, self.susb.DEV_EP_STORE[devid][self.susb._interface].write_ep
        )

    def test_get_ep_no_interface(self):
        devid = self.susb.get_device_info()
        self.susb.DEV_EP_STORE = {devid: {}}

        with self.assertRaises(SusbError) as context:
            self.susb._get_ep(write=True)

        self.assertEqual(
            str(context.exception),
            "Device %r has no endpoints setup for interface %d"
            % (devid, self.susb._interface),
        )


if __name__ == "__main__":
    unittest.main()
