# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import mock
import unittest

from mock import call
from servo.drv import hw_driver
from servo.drv import usb_image_manager
from servo.interface import interface
from servo import servo_server

class TestUsbImageManager(unittest.TestCase):
  """
  Unit test class for usbImageManager
  Please note that this class isn't fully implemented, only the most recent changes are tested.
  """
  class interface_stub(interface.Interface):
    def __init__(self):
       pass
    _logger = mock.MagicMock()

  class servod_stub(servo_server.Servod):
    def __init__(self):
       pass
    _logger = mock.MagicMock()

  # Test Init in the case that there is no map dict
  # This case happens  when a _Get/_Set function is called that lacks
  # the usbkey map param
  def test_init_empty_dict(self):
    params = {'cmd': 'set'}
    intfc = self.interface_stub()
    hw_drv = hw_driver.HwDriver(intfc, params)
    svd = self.servod_stub()
    usbMgr = usb_image_manager.usbImageManager(hw_drv, params, svd)
    self.assertEqual(None, usbMgr._MAP_DICT)

  # Test the Init function in the case that there is a map dict in the params
  def test_init_usbkey_dict(self):
    # Set up vals
    params = {'cmd': 'set', 'map':'usb_key', 'map_params': {'dut_sees_usbkey': '0', 'servo_sees_usbkey': '1'} }
    intfc = self.interface_stub()
    hw_drv = hw_driver.HwDriver(intfc, params)
    svd = self.servod_stub()
    # Run Init
    usbMgr = usb_image_manager.usbImageManager(hw_drv, params, svd)
    # Confirm resultant map dicts are set up as expected
    expected_map_dict = {'dut_sees_usbkey': '0', 'servo_sees_usbkey': '1'}
    self.assertEqual(expected_map_dict, usbMgr._MAP_DICT)
    expected_reversed = {'0': 'dut_sees_usbkey', '1': 'servo_sees_usbkey'}
    self.assertEqual(expected_reversed, usbMgr._MAP_DICT_REVERSED)

  # Test the set_image_usbkey_direction function, and ensure that it passes the desired
  # string types into _SafelySwitchMux
  @mock.patch('servo.drv.hw_driver.HwDriver._servod_set')
  @mock.patch('servo.drv.hw_driver.HwDriver._servod_get')
  @mock.patch('servo.drv.usb_image_manager.usbImageManager._SafelySwitchMux')
  def test_set_image_usbkey_direction(self, SafelySwitchMuxMock, ServodGetMock, ServodSetMock):
    # Set up vals
    intfc = self.interface_stub()
    params = {'cmd': 'set', 'map':'usb_key', 'map_params': {'dut_sees_usbkey': '0', 'servo_sees_usbkey': '1'} }
    hw_drv = hw_driver.HwDriver(intfc, params)
    svd = self.servod_stub()
    usbMgr = usb_image_manager.usbImageManager(hw_drv, params, svd)

    # Test all the different possible inputs
    usbMgr._Set_image_usbkey_direction(1)
    SafelySwitchMuxMock.assert_called_with('servo_sees_usbkey')

    usbMgr._Set_image_usbkey_direction(0)
    SafelySwitchMuxMock.assert_called_with('dut_sees_usbkey')

    usbMgr._Set_image_usbkey_direction('servo_sees_usbkey')
    SafelySwitchMuxMock.assert_called_with('servo_sees_usbkey')

    usbMgr._Set_image_usbkey_direction('dut_sees_usbkey')
    SafelySwitchMuxMock.assert_called_with('dut_sees_usbkey')

    self.assertRaises(usb_image_manager.UsbImageManagerError, usbMgr._Set_image_usbkey_direction, 2)
