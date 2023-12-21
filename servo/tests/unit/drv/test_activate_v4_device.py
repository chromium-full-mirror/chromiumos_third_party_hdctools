# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import unittest
import unittest.mock

import mock

from servo.common.interface import interface
from servo.common.proto.servo_dev_pb2 import BoolResponse
from servo.common.proto.servo_dev_pb2 import V4DeviceResponse
from servo.data.drv import active_v4_device
from servo.data.drv import hw_driver


class TestActivate4Device(unittest.TestCase):
    """
    Unit test class for relaySwitch
    """

    def get_v4_device_info(self, device):
        if device == "default":
            return "ccd_cr50"
        else:
            return ["ccd_cr50", "c2d2"]

    def setUp(self):
        intfc = mock.Mock(interface.Interface)
        params = {"cmd": "set"}
        hw_drv = hw_driver.HwDriver(intfc, params)
        self.active_v4_device = active_v4_device.activeV4Device(hw_drv, params)
        response = BoolResponse(value=True)
        self.active_v4_device._driver_client.IsServoHasAttr = unittest.mock.MagicMock(
            return_value=response
        )

    def test_get_v4_device_info(self):
        """Test get_v4_device_info()"""
        self.active_v4_device._servod_get = unittest.mock.MagicMock(
            return_value="servo_type"
        )
        response = V4DeviceResponse(value="test_device")
        self.active_v4_device._driver_client.GetInitV4Device = unittest.mock.MagicMock(
            return_value=response
        )
        device_info = self.active_v4_device.get_v4_device_info("default")
        self.active_v4_device._servod_get.assert_called_once_with("servo_type")
        self.assertEqual(device_info, "test_device")

    def test_Set_device(self):
        """Test _Set_device()"""
        self.active_v4_device.get_v4_device_info = unittest.mock.MagicMock(
            side_effect=self.get_v4_device_info
        )
        self.active_v4_device._Get_device = unittest.mock.MagicMock(
            return_value="ccd_cr50"
        )
        self.active_v4_device._Set_device("default")
        self.active_v4_device.get_v4_device_info.assert_called()

    def test_using_ccd(self):
        """Test _using_ccd()"""
        response = BoolResponse(value=True)
        self.active_v4_device._driver_client.IsServoHasAttr = unittest.mock.MagicMock(
            return_value=response
        )
        self.active_v4_device._servod_get = unittest.mock.MagicMock(return_value="1a")
        value = self.active_v4_device._using_ccd()
        self.assertEqual(value, False)

    def test_Get_device(self):
        """Test _Get_device"""
        self.active_v4_device._using_ccd = unittest.mock.MagicMock(return_value=True)
        self.active_v4_device._servod_get = unittest.mock.MagicMock(return_value="on")
        value = self.active_v4_device._Get_device()
        self.assertEqual(value, "neither")
        self.active_v4_device._using_ccd = unittest.mock.MagicMock(return_value=False)
        self.active_v4_device._servod_get = unittest.mock.MagicMock(return_value="on")
        self.active_v4_device.get_v4_device_info = unittest.mock.MagicMock(
            side_effect=self.get_v4_device_info
        )
        value = self.active_v4_device._Get_device()
        self.assertEqual(value, "c2d2")
        self.active_v4_device._using_ccd = unittest.mock.MagicMock(return_value=False)
        self.active_v4_device._servod_get = unittest.mock.MagicMock(return_value="off")
        value = self.active_v4_device._Get_device()
        self.assertEqual(value, "neither")
        self.active_v4_device._using_ccd = unittest.mock.MagicMock(return_value=True)
        self.active_v4_device._servod_get = unittest.mock.MagicMock(return_value="off")
        value = self.active_v4_device._Get_device()
        self.assertEqual(value, "ccd_cr50")
