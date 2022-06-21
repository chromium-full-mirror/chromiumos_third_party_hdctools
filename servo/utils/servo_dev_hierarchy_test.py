# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Servo device hierarchy class tests."""

import shutil
import tempfile
import unittest

from servo import servo_dev_templates as dev_templates
from servo.utils.usb_hierarchy import Hierarchy as UsbHierarchy
from servo.utils.servo_dev_hierarchy import ServoDeviceEntry
from servo.utils.servo_dev_hierarchy import ServoDeviceHierarchy
from servo.utils.servo_dev_hierarchy import ServoDeviceHierarchyError
from servo.utils.usb_hierarchy_test import TestUsbHierarchy


class TestServoDeviceHierarchy(unittest.TestCase):
  """Tests to ensure that the ServoDeviceHierarchy works."""

  def setUp(self):
    """Setup testing by creating a mocked /sys/bus/usb/devices directory.

    This also sets up a few convenience dictionaries to create servo device
    entries in the mocked usb directory. These are called 'attrs' throughout
    the tests.
    """
    unittest.TestCase.setUp(self)
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

    self._solo_dev_attrs = {'hub_port_path': '1.2.7',
                            'devnum': 6,
                            'busnum': default_busnum,
                            'serial': 'dev-d',
                            'vid': dev_templates.ServoV2.VID,
                            'pid': dev_templates.ServoV2.PID}

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
      if TestServoDeviceHierarchy.attrs_belong_to_entry(attrs, entry):
        return True
    return False

  @staticmethod
  def get_attrs_id(attrs):
    """Return (vid, pid, serial) tuple from a attrs dict.

    Args:
      attrs: a dictionary in the style of the attrss in set_up above

    Returns:
      (vid, pid, serial) tuple from those keys in the attrs
    """
    return (attrs['vid'], attrs['pid'], attrs['serial'])

  def test_get_entry(self):
    """Assert that a properly formatted servo device entry is retrived."""
    dev_attrs = self._root_servo_dev_attrs
    TestUsbHierarchy.AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **dev_attrs)
    hierarchy = ServoDeviceHierarchy()
    devid = self.get_attrs_id(dev_attrs)
    entry = hierarchy.get_entry(*devid)
    # Assert the entry was found.
    assert entry
    assert self.attrs_belong_to_entry(dev_attrs, entry)

  def test_get_cluster(self):
    """Assert that a well formatted servo device cluster is fully retrieved."""
    TestUsbHierarchy.AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._root_servo_dev_attrs)
    TestUsbHierarchy.AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._non_root_servo_dev_1_attrs)
    TestUsbHierarchy.AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._non_root_servo_dev_2_attrs)
    hierarchy = ServoDeviceHierarchy()
    devid = self.get_attrs_id(self._root_servo_dev_attrs)
    cluster = hierarchy.get_cluster(*devid)
    # Assert the cluster was found.
    assert cluster
    # Assert the cluster has the right number of members.
    assert 3 == len(cluster)
    # Assert regardless of which member is used to index the cluster, the
    # cluster returned is always the same.
    bdevid = self.get_attrs_id(self._non_root_servo_dev_1_attrs)
    assert cluster == hierarchy.get_cluster(*bdevid)
    cdevid = self.get_attrs_id(self._non_root_servo_dev_2_attrs)
    assert cluster == hierarchy.get_cluster(*cdevid)
    # Assert Devs A, B, and C are actually the 3 devices returned.
    for attrs in [self._root_servo_dev_attrs, self._non_root_servo_dev_1_attrs,
                  self._non_root_servo_dev_2_attrs]:
      assert self.attrs_in_entries(attrs, cluster)

  def test_get_cluster_no_clusters(self):
    """get_cluster returns the device only if it's not part of a cluster."""
    TestUsbHierarchy.AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._root_servo_dev_attrs)
    TestUsbHierarchy.AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._solo_dev_attrs)
    hierarchy = ServoDeviceHierarchy()
    devid = self.get_attrs_id(self._root_servo_dev_attrs)
    cluster = hierarchy.get_cluster(*devid)
    assert cluster
    assert 1 == len(cluster)
    attrs = self._root_servo_dev_attrs
    assert self.attrs_in_entries(attrs, cluster)

  def test_get_cluster_root_servos(self):
    """get_cluster_root_servos returns all root devices in a cluster."""
    TestUsbHierarchy.AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._root_servo_dev_attrs)
    TestUsbHierarchy.AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._non_root_servo_dev_1_attrs)
    hierarchy = ServoDeviceHierarchy()
    root_servos = hierarchy.get_cluster_root_servos()
    assert root_servos
    assert 1 == len(root_servos)
    assert self.attrs_in_entries(self._root_servo_dev_attrs, root_servos)

  def test_get_cluster_root_servos_no_root_servos(self):
    """get_cluster_root_servos is [] if no root devices are in a cluster."""
    TestUsbHierarchy.AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._solo_dev_attrs)
    hierarchy = ServoDeviceHierarchy()
    root_servos = hierarchy.get_cluster_root_servos()
    # Assert that no active root_servos are reported
    assert not root_servos

  def test_get_cluster_non_root_servos(self):
    """get_cluster_non_root_servos returns all non_root_servos devices in a cluster."""
    TestUsbHierarchy.AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._root_servo_dev_attrs)
    TestUsbHierarchy.AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._non_root_servo_dev_1_attrs)
    TestUsbHierarchy.AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._non_root_servo_dev_2_attrs)
    hierarchy = ServoDeviceHierarchy()
    non_root_servos = hierarchy.get_cluster_non_root_servos()
    assert non_root_servos
    assert 2 == len(non_root_servos)
    for attrs in [self._non_root_servo_dev_2_attrs, self._non_root_servo_dev_1_attrs]:
      assert self.attrs_in_entries(attrs, non_root_servos)

  def test_get_cluster_non_root_servos_empty(self):
    """get_cluster_non_root_servos is [] if no non_root_servos devices are in a cluster."""
    TestUsbHierarchy.AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._root_servo_dev_attrs)
    hierarchy = ServoDeviceHierarchy()
    non_root_servos = hierarchy.get_cluster_non_root_servos()
    assert not non_root_servos

  def test_get_solo_devices(self):
    """get_solo_devices returns all solo devices."""
    TestUsbHierarchy.AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._root_servo_dev_attrs)
    TestUsbHierarchy.AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._solo_dev_attrs)
    hierarchy = ServoDeviceHierarchy()
    solo_devs = hierarchy.get_solo_devices()
    assert solo_devs
    assert 2 == len(solo_devs)
    for attrs in [self._root_servo_dev_attrs, self._solo_dev_attrs]:
      assert self.attrs_in_entries(attrs, solo_devs)

  def test_get_solo_devices_empty(self):
    """get_solo_devices is [] if no solo devices are found."""
    TestUsbHierarchy.AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._root_servo_dev_attrs)
    TestUsbHierarchy.AddFakeUsbEntry(usb_devices_dir=self._fake_sysfs_usb_path,
                                     **self._non_root_servo_dev_1_attrs)
    hierarchy = ServoDeviceHierarchy()
    solo_devs = hierarchy.get_solo_devices()
    assert not solo_devs


class TestServoDeviceEntry(unittest.TestCase):
  """Test ServoDeviceEntry class logic."""

  def setUp(self):
    """Setup convenience ServoDeviceEntry instances to use during testing."""
    # It is not crucial what the exact vid/pids are, they just need to be
    # from a serial servo dev template for initialization to work properly.
    unittest.TestCase.setUp(self)
    self._vid = dev_templates.ServoV2.VID
    self._pid = dev_templates.ServoV2.PID

  def test_set_cluster_root(self):
    """Setting a ServoDeviceEntry as the cluster root servo of another works."""
    test_entry = ServoDeviceEntry(vid=dev_templates.CcdCr50.VID,
                                   pid=dev_templates.CcdCr50.PID,
                                   serial='s', dev_path='a-b-c')
    test_entry2 = ServoDeviceEntry(vid=dev_templates.ServoV4.VID,
                                    pid=dev_templates.ServoV4.PID,
                                    serial='c', dev_path='1-2-3')
    test_entry.set_cluster_root(test_entry2)
    assert test_entry2 == test_entry.cluster_root

  def test_set_cluster_root_duplicate(self):
    """Setting a ServoDeviceEntry's cluster_root_servo twice raises a ServoDeviceHierarchyError."""
    test_entry = ServoDeviceEntry(vid=dev_templates.CcdCr50.VID,
                                   pid=dev_templates.CcdCr50.PID,
                                   serial='s', dev_path='a-b-c')
    test_entry2 = ServoDeviceEntry(vid=dev_templates.ServoV4.VID,
                                    pid=dev_templates.ServoV4.PID,
                                    serial='c', dev_path='1-2-3')
    test_entry3 = ServoDeviceEntry(vid=dev_templates.ServoV4.VID,
                                    pid=dev_templates.ServoV4.PID,
                                    serial='z', dev_path='i-o-p')
    test_entry.set_cluster_root(test_entry2)
    with self.assertRaisesRegex(ServoDeviceHierarchyError,
                                'A servo device entry cannot have more than '
                                'one root servo.'):
      test_entry.set_cluster_root(test_entry3)

  def test_set_cluster_root_not_hub(self):
    """Setting a ServoDeviceEntry's cluster_root_servo as a non-root-hub raises a ServoDeviceHierarchyError."""
    test_entry = ServoDeviceEntry(vid=dev_templates.CcdCr50.VID,
                                   pid=dev_templates.CcdCr50.PID,
                                   serial='s', dev_path='a-b-c')
    test_entry2 = ServoDeviceEntry(vid=dev_templates.ServoMicro.VID,
                                    pid=dev_templates.ServoMicro.PID,
                                    serial='c', dev_path='1-2-3')
    with self.assertRaisesRegex(ServoDeviceHierarchyError,
                                'because the former is not a hub servo'):
      test_entry.set_cluster_root(test_entry2)

  def test_set_cluster_root_too_many_levels(self):
    """Setting a ServoDeviceEntry's cluster with more than 2 levels raises a ServoDeviceHierarchyError."""
    test_entry = ServoDeviceEntry(vid=dev_templates.CcdCr50.VID,
                                   pid=dev_templates.CcdCr50.PID,
                                   serial='s', dev_path='a-b-c')
    test_entry2 = ServoDeviceEntry(vid=dev_templates.ServoV4.VID,
                                    pid=dev_templates.ServoV4.PID,
                                    serial='c', dev_path='1-2-3')
    test_entry3 = ServoDeviceEntry(vid=dev_templates.ServoV4.VID,
                                    pid=dev_templates.ServoV4.PID,
                                    serial='z', dev_path='i-o-p')
    test_entry4 = ServoDeviceEntry(vid=dev_templates.ServoV4.VID,
                                    pid=dev_templates.ServoV4.PID,
                                    serial='h', dev_path='x-y-z')
    test_entry2.set_cluster_root(test_entry3)
    with self.assertRaisesRegex(ServoDeviceHierarchyError,
                                'Currently servod does not support chaining '
                                '3 or more levels of servo devices'):
      test_entry.set_cluster_root(test_entry2)
    with self.assertRaisesRegex(ServoDeviceHierarchyError,
                                'Currently servod does not support chaining '
                                '3 or more levels of servo devices'):
      test_entry3.set_cluster_root(test_entry4)

  def test_validate_entry_uniqueness(self):
    """Each physical device only corresponds to a device entry."""
    test_entry = ServoDeviceEntry(vid=dev_templates.CcdCr50.VID,
                                   pid=dev_templates.CcdCr50.PID,
                                   serial='s', dev_path='a-b-c')
    test_entry2 = ServoDeviceEntry(vid=dev_templates.CcdCr50.VID,
                                   pid=dev_templates.CcdCr50.PID,
                                   serial='s', dev_path='1-2-3')
    test_entry3 = ServoDeviceEntry(vid=dev_templates.ServoV4.VID,
                                    pid=dev_templates.ServoV4.PID,
                                    serial='z', dev_path='i-o-p')
    test_entry.validate_entry_uniqueness(None)
    test_entry.validate_entry_uniqueness(test_entry)
    test_entry.validate_entry_uniqueness(test_entry3)
    with self.assertRaisesRegex(ServoDeviceHierarchyError,
                                'corresponds to 2 ServoDeviceEntry'):
      test_entry.validate_entry_uniqueness(test_entry2)

if __name__ == '__main__':
  unittest.main()