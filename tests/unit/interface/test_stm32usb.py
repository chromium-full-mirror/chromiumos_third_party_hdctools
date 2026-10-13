#!/usr/bin/env python3
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# pylint: disable=unused-argument
# pylint: disable=unused-variable
import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

import usb

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
        self.susb.DEV_EP_STORE[devid] = {
            self.susb._interface: EPInfo(write_ep=MagicMock(), read_ep=MagicMock())
        }

        result = self.susb._get_ep(write=False)

        self.assertEqual(
            result, self.susb.DEV_EP_STORE[devid][self.susb._interface].read_ep
        )

    def test_get_ep_write(self):
        devid = self.susb.get_device_info()
        self.susb.DEV_EP_STORE[devid] = {
            self.susb._interface: EPInfo(write_ep=MagicMock(), read_ep=MagicMock())
        }

        result = self.susb._get_ep(write=True)

        self.assertEqual(
            result, self.susb.DEV_EP_STORE[devid][self.susb._interface].write_ep
        )

    def test_get_ep_no_interface(self):
        devid = self.susb.get_device_info()
        self.susb.DEV_EP_STORE[devid] = {}

        with self.assertRaises(SusbError) as context:
            self.susb._get_ep(write=True)

        self.assertEqual(
            str(context.exception),
            "Device %r has no endpoints setup for interface %d"
            % (devid, self.susb._interface),
        )

    @patch("servo.common.interface.stm32usb.time.sleep")
    @patch("servo.utils.usb_hierarchy.Hierarchy.get_usb_device")
    @patch("usb.util.release_interface")
    @patch("usb.util.claim_interface")
    @patch("usb.util.find_descriptor")
    def test_susb_reset_usb_reinitializes_siblings_and_throttles(
        self,
        mock_find_descriptor,
        mock_claim_interface,
        mock_release_interface,
        mock_get_usb_device,
        unused_mock_sleep,
    ):
        serial = "MULTI_INTF_SERIAL"
        susb0 = Susb(
            vendor=0x18D1,
            product=0x501A,
            interface_id=0,
            serialname=serial,
            logger=MagicMock(),
        )
        susb2 = Susb(
            vendor=0x18D1,
            product=0x501A,
            interface_id=2,
            serialname=serial,
            logger=MagicMock(),
        )
        susb3 = Susb(
            vendor=0x18D1,
            product=0x501A,
            interface_id=3,
            serialname=serial,
            logger=MagicMock(),
        )
        # Simulate Si2cBus releasing its USB interface after claiming endpoints.
        susb2.release()
        self.assertTrue(susb2._is_released)

        devid = susb0.get_device_info()
        Susb.DEV_LAST_RESET_TIME.pop(devid, None)

        susb0._find_device = MagicMock(wraps=susb0._find_device)
        susb2._find_device = MagicMock(wraps=susb2._find_device)
        susb3._find_device = MagicMock(wraps=susb3._find_device)

        mock_release_interface.reset_mock()
        susb0.reset_usb(force=True, reset_device=True)

        susb0._find_device.assert_called_once_with(force=False)
        susb2._find_device.assert_called_once_with(force=False)
        susb3._find_device.assert_called_once_with(force=False)
        self.assertTrue(susb2._is_released)
        self.assertFalse(susb0._is_released)
        self.assertFalse(susb3._is_released)

        # Immediate follow-up hardware reset from a sibling interface within
        # RESET_COOLDOWN_S should skip the hardware reset and downgrade to a
        # non-forced _find_device() on the caller only.
        susb0._find_device.reset_mock()
        susb2._find_device.reset_mock()
        susb3._find_device.reset_mock()
        susb3.reset_usb(force=True, reset_device=True)
        susb0._find_device.assert_not_called()
        susb2._find_device.assert_not_called()
        susb3._find_device.assert_called_once_with(force=False)

    def test_susb_needs_rediscovery(self):
        devid = self.susb.get_device_info()
        self.susb._dev = MagicMock()
        self.susb.DEV_EP_STORE[devid] = {
            self.susb._interface: EPInfo(write_ep=MagicMock(), read_ep=MagicMock())
        }
        self.assertFalse(self.susb.needs_rediscovery())

        # Missing endpoint entry triggers rediscovery.
        self.susb.DEV_EP_STORE[devid] = {}
        self.assertTrue(self.susb.needs_rediscovery())

        # None _dev handle triggers rediscovery.
        self.susb.DEV_EP_STORE[devid] = {
            self.susb._interface: EPInfo(write_ep=MagicMock(), read_ep=MagicMock())
        }
        self.susb._dev = None
        self.assertTrue(self.susb.needs_rediscovery())

    def _setup_cdc_acm_device(
        self, mock_find_descriptor, mock_get_usb_device, comm_class, ep_addresses
    ):
        """Simulate a Zephyr CDC-ACM device: comm intf 0 + data intf 1.

        Args:
          mock_find_descriptor: patched usb.util.find_descriptor
          mock_get_usb_device: patched Hierarchy.get_usb_device
          comm_class: bInterfaceClass of USB interface 0
          ep_addresses: bulk endpoint addresses on the data interface (1)

        Returns:
          (dev, endpoints) mocks
        """
        dev = MagicMock()
        dev.address = 42
        dev.is_kernel_driver_active.return_value = True
        mock_get_usb_device.return_value = dev

        interfaces = {0: MagicMock(), 1: MagicMock()}
        interfaces[0].bInterfaceNumber = 0
        interfaces[0].bInterfaceClass = comm_class
        interfaces[1].bInterfaceNumber = 1
        interfaces[1].bInterfaceClass = usb.CLASS_DATA

        endpoints = []
        for address in ep_addresses:
            ep = MagicMock()
            ep.bEndpointAddress = address
            ep.bmAttributes = usb.util.ENDPOINT_TYPE_BULK
            endpoints.append(ep)

        def find_descriptor(_desc, **kwargs):
            if "bInterfaceNumber" in kwargs:
                return interfaces.get(kwargs["bInterfaceNumber"])
            if "bEndpointAddress" in kwargs:
                for ep in endpoints:
                    if ep.bEndpointAddress == kwargs["bEndpointAddress"]:
                        return ep
                return None
            for ep in endpoints:
                if kwargs["custom_match"](ep):
                    return ep
            return None

        mock_find_descriptor.side_effect = find_descriptor
        return dev, endpoints

    def _new_maui_susb(self, serial):
        return Susb(
            vendor=0x18D1,
            product=0x5085,
            interface_id=1,
            serialname=serial,
            logger=MagicMock(),
        )

    @patch("servo.utils.usb_hierarchy.Hierarchy.get_usb_device")
    @patch("usb.util.claim_interface")
    @patch("usb.util.find_descriptor")
    def test_susb_find_device_cdc_acm_it82002(
        self, mock_find_descriptor, mock_claim_interface, mock_get_usb_device
    ):
        # Maui v1.2 (IT82002): bulk IN 0x83 does not match 1+0x81, OUT 0x02 does.
        dev, (ep_in, ep_out) = self._setup_cdc_acm_device(
            mock_find_descriptor, mock_get_usb_device, usb.CLASS_COMM, (0x83, 0x02)
        )
        susb = self._new_maui_susb("MAUI_IT82002")

        eps = susb.DEV_EP_STORE[susb.get_device_info()][1]
        self.assertEqual(eps.read_ep, ep_in)
        self.assertEqual(eps.write_ep, ep_out)
        dev.detach_kernel_driver.assert_any_call(0)
        mock_claim_interface.assert_any_call(dev, 0)
        mock_claim_interface.assert_any_call(dev, 1)
        dev.ctrl_transfer.assert_called_once_with(
            bmRequestType=0x21,
            bRequest=0x22,
            wValue=0x03,
            wIndex=0,
        )

    @patch("servo.utils.usb_hierarchy.Hierarchy.get_usb_device")
    @patch("usb.util.claim_interface")
    @patch("usb.util.find_descriptor")
    def test_susb_find_device_cdc_acm_mspm0(
        self, mock_find_descriptor, mock_claim_interface, mock_get_usb_device
    ):
        # Maui v1.1 (MSPM0): bulk IN 0x82 matches 1+0x81, OUT 0x01 does not.
        dev, (ep_in, ep_out) = self._setup_cdc_acm_device(
            mock_find_descriptor, mock_get_usb_device, usb.CLASS_COMM, (0x82, 0x01)
        )
        susb = self._new_maui_susb("MAUI_MSPM0")

        eps = susb.DEV_EP_STORE[susb.get_device_info()][1]
        self.assertEqual(eps.read_ep, ep_in)
        self.assertEqual(eps.write_ep, ep_out)
        dev.ctrl_transfer.assert_called_once()

    @patch("servo.utils.usb_hierarchy.Hierarchy.get_usb_device")
    @patch("usb.util.claim_interface")
    @patch("usb.util.find_descriptor")
    def test_susb_find_device_cdc_data_without_comm_interface(
        self, mock_find_descriptor, mock_claim_interface, mock_get_usb_device
    ):
        # Interface N-1 is not a CDC Communications interface: no DTR request.
        dev, _ = self._setup_cdc_acm_device(
            mock_find_descriptor, mock_get_usb_device, 0xFF, (0x83, 0x02)
        )
        self._new_maui_susb("MAUI_NO_COMM")

        dev.ctrl_transfer.assert_not_called()
        mock_claim_interface.assert_called_once_with(dev, 1)

    @patch("servo.utils.usb_hierarchy.Hierarchy.get_usb_device")
    @patch("usb.util.claim_interface")
    @patch("usb.util.find_descriptor")
    def test_susb_find_device_missing_endpoint(
        self, mock_find_descriptor, mock_claim_interface, mock_get_usb_device
    ):
        self._setup_cdc_acm_device(
            mock_find_descriptor, mock_get_usb_device, usb.CLASS_COMM, (0x83,)
        )
        with self.assertRaises(SusbError):
            self._new_maui_susb("MAUI_NO_OUT_EP")


if __name__ == "__main__":
    unittest.main()
