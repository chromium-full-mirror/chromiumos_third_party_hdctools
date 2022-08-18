# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Servo device finder class tests."""

import logging
import os
import shutil
import tempfile
import unittest

from servo import servo_dev_finder as dev_finder
from servo import servo_dev_templates as dev_templates
from servo import servo_parsing
from servo.servo_dev_finder import ServoDeviceFinderError
from servo.utils.usb_hierarchy import Hierarchy as UsbHierarchy
from servo.utils.scratch import Scratch
from servo.utils.servo_dev_hierarchy import ServoDeviceEntry
from servo.utils.servo_dev_hierarchy import ServoDeviceHierarchy

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
    self._dummy_choose_device = lambda devs: None

  def tearDown(self):
    """Remove /sys/bus/usb/devices mocking & destroy temp directory."""
    shutil.rmtree(self._fake_sysfs_usb_path)
    UsbHierarchy.RestoreDefaultUsbSysfsPathForTest()
    unittest.TestCase.tearDown(self)

  @staticmethod
  def attrs_belong_to_entry(attrs, entry):
    """Assert that a attrs dict has the same values as a ServoDeviceEntry.

    Args:
      attrs: a dictionary in the style of the attrss in set_up above
      entry: a ServoDeviceEntry object

    Returns:
      True if the attrs's vid/pid/serial match the entry's vid, pid, serial
    """
    return (entry.vid == attrs['vid'] and entry.pid == attrs['pid'] and
            entry.serial == attrs['serial'])

  @staticmethod
  def attrs_in_entries(attrs, entries):
    """Assert that a attrs dict matches a ServoDeviceEntry in |entries|.

    Args:
      attrs: a dictionary in the style of the attrss in set_up above
      entries: a collection ServoDeviceEntry object

    Returns:
      True if the attrs and a entry in entries return True for
      attrs_belong_to_entry False otherwise
    """
    for entry in entries:
      if TestServoDeviceFinder.attrs_belong_to_entry(attrs, entry):
        return True
    return False

  def test_discover_servos_complete_cluster(self):
    """Test servod device list is completed and the device list does not contain partial clusters."""
    AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._root_servo_dev_attrs)
    AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._non_root_servo_dev_1_attrs)
    AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._non_root_servo_dev_3_attrs)
    hierarchy = ServoDeviceHierarchy()
    devopts = servo_parsing.empty_devopts()
    devopts.vendor = None
    devopts.product = None
    devopts.serialname = None
    finder = dev_finder.ServoDeviceFinder([devopts], hierarchy, Scratch(), self._dummy_choose_device)
    entries = finder.discover_servos(True)
    assert 3 == len(entries)
    for attrs in [self._root_servo_dev_attrs, self._non_root_servo_dev_1_attrs,
                  self._non_root_servo_dev_3_attrs]:
      assert self.attrs_in_entries(attrs, entries)

  def test_discover_servos_incomplete_cluster(self):
    """Test servod device list is completed and the device list can contain partial clusters."""
    AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._root_servo_dev_attrs)
    AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._non_root_servo_dev_1_attrs)
    AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._non_root_servo_dev_3_attrs)
    AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._solo_dev_attrs)
    hierarchy = ServoDeviceHierarchy()
    devopts = servo_parsing.empty_devopts()
    devopts.vendor = dev_templates.ServoMicro.VID
    devopts.product = dev_templates.ServoMicro.PID
    devopts.serialname = None
    finder = dev_finder.ServoDeviceFinder([devopts], hierarchy, Scratch(), self._dummy_choose_device)
    entries = finder.discover_servos(False)
    assert 2 == len(entries)
    for attrs in [self._root_servo_dev_attrs, self._non_root_servo_dev_1_attrs]:
      assert self.attrs_in_entries(attrs, entries)

  def test_discover_servos_solo_device(self):
    """Test servod device list is completed for a solo device."""
    AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._root_servo_dev_attrs)
    AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._non_root_servo_dev_1_attrs)
    AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._non_root_servo_dev_3_attrs)
    AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._solo_dev_attrs)
    hierarchy = ServoDeviceHierarchy()
    devopts = servo_parsing.empty_devopts()
    devopts.vendor = dev_templates.ServoV2.VID
    devopts.product = dev_templates.ServoV2.PID
    devopts.serialname = None
    finder = dev_finder.ServoDeviceFinder([devopts], hierarchy, Scratch(), self._dummy_choose_device)
    entries = finder.discover_servos(False)
    assert 1 == len(entries)
    assert self.attrs_belong_to_entry(self._solo_dev_attrs, entries[0])

  def test_discover_servos_multiple_devices(self):
    """Test discover_servos error out when there are multiple devices matched with invocation
    arguments and user specifies which device they want through the interative menu."""
    AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._root_servo_dev_attrs)
    AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._non_root_servo_dev_1_attrs)
    AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._non_root_servo_dev_2_attrs)
    hierarchy = ServoDeviceHierarchy()
    devopts = servo_parsing.empty_devopts()
    devopts.vendor = None
    devopts.product = None
    devopts.serialname = None
    _non_root_servo_dev_1_entry = hierarchy.get_entry(dev_templates.ServoMicro.VID,
                                            dev_templates.ServoMicro.PID, 'dev-b')
    finder = dev_finder.ServoDeviceFinder([devopts], hierarchy, Scratch(),
      lambda devs: _non_root_servo_dev_1_entry)
    entries = finder.discover_servos(True)
    assert 3 == len(entries)
    for attrs in [self._root_servo_dev_attrs, self._non_root_servo_dev_1_attrs,
                  self._non_root_servo_dev_2_attrs]:
      assert self.attrs_in_entries(attrs, entries)

  def test_discover_servos_multiple_devices_no_user_input(self):
    """Test discover_servos error out when there are multiple devices matched with invocation
    arguments but user does not choose what they mean through the interative menu."""
    AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._root_servo_dev_attrs)
    AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._non_root_servo_dev_1_attrs)
    AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._non_root_servo_dev_2_attrs)
    hierarchy = ServoDeviceHierarchy()
    devopts = servo_parsing.empty_devopts()
    devopts.vendor = None
    devopts.product = None
    devopts.serialname = None
    finder = dev_finder.ServoDeviceFinder([devopts], hierarchy, Scratch(), self._dummy_choose_device)
    with self.assertRaisesRegex(ServoDeviceFinderError,
      'User does not choose a valid device for'):
      entries = finder.discover_servos(True)

  def test_discover_servos_no_device(self):
    """Test discover_servos error out when there are no devices connected."""
    hierarchy = ServoDeviceHierarchy()
    devopts = servo_parsing.empty_devopts()
    devopts.vendor = None
    devopts.product = None
    devopts.serialname = None
    finder = dev_finder.ServoDeviceFinder([devopts], hierarchy, Scratch(), self._dummy_choose_device)
    with self.assertRaisesRegex(ServoDeviceFinderError,
      'Cannot find a servo device with'):
      entries = finder.discover_servos(True)

  def test_choose_main_device_1_user_main(self):
    """Test choose_main_device return the only main device chosen by the user."""
    test_entry = ServoDeviceEntry(vid=dev_templates.ServoMicro.VID,
                                   pid=dev_templates.ServoMicro.PID,
                                   serial='s', dev_path='a-b-c')
    test_entry.devopts.prefix = ''
    test_entry2 = ServoDeviceEntry(vid=dev_templates.C2d2.VID,
                                   pid=dev_templates.C2d2.PID,
                                   serial='s', dev_path='1-2-3')
    devs = [test_entry, test_entry2]
    hierarchy = ServoDeviceHierarchy()
    devopts = servo_parsing.empty_devopts()
    finder = dev_finder.ServoDeviceFinder([devopts], hierarchy, Scratch(), self._dummy_choose_device)
    main = finder.choose_main_device(devs)
    assert main == test_entry

  def test_choose_main_device_multiple_user_main_no_user_input(self):
    """Test choose_main_device ask for user input if user choose multiple main devices during
    servod invocation."""
    """Test choose_main_device return the only main device chosen by the user."""
    test_entry = ServoDeviceEntry(vid=dev_templates.ServoMicro.VID,
                                   pid=dev_templates.ServoMicro.PID,
                                   serial='s', dev_path='a-b-c')
    test_entry.devopts.prefix = ''
    test_entry2 = ServoDeviceEntry(vid=dev_templates.C2d2.VID,
                                   pid=dev_templates.C2d2.PID,
                                   serial='s', dev_path='1-2-3')
    test_entry2.devopts.prefix = ''
    devs = [test_entry, test_entry2]
    hierarchy = ServoDeviceHierarchy()
    devopts = servo_parsing.empty_devopts()
    finder = dev_finder.ServoDeviceFinder([devopts], hierarchy, Scratch(), lambda devs: test_entry)
    main = finder.choose_main_device(devs)
    assert main == test_entry

  def test_choose_main_device_multiple_user_main_no_user_input(self):
    """Test choose_main_device ask for user input if user choose multiple main devices during
    servod invocation. Error out if user does not provide any input."""
    """Test choose_main_device return the only main device chosen by the user."""
    test_entry = ServoDeviceEntry(vid=dev_templates.ServoMicro.VID,
                                   pid=dev_templates.ServoMicro.PID,
                                   serial='s', dev_path='a-b-c')
    test_entry.devopts.prefix = ''
    test_entry2 = ServoDeviceEntry(vid=dev_templates.C2d2.VID,
                                   pid=dev_templates.C2d2.PID,
                                   serial='s', dev_path='1-2-3')
    test_entry2.devopts.prefix = ''
    devs = [test_entry, test_entry2]
    hierarchy = ServoDeviceHierarchy()
    devopts = servo_parsing.empty_devopts()
    finder = dev_finder.ServoDeviceFinder([devopts], hierarchy, Scratch(), self._dummy_choose_device)
    with self.assertRaisesRegex(ServoDeviceFinderError,
      'No device is picked as the main device'):
      main = finder.choose_main_device(devs)

  def test_choose_main_device_no_user_main(self):
    """Test choose_main_device smartly choose a main device when user does not choose one."""
    test_entry = ServoDeviceEntry(vid=dev_templates.ServoMicro.VID,
                                   pid=dev_templates.ServoMicro.PID,
                                   serial='s', dev_path='a-b-c')
    test_entry2 = ServoDeviceEntry(vid=dev_templates.Sweetberry.VID,
                                   pid=dev_templates.Sweetberry.PID,
                                   serial='s', dev_path='1-2-3')
    devs = [test_entry, test_entry2]
    hierarchy = ServoDeviceHierarchy()
    devopts = servo_parsing.empty_devopts()
    finder = dev_finder.ServoDeviceFinder([devopts], hierarchy, Scratch(), self._dummy_choose_device)
    main = finder.choose_main_device(devs)
    assert main == test_entry

  def test_choose_main_device_multiple_candidates(self):
    """Test choose_main_device tries smartly choose a main device, but there are multiple
    candidates so user still needs to manually choose one."""
    test_entry = ServoDeviceEntry(vid=dev_templates.ServoMicro.VID,
                                   pid=dev_templates.ServoMicro.PID,
                                   serial='s', dev_path='a-b-c')
    test_entry2 = ServoDeviceEntry(vid=dev_templates.C2d2.VID,
                                   pid=dev_templates.C2d2.PID,
                                   serial='s', dev_path='1-2-3')
    devs = [test_entry, test_entry2]
    hierarchy = ServoDeviceHierarchy()
    devopts = servo_parsing.empty_devopts()
    finder = dev_finder.ServoDeviceFinder([devopts], hierarchy, Scratch(), lambda devs: test_entry)
    main = finder.choose_main_device(devs)
    assert main == test_entry

  def test_choose_main_device_multiple_candidates_no_user_input(self):
    """Test choose_main_device smartly choose a main device when user does not choose one
    and there are multiple candidates, but user does not choose one from the candidates."""
    test_entry = ServoDeviceEntry(vid=dev_templates.ServoMicro.VID,
                                   pid=dev_templates.ServoMicro.PID,
                                   serial='s', dev_path='a-b-c')
    test_entry2 = ServoDeviceEntry(vid=dev_templates.C2d2.VID,
                                   pid=dev_templates.C2d2.PID,
                                   serial='s', dev_path='1-2-3')
    devs = [test_entry, test_entry2]
    hierarchy = ServoDeviceHierarchy()
    devopts = servo_parsing.empty_devopts()
    finder = dev_finder.ServoDeviceFinder([devopts], hierarchy, Scratch(), self._dummy_choose_device)
    with self.assertRaisesRegex(ServoDeviceFinderError,
      'No device is picked as the main device'):
      main = finder.choose_main_device(devs)

  def test_generate_prefixes_main_device(self):
    """Test generate_prefixes generate correct prefixes for the main device and non-main devices."""
    test_entry = ServoDeviceEntry(vid=dev_templates.ServoMicro.VID,
                                   pid=dev_templates.ServoMicro.PID,
                                   serial='s', dev_path='a-b-c')
    test_entry2 = ServoDeviceEntry(vid=dev_templates.ServoV4.VID,
                                   pid=dev_templates.ServoV4.PID,
                                   serial='s', dev_path='1-2-3')
    devs = [test_entry, test_entry2]
    hierarchy = ServoDeviceHierarchy()
    devopts = servo_parsing.empty_devopts()
    finder = dev_finder.ServoDeviceFinder([devopts], hierarchy, Scratch(), self._dummy_choose_device)
    test_entry.devopts.prefix = None
    test_entry2.devopts.prefix = dev_templates.MAIN_DEV_PREFIX

    finder.generate_prefixes(devs, test_entry)
    assert test_entry.devopts.prefix == dev_templates.MAIN_DEV_PREFIX
    assert test_entry2.devopts.prefix == 'servo_v4'

  def test_generate_prefixes_auto_generation(self):
    """Test generate_prefixes auto generate prefixes for devices."""
    test_entry = ServoDeviceEntry(vid=dev_templates.ServoMicro.VID,
                                   pid=dev_templates.ServoMicro.PID,
                                   serial='s', dev_path='a-b-c')
    test_entry2 = ServoDeviceEntry(vid=dev_templates.ServoMicro.VID,
                                   pid=dev_templates.ServoMicro.PID,
                                   serial='s', dev_path='a-b-c')
    test_entry3 = ServoDeviceEntry(vid=dev_templates.ServoV4.VID,
                                   pid=dev_templates.ServoV4.PID,
                                   serial='4321', dev_path='1-2-3')
    test_entry4 = ServoDeviceEntry(vid=dev_templates.ServoV4.VID,
                                   pid=dev_templates.ServoV4.PID,
                                   serial='11234', dev_path='1-2-3')
    test_entry5 = ServoDeviceEntry(vid=dev_templates.ServoV4.VID,
                                   pid=dev_templates.ServoV4.PID,
                                   serial='21234', dev_path='1-2-3')
    devs = [test_entry, test_entry2, test_entry3, test_entry4, test_entry5]
    hierarchy = ServoDeviceHierarchy()
    devopts = servo_parsing.empty_devopts()
    finder = dev_finder.ServoDeviceFinder([devopts], hierarchy, Scratch(), self._dummy_choose_device)
    test_entry3.devopts.prefix = 'servo_v4-1234'

    finder.generate_prefixes(devs, test_entry)
    assert test_entry.devopts.prefix == dev_templates.MAIN_DEV_PREFIX
    assert test_entry2.devopts.prefix == 'servo_micro'
    assert test_entry3.devopts.prefix == 'servo_v4-1234'
    assert test_entry4.devopts.prefix == 'servo_v4-1234-2'
    assert test_entry5.devopts.prefix == 'servo_v4-1234-3'

  def test_validate_devopts_no_prefix(self):
    """Test validate_devopts error out when a device does not have a prefix"""
    test_entry = ServoDeviceEntry(vid=dev_templates.ServoV4.VID,
                                   pid=dev_templates.ServoV4.PID,
                                   serial='s', dev_path='a-b-c')
    hierarchy = ServoDeviceHierarchy()
    devopts = servo_parsing.empty_devopts()
    finder = dev_finder.ServoDeviceFinder([devopts], hierarchy, Scratch(), self._dummy_choose_device)
    with self.assertRaisesRegex(ServoDeviceFinderError, 'does not have a prefix'):
      main = finder.validate_devopts([test_entry])

  def test_validate_devopts_multiple_main_devices(self):
    """Test validate_devopts error out if there are multiple devices chosen as the main device."""
    test_entry = ServoDeviceEntry(vid=dev_templates.ServoV4.VID,
                                   pid=dev_templates.ServoV4.PID,
                                   serial='s', dev_path='a-b-c')
    test_entry2 = ServoDeviceEntry(vid=dev_templates.ServoV4.VID,
                                   pid=dev_templates.ServoV4.PID,
                                   serial='s2', dev_path='a-b-c')
    test_entry.devopts.prefix = ''
    test_entry2.devopts.prefix = ''
    hierarchy = ServoDeviceHierarchy()
    devopts = servo_parsing.empty_devopts()
    finder = dev_finder.ServoDeviceFinder([devopts], hierarchy, Scratch(), self._dummy_choose_device)
    with self.assertRaisesRegex(ServoDeviceFinderError,
      'Multiple devices are chosen as the main device.'):
      main = finder.validate_devopts([test_entry, test_entry2])

  def test_validate_device_availability(self):
    """Test validate_device_availability error out when some device is not available."""
    test_entry = ServoDeviceEntry(vid=dev_templates.ServoV4.VID,
                                   pid=dev_templates.ServoV4.PID,
                                   serial='s', dev_path='a-b-c')
    test_entry2 = ServoDeviceEntry(vid=dev_templates.ServoMicro.VID,
                                   pid=dev_templates.ServoMicro.PID,
                                   serial='s2', dev_path='e-f-g')
    hierarchy = ServoDeviceHierarchy()
    devopts = servo_parsing.empty_devopts()
    finder = dev_finder.ServoDeviceFinder([devopts], hierarchy, MockScratch(), self._dummy_choose_device)
    with self.assertRaisesRegex(ServoDeviceFinderError,
      'Not all devices requested are available right now.'):
      main = finder.validate_device_availability([test_entry, test_entry2])

class MockScratch(Scratch):
  def GetAllEntries(self):
    return [{"serials": ["s"], "port": 9999}, {"serials": ["s2"], "port": 9998}]

def AddFakeUsbEntry(usb_devices_dir, hub_port_path, root_hub=2, devnum=None,
                    busnum=None, serial=None, vid=None, pid=None):
  """Helper to add a fake sysfs-like device file for a usb device.

  Args:
    usb_devices_dir: directory mocking /sys/bus/usb/devices
    hub_port_path: the 'x.x.x' port path of the device on the root hub
    root_hub: the usb root hub number
    devnum: content for the dev-num file. File not created if ommited
    busnum: content for the bus-num file. File not created if ommited
    serial: content for the serial file. File not created if ommited
    vid: content for the idVendor file. File not created if ommited
    pid: content for the idProduct file. File not created if ommited

  Returns:
    devdir: directory in |usb_devices_dir| that was created
  """
  dev_dir_path = '%d-%s' % (root_hub, hub_port_path)
  dev_dir_path_full = os.path.join(usb_devices_dir, dev_dir_path)
  # Create the fake device path entry
  os.mkdir(dev_dir_path_full)
  # Create a file for each attribute that is present
  for attr, attr_file, fmt in [(devnum, UsbHierarchy.DEV_FILE, 'd'),
                               (busnum, UsbHierarchy.BUS_FILE, 'd'),
                               (vid, UsbHierarchy.VID_FILE, 'x'),
                               (pid, UsbHierarchy.PID_FILE, 'x'),
                               (serial, UsbHierarchy.SERIAL_FILE, 's')]:
    if attr:
      attr_path = os.path.join(dev_dir_path_full, attr_file)
      with open(attr_path, 'w') as f:
        f.write(format(attr, fmt))
  return dev_dir_path_full

if __name__ == '__main__':
  unittest.main()
