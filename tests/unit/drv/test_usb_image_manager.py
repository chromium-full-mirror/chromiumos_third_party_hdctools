# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests usbImageManager class."""

import unittest

import mock

from servo.common.interface import interface
from servo.core import servo_server
from servo.drv import hw_driver
from servo.drv import usb_image_manager


class TestUsbImageManager(unittest.TestCase):
    """
    Unit test class for usbImageManager
    Please note that this class isn't fully implemented, only the most recent changes are tested.
    """

    class InterfaceStub(interface.Interface):
        """Interface stub"""

        def __init__(self): ...

    class ServodStub(servo_server.Servod):
        """Servod stub"""

        def __init__(self): ...

    def setUp(self):
        """Set up for each test case"""
        intfc = self.InterfaceStub()
        params = {
            "cmd": "set",
            "map": "usb_key",
            "map_params": {"dut_sees_usbkey": "0", "servo_sees_usbkey": "1"},
        }
        self.usb_mgr = usb_image_manager.usbImageManager(
            ("localhost", 9999), ("localhost", 9999), intfc, params
        )

    @staticmethod
    def get_usb_to_servo_calls(usbkey_mux, usbkey_pwr):
        """Returns Expected Usb to Servo calls for Set_X_usbkey_direction functions"""
        return [
            mock.call(usbkey_pwr, "off"),
            mock.call(usbkey_mux, "servo_sees_usbkey"),
            mock.call(usbkey_pwr, "on"),
        ]

    @staticmethod
    def get_usb_to_dut_calls(usbkey_mux, usbkey_pwr):
        """Returns Expected Usb to Dut calls for Set_X_usbkey_direction functions"""
        return [
            mock.call(usbkey_pwr, "off"),
            mock.call(usbkey_mux, "dut_sees_usbkey"),
            mock.call(usbkey_pwr, "on"),
        ]

    @mock.patch(
        "servo.drv.hw_driver.HwDriver._servod_get", return_value="mock_direction"
    )
    def test_get_image_usbkey(self, servod_get_mock):
        """Test Get_image_usbkey_direction"""
        self.assertEqual(self.usb_mgr._Get_image_usbkey_direction(), "mock_direction")
        servod_get_mock.assert_called_once_with("image_usbkey_mux")

    @mock.patch(
        "servo.drv.hw_driver.HwDriver._servod_get", return_value="mock_direction"
    )
    def test_get_second_usbkey(self, servod_get_mock):
        """Test Get_second_usbkey_direction"""
        self.assertEqual(self.usb_mgr._Get_second_usbkey_direction(), "mock_direction")
        servod_get_mock.assert_called_once_with("bottom_usbkey_mux")

    @mock.patch("servo.drv.hw_driver.HwDriver._servod_set")
    @mock.patch("servo.drv.hw_driver.HwDriver._servod_get", return_value="")
    def test_set_image_usbkey_1(self, servod_get_mock, servod_set_mock):
        """Test the Set_image_usbkey_direction function with 1 as an input."""
        usb_to_servo_calls = self.get_usb_to_servo_calls(
            "image_usbkey_mux", "image_usbkey_pwr"
        )
        self.usb_mgr._Set_image_usbkey_direction(1)
        servod_set_mock.assert_has_calls(usb_to_servo_calls)

    @mock.patch("servo.drv.hw_driver.HwDriver._servod_set")
    @mock.patch("servo.drv.hw_driver.HwDriver._servod_get", return_value="")
    def test_set_second_usbkey_1(self, servod_get_mock, servod_set_mock):
        """Test the Set_second_usbkey_direction function with 1 as an input."""
        usb_to_servo_calls = self.get_usb_to_servo_calls(
            "bottom_usbkey_mux", "bottom_usbkey_pwr"
        )
        self.usb_mgr._Set_second_usbkey_direction(1)
        servod_set_mock.assert_has_calls(usb_to_servo_calls)

    @mock.patch("servo.drv.hw_driver.HwDriver._servod_set")
    @mock.patch("servo.drv.hw_driver.HwDriver._servod_get", return_value="")
    def test_set_image_usbkey_0(self, servod_get_mock, servod_set_mock):
        """Test the Set_image_usbkey_direction function with 0 as an input."""
        usb_to_dut_calls = self.get_usb_to_dut_calls(
            "image_usbkey_mux", "image_usbkey_pwr"
        )
        self.usb_mgr._Set_image_usbkey_direction(0)
        servod_set_mock.assert_has_calls(usb_to_dut_calls)

    @mock.patch("servo.drv.hw_driver.HwDriver._servod_set")
    @mock.patch("servo.drv.hw_driver.HwDriver._servod_get", return_value="")
    def test_set_second_usbkey_0(self, servod_get_mock, servod_set_mock):
        """Test the Set_second_usbkey_direction function with 0 as an input."""
        usb_to_dut_calls = self.get_usb_to_dut_calls(
            "bottom_usbkey_mux", "bottom_usbkey_pwr"
        )
        self.usb_mgr._Set_second_usbkey_direction(0)
        servod_set_mock.assert_has_calls(usb_to_dut_calls)

    @mock.patch("servo.drv.hw_driver.HwDriver._servod_set")
    @mock.patch("servo.drv.hw_driver.HwDriver._servod_get", return_value="")
    def test_set_image_usbkey_servo(self, servod_get_mock, servod_set_mock):
        """Test the Set_image_usbkey_direction function with input servo_sees_usbkey."""
        usb_to_servo_calls = self.get_usb_to_servo_calls(
            "image_usbkey_mux", "image_usbkey_pwr"
        )
        self.usb_mgr._Set_image_usbkey_direction("servo_sees_usbkey")
        servod_set_mock.assert_has_calls(usb_to_servo_calls)

    @mock.patch("servo.drv.hw_driver.HwDriver._servod_set")
    @mock.patch("servo.drv.hw_driver.HwDriver._servod_get", return_value="")
    def test_set_second_usbkey_servo(self, servod_get_mock, servod_set_mock):
        """Test the Set_second_usbkey_direction function with input servo_sees_usbkey."""
        usb_to_servo_calls = self.get_usb_to_servo_calls(
            "bottom_usbkey_mux", "bottom_usbkey_pwr"
        )
        self.usb_mgr._Set_second_usbkey_direction("servo_sees_usbkey")
        servod_set_mock.assert_has_calls(usb_to_servo_calls)

    @mock.patch("servo.drv.hw_driver.HwDriver._servod_set")
    @mock.patch("servo.drv.hw_driver.HwDriver._servod_get", return_value="")
    def test_set_image_usbkey_dut(self, servod_get_mock, servod_set_mock):
        """Test the Set_image_usbkey_direction function with input dut_sees_usbkey."""
        usb_to_dut_calls = self.get_usb_to_dut_calls(
            "image_usbkey_mux", "image_usbkey_pwr"
        )
        self.usb_mgr._Set_image_usbkey_direction("dut_sees_usbkey")
        servod_set_mock.assert_has_calls(usb_to_dut_calls)

    @mock.patch("servo.drv.hw_driver.HwDriver._servod_set")
    @mock.patch("servo.drv.hw_driver.HwDriver._servod_get", return_value="")
    def test_set_second_usbkey_dut(self, servod_get_mock, servod_set_mock):
        """Test the Set_second_usbkey_direction function with input dut_sees_usbkey."""
        usb_to_dut_calls = self.get_usb_to_dut_calls(
            "bottom_usbkey_mux", "bottom_usbkey_pwr"
        )
        self.usb_mgr._Set_second_usbkey_direction("dut_sees_usbkey")
        servod_set_mock.assert_has_calls(usb_to_dut_calls)

    def test_set_image_usbkey_dut_err(self):
        """Confirm that a bad numerical value results in an error"""
        self.assertRaises(
            usb_image_manager.UsbImageManagerError,
            self.usb_mgr._Set_image_usbkey_direction,
            2,
        )

    def test_set_second_usbkey_dut_err(self):
        """Confirm that a bad numerical value results in an error"""
        self.assertRaises(
            usb_image_manager.UsbImageManagerError,
            self.usb_mgr._Set_second_usbkey_direction,
            2,
        )

    @mock.patch("servo.drv.hw_driver.HwDriver._servod_set")
    @mock.patch(
        "servo.drv.hw_driver.HwDriver._servod_get",
        return_value="servo_sees_usbkey",
    )
    def test_set_image_usbkey_repeat(self, servod_get_mock, servod_set_mock):
        """Test that when usbkey is already set to the requested direction, then no call is made"""
        self.usb_mgr._Set_image_usbkey_direction("servo_sees_usbkey")
        assert mock.call("servo_sees_usbkey") not in servod_set_mock.mock_calls

    @mock.patch("servo.drv.hw_driver.HwDriver._servod_set")
    @mock.patch(
        "servo.drv.hw_driver.HwDriver._servod_get",
        return_value="servo_sees_usbkey",
    )
    def test_set_second_usbkey_repeat(self, servod_get_mock, servod_set_mock):
        """Test that when usbkey is already set to the requested direction, then no call is made"""
        self.usb_mgr._Set_second_usbkey_direction("servo_sees_usbkey")
        assert mock.call("servo_sees_usbkey") not in servod_set_mock.mock_calls
