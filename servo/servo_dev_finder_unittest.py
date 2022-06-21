# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Servo device finder class tests."""

import logging
import shutil
import tempfile
import unittest

from servo import servo_dev_finder as dev_finder
from servo import servo_dev_templates as dev_templates
from servo import servo_parsing
from servo.utils.usb_hierarchy import Hierarchy as UsbHierarchy
from servo.utils.servo_dev_hierarchy import ServoDeviceEntry
from servo.utils.servo_dev_hierarchy import ServoDeviceHierarchy
from servo.utils.usb_hierarchy_test import TestUsbHierarchy
from servo.utils.servo_dev_hierarchy_test import TestServoDeviceHierarchy


class TestServoDeviceFinder(unittest.TestCase):
  """Tests to ensure that the ServoDeviceFinder works."""

  def setUp(self):
    """Setup testing by creating a mocked /sys/bus/usb/devices directory.

    This also sets up a few convenience dictionaries to create servo device
    entries in the mocked usb directory. These are called 'attrs' throughout
    the tests.
    """
    unittest.TestCase.setUp(self)
    logging.disable(logging.CRITICAL)
    self._fake_sysfs_usb_path = tempfile.mkdtemp()
    UsbHierarchy.MockUsbSysfsPathForTest(self._fake_sysfs_usb_path)
    self._hierarchy = UsbHierarchy()
    default_busnum = 3
    self._root_servo_dev_attrs = {'hub_port_path': '1.1.1',
                                'devnum': 3,
                                'busnum': default_busnum,
                                'serial': 'dev-a',
                                'vid': dev_templates.ServoV4.VID,
                                'pid': dev_templates.ServoV4.PID}
    self._non_root_servo_dev_1_attrs = {'hub_port_path': '1.1.2',
                                   'devnum': 4,
                                   'busnum': default_busnum,
                                   'serial': 'dev-b',
                                   'vid': dev_templates.ServoMicro.VID,
                                   'pid': dev_templates.ServoMicro.PID}

    self._non_root_servo_dev_2_attrs = {'hub_port_path': '1.1.3',
                                   'devnum': 5,
                                   'busnum': default_busnum,
                                   'serial': 'dev-c',
                                   'vid': dev_templates.ServoMicro.VID,
                                   'pid': dev_templates.ServoMicro.PID}
    self._non_root_servo_dev_3_attrs = {'hub_port_path': '1.1.4.1',
                                   'devnum': 6,
                                   'busnum': default_busnum,
                                   'serial': 'dev-d',
                                   'vid': dev_templates.ServoV4.VID,
                                   'pid': dev_templates.ServoV4.PID}
    self._solo_dev_attrs = {'hub_port_path': '1.2.7',
                            'devnum': 8,
                            'busnum': default_busnum,
                            'serial': 'dev-f',
                            'vid': dev_templates.ServoV2.VID,
                            'pid': dev_templates.ServoV2.PID}

  def tearDown(self):
    """Remove /sys/bus/usb/devices mocking & destroy temp directory."""
    shutil.rmtree(self._fake_sysfs_usb_path)
    UsbHierarchy.RestoreDefaultUsbSysfsPathForTest()
    unittest.TestCase.tearDown(self)

  def test_complete_servod_device_list_complete_cluster(self):
    """Test servod device list is completed and the device does not contain partial clusters."""
    TestUsbHierarchy.AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._root_servo_dev_attrs)
    TestUsbHierarchy.AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._non_root_servo_dev_1_attrs)
    TestUsbHierarchy.AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._non_root_servo_dev_3_attrs)
    hierarchy = ServoDeviceHierarchy()
    devopts = servo_parsing.empty_devopts()
    devopts.vendor = None
    devopts.product = None
    devopts.serialname = None
    entries = dev_finder.complete_servod_device_list([devopts], hierarchy, True)
    assert 3 == len(entries)
    for attrs in [self._root_servo_dev_attrs, self._non_root_servo_dev_1_attrs,
                  self._non_root_servo_dev_3_attrs]:
      assert TestServoDeviceHierarchy.attrs_in_entries(attrs, entries)

  def test_complete_servod_device_list_incomplete_cluster(self):
    """Test servod device list is completed and the device does not contain partial clusters."""
    TestUsbHierarchy.AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._root_servo_dev_attrs)
    TestUsbHierarchy.AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._non_root_servo_dev_1_attrs)
    TestUsbHierarchy.AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._non_root_servo_dev_3_attrs)
    TestUsbHierarchy.AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._solo_dev_attrs)
    hierarchy = ServoDeviceHierarchy()
    devopts = servo_parsing.empty_devopts()
    devopts.vendor = dev_templates.ServoMicro.VID
    devopts.product = dev_templates.ServoMicro.PID
    devopts.serialname = None
    entries = dev_finder.complete_servod_device_list([devopts], hierarchy, False)
    assert 2 == len(entries)
    for attrs in [self._root_servo_dev_attrs, self._non_root_servo_dev_1_attrs]:
      assert TestServoDeviceHierarchy.attrs_in_entries(attrs, entries)

  def test_complete_servod_device_list_solo_device(self):
    """Test servod device list is completed and the device does not contain partial clusters."""
    TestUsbHierarchy.AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._root_servo_dev_attrs)
    TestUsbHierarchy.AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._non_root_servo_dev_1_attrs)
    TestUsbHierarchy.AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._non_root_servo_dev_3_attrs)
    TestUsbHierarchy.AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._solo_dev_attrs)
    hierarchy = ServoDeviceHierarchy()
    devopts = servo_parsing.empty_devopts()
    devopts.vendor = dev_templates.ServoV2.VID
    devopts.product = dev_templates.ServoV2.PID
    devopts.serialname = None
    entries = dev_finder.complete_servod_device_list([devopts], hierarchy, False)
    assert 1 == len(entries)
    assert TestServoDeviceHierarchy.attrs_belong_to_entry(self._solo_dev_attrs, entries[0])

  def test_complete_servod_device_list_multiple_devices(self):
    """Test servod device list is completed and the device does not contain partial clusters."""
    TestUsbHierarchy.AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._root_servo_dev_attrs)
    TestUsbHierarchy.AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._non_root_servo_dev_1_attrs)
    TestUsbHierarchy.AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._non_root_servo_dev_2_attrs)
    hierarchy = ServoDeviceHierarchy()
    devopts = servo_parsing.empty_devopts()
    devopts.vendor = None
    devopts.product = None
    devopts.serialname = None
    with self.assertRaises(SystemExit) as cm:
      entries = dev_finder.complete_servod_device_list([devopts], hierarchy, True)
    self.assertEqual(cm.exception.code, 1)

  def test_complete_servod_device_list_no_device(self):
    """Test servod device list is completed and the device does not contain partial clusters."""
    hierarchy = ServoDeviceHierarchy()
    devopts = servo_parsing.empty_devopts()
    devopts.vendor = None
    devopts.product = None
    devopts.serialname = None
    with self.assertRaises(SystemExit) as cm:
      entries = dev_finder.complete_servod_device_list([devopts], hierarchy, True)
    self.assertEqual(cm.exception.code, 1)

if __name__ == '__main__':
  unittest.main()