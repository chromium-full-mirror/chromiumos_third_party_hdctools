# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# pylint: disable=unsubscriptable-object, unused-argument

"""USB hierarchy class tests for both the pyusb wrappers and sysfs functions."""

import os
import shutil
import tempfile
import unittest

import pytest
import usb

from servo.utils.usb_hierarchy import Hierarchy
from servo.utils.usb_hierarchy import HierarchyError


class TestUsbHierarchy(unittest.TestCase):
    """Test UsbHierarchy code logic."""

    class FakePyUSBCoreDevice:
        """Fake usb.core.Device object exposing dev/bus num to test interaction."""

        def __init__(self, busnum, devnum):
            """Initialize fake device.

            Args:
              busnum: bus num for device
              devnum: dev num for device
            """
            self.bus = busnum
            self.address = devnum

    def setUp(self):
        """Setup testing by creating a mocked /sys/bus/usb/devices  .

        This also sets up a few convenience objects and values to mock usb devices
        for the tests below.
        """
        unittest.TestCase.setUp(self)
        self._usb_dir = tempfile.mkdtemp()
        # This ensures that UsbHierarchy will use |_fake_sysfs_usb_path|.
        Hierarchy.mock_usb_sysfs_path_for_test(self._usb_dir)
        self._hierarchy = Hierarchy()
        # The default values to use to mock a sysfs entry
        self._busnum = 2
        self._devnum = 89
        self._vid = 0x91
        self._pid = 0x81
        self._serial = "serial"
        self._hub_port_path = "1.1.1"
        # Create a fake libusb device (only bus & devnum needed) to index hierarchy.
        dev = TestUsbHierarchy.FakePyUSBCoreDevice(
            busnum=self._busnum, devnum=self._devnum
        )
        self._fake_dev = dev

    def tearDown(self):
        """Remove /sys/bus/usb/devices mocking & destroy temp directory."""
        shutil.rmtree(self._usb_dir)
        Hierarchy.restore_default_usb_sysfs_path_for_test()
        unittest.TestCase.tearDown(self)

    def test_find_conforming_usb_device(self):
        """Find a conforming usb device in the UsbHierarchy."""
        # Add a fake entry with all attributes
        add_fake_usb_entry(
            usb_devices_dir=self._usb_dir,
            hub_port_path=self._hub_port_path,
            devnum=self._devnum,
            busnum=self._busnum,
            serial=self._serial,
            vid=self._vid,
            pid=self._pid,
        )
        # This should now recognize the device.
        self._hierarchy.refresh_hierarchy()
        # Assert that there is only one entry
        assert len(self._hierarchy.hierarchy) == 1
        # Assert that the entry corresponds to the fake device added above by
        dev_path = self._hierarchy.get_dev_port_path(self._fake_dev)
        assert dev_path
        assert dev_path.endswith(self._hub_port_path)

    def test_skip_usb_device_missing_busnum(self):
        """A device missing a busnum file is skipped in the UsbHierarchy."""
        # Add a fake entry with all attributes, expect busnum
        add_fake_usb_entry(
            usb_devices_dir=self._usb_dir,
            hub_port_path=self._hub_port_path,
            devnum=self._devnum,
            serial=self._serial,
            vid=self._vid,
            pid=self._pid,
        )
        # This should now recognize the device.
        self._hierarchy.refresh_hierarchy()
        # Assert that there is no entry, as this entry should have been skipped
        assert not self._hierarchy.hierarchy

    def test_skip_usb_device_missing_devnum(self):
        """A device missing a devnum file is skipped in the UsbHierarchy."""
        # Add a fake entry with all attributes, expect devnum
        add_fake_usb_entry(
            usb_devices_dir=self._usb_dir,
            hub_port_path=self._hub_port_path,
            busnum=self._busnum,
            serial=self._serial,
            vid=self._vid,
            pid=self._pid,
        )
        # This should now recognize the device.
        self._hierarchy.refresh_hierarchy()
        # Assert that there is no entry, as this entry should have been skipped
        assert not self._hierarchy.hierarchy

    def test_no_skip_usb_device_missing_other_descriptors(self):
        """A device with bus/devnum is added even when lacking other descriptors."""
        # Add a fake entry with no attributes, expect devnum and busnum
        add_fake_usb_entry(
            usb_devices_dir=self._usb_dir,
            hub_port_path=self._hub_port_path,
            devnum=self._devnum,
            busnum=self._busnum,
        )
        # This should now recognize the device, as those two are the only required
        # ones to be index.
        self._hierarchy.refresh_hierarchy()
        # Assert that there is one entry
        assert len(self._hierarchy.hierarchy) == 1
        # Assert that the entry corresponds to the fake device added above by
        dev_path = self._hierarchy.get_dev_port_path(self._fake_dev)
        assert dev_path
        assert dev_path.endswith(self._hub_port_path)

    def test_get_all_usb_device_sysfs_paths(self):
        """Verify we retrieve all devices conforming to vid/pid pairs."""
        # Add 3 distinct devices that all have the same vid/pid
        devices = 3
        for extra in range(devices):
            port_path = self._hub_port_path + ".%s" % str(extra)
            serial = self._serial + str(extra)
            devnum = self._devnum + extra
            add_fake_usb_entry(
                usb_devices_dir=self._usb_dir,
                hub_port_path=port_path,
                busnum=self._busnum,
                devnum=devnum,
                serial=serial,
                vid=self._vid,
                pid=self._pid,
            )
        # Ensure all devices are found when supplying the vid/pid
        vid_pid_list = [(self._vid, self._pid)]
        assert len(Hierarchy.get_all_usb_device_sysfs_paths(vid_pid_list)) == devices

    def test_get_all_usb_device_sysfs_paths_no_list(self):
        """Verify we retrieve all devices if no filters provided."""
        devices = 5
        for extra in range(devices):
            # each device here will have a different vid, with one of them
            # being the default_vid
            port_path = self._hub_port_path + ".%s" % str(extra)
            serial = self._serial + str(extra)
            devnum = self._devnum + extra
            vid = self._vid + extra
            pid = self._pid + extra
            add_fake_usb_entry(
                usb_devices_dir=self._usb_dir,
                hub_port_path=port_path,
                busnum=self._busnum,
                devnum=devnum,
                serial=serial,
                vid=vid,
                pid=pid,
            )
        vid_pid_list = [(self._vid, self._pid)]
        # This is to ensure that only one device is actually found
        assert len(Hierarchy.get_all_usb_device_sysfs_paths(vid_pid_list)) == 1
        # This is to ensure that once the filters are all lifted, all devices
        # are found.
        assert len(Hierarchy.get_all_usb_device_sysfs_paths()) == devices

    def test_get_all_usb_device_sysfs_paths_pid_wildcard(self):
        """Verify we retrieve all devices when pid is a wildcard."""
        devices = 5
        for extra in range(devices):
            # each device here will have a different pid, with one of them
            # being the default_pid
            port_path = self._hub_port_path + ".%s" % str(extra)
            serial = self._serial + str(extra)
            devnum = self._devnum + extra
            pid = self._pid + extra
            add_fake_usb_entry(
                usb_devices_dir=self._usb_dir,
                hub_port_path=port_path,
                busnum=self._busnum,
                devnum=devnum,
                serial=serial,
                vid=self._vid,
                pid=pid,
            )
        vid_pid_list = [(self._vid, self._pid)]
        # This is to ensure that only one device is actually found
        assert len(Hierarchy.get_all_usb_device_sysfs_paths(vid_pid_list)) == 1
        # This is to ensure that once we lift the restriction on pid i.e. it's
        # a wildcard, all devices are found again
        vid_pid_list = [(self._vid, None)]
        assert len(Hierarchy.get_all_usb_device_sysfs_paths(vid_pid_list)) == devices

    def test_get_usb_device_sysfs_path(self):
        """Verify retrieving the sysfs directory path works as expected."""
        add_fake_usb_entry(
            usb_devices_dir=self._usb_dir,
            hub_port_path=self._hub_port_path,
            devnum=self._devnum,
            busnum=self._busnum,
            vid=self._vid,
            pid=self._pid,
            serial=self._serial,
        )
        vid, pid, sid = self._vid, self._pid, self._serial
        dev_path = Hierarchy.get_usb_device_sysfs_path(vid=vid, pid=pid, serial=sid)
        # Assert on an existing device that the path exists.
        assert os.path.exists(dev_path)
        # Assert if the device does not exist, that None is returned.
        dev_path = Hierarchy.get_usb_device_sysfs_path(vid=vid, pid=pid, serial="fake")
        assert dev_path is None

    def test_get_usb_device_sysfs_path_no_serial_no_error(self):
        """Verify missing 'serial' file does not throw error."""
        # Skip adding serial file.
        add_fake_usb_entry(
            usb_devices_dir=self._usb_dir,
            hub_port_path=self._hub_port_path,
            devnum=self._devnum,
            busnum=self._busnum,
            vid=self._vid,
            pid=self._pid,
        )
        vid, pid, sid = self._vid, self._pid, self._serial
        dev_path = Hierarchy.get_usb_device_sysfs_path(vid=vid, pid=pid, serial=sid)
        assert dev_path is None

    def test_get_usb_device_sysfs_path_multiple_vid_pid_serial_fails(self):
        """Verify that more than one vid:pid serial pair throws an error."""
        add_fake_usb_entry(
            usb_devices_dir=self._usb_dir,
            hub_port_path=self._hub_port_path,
            devnum=self._devnum,
            busnum=self._busnum,
            vid=self._vid,
            pid=self._pid,
            serial=self._serial,
        )
        # Edit the dev-port path and the dev-num so that two entries are added.
        add_fake_usb_entry(
            usb_devices_dir=self._usb_dir,
            hub_port_path="1.1.2",
            devnum=self._devnum + 1,
            busnum=self._busnum,
            vid=self._vid,
            pid=self._pid,
            serial=self._serial,
        )
        vid, pid, sid = self._vid, self._pid, self._serial
        with self.assertRaisesRegex(HierarchyError, "Found 2 devices with"):
            _unused = Hierarchy.get_usb_device_sysfs_path(vid=vid, pid=pid, serial=sid)

    def test_get_dev_port_path(self):
        """Retrieving the /sys/bus/usb/devices path for a device works."""
        # Define own root hub number instead of using default to verify path name.
        root_hub = 3
        # Add a fake entry with minimum necessary attributes to be a valid entry
        add_fake_usb_entry(
            usb_devices_dir=self._usb_dir,
            root_hub=root_hub,
            hub_port_path=self._hub_port_path,
            devnum=self._devnum,
            busnum=self._busnum,
        )
        self._hierarchy.refresh_hierarchy()
        dev_path = self._hierarchy.get_dev_port_path(self._fake_dev)
        # The usb device's dirname is <root-hub>-<port-hub>[.<port-hub>]*
        expected_dev_dir = "%s-%s" % (root_hub, self._hub_port_path)
        # The entire sysfs path is the sysfs directory used (here mocked)
        # and the full_dev_dirname above.
        assert os.path.join(self._usb_dir, expected_dev_dir) == dev_path

    def test_get_sysfs_parent_hub_stub_logic(self):
        """Ensure that the utility function get_sysfs_parent_hub_stub works."""
        no_parent = "1-2"
        valid = "%s.1" % no_parent
        full_dir_no_parent = os.path.join(self._usb_dir, no_parent)
        full_dir_valid = "%s.1" % full_dir_no_parent
        # The root hub is returned when asking for the parent of a device without one
        assert Hierarchy.get_sysfs_parent_hub_stub(no_parent) == no_parent[0:-2]
        # The same is true if a full path is supplied.
        assert (
            Hierarchy.get_sysfs_parent_hub_stub(full_dir_no_parent)
            == full_dir_no_parent[0:-2]
        )
        # The parent stub should be returned if there is a parent device.
        assert no_parent == Hierarchy.get_sysfs_parent_hub_stub(valid)
        # If a full path is supplied the parent stub plus the directories leading up
        # to the usb device should be returned.
        assert full_dir_no_parent == Hierarchy.get_sysfs_parent_hub_stub(full_dir_valid)

    def test_get_parent_hub_stub(self):
        """Retrieving the .../devices/d-[d.d.d.d].d parent hub path stub works."""
        # Define own root hub number instead of using default to verify path name.
        root_hub = 3
        # Add a fake entry with minimum necessary attributes to be a valid entry
        add_fake_usb_entry(
            usb_devices_dir=self._usb_dir,
            root_hub=root_hub,
            hub_port_path=self._hub_port_path,
            devnum=self._devnum,
            busnum=self._busnum,
        )
        self._hierarchy.refresh_hierarchy()
        found_stub = self._hierarchy.get_parent_hub_stub(self._fake_dev)
        # The usb device's dirname is <root-hub>-<port-hub>[.<port-hub>]*
        expected_dev_dir = "%s-%s" % (root_hub, self._hub_port_path)
        parent_stub = Hierarchy.get_sysfs_parent_hub_stub(expected_dev_dir)
        # The entire parent hub sysfs substring  is the sysfs directory used
        # (here mocked) and the parent-stub above.
        assert os.path.join(self._usb_dir, parent_stub) == found_stub

    def test_get_parent_hub_stub_attached_to_root_hub(self):
        """The parent hub path stub is the root-hub if attached to the root-hub."""
        # Define own root hub number instead of using default to verify path name.
        root_hub = 3
        # Define own hub-port path without any sub-ports. Device is directly
        # attached to the root hub
        hub_port_path = "1"
        # Add a fake entry with minimum necessary attributes to be a valid entry
        add_fake_usb_entry(
            usb_devices_dir=self._usb_dir,
            root_hub=root_hub,
            hub_port_path=hub_port_path,
            devnum=self._devnum,
            busnum=self._busnum,
        )
        self._hierarchy.refresh_hierarchy()
        found_stub = self._hierarchy.get_parent_hub_stub(self._fake_dev)
        assert found_stub[-1] == str(root_hub)

    def test_dev_on_hub_port_on_conforming_devices(self):
        """DevOnHubPort is True when the device is a child of the hub stub."""
        default_hub_port_path = self._hub_port_path
        # Create another hub_port_path that's on the same parent
        parent_stub = Hierarchy.get_sysfs_parent_hub_stub(default_hub_port_path)
        new_dev_hub_port_path = "%s.7.9.7" % parent_stub
        assert Hierarchy.dev_on_hub_port_from_sysfs(parent_stub, new_dev_hub_port_path)

    def test_no_dev_on_hub_port_on_conforming_devices(self):
        """DevOnHubPort is False when dev_path is not a child of the hub stub."""
        hub_port_stub = "2-1.2.3"
        # This device hangs on hub 1.2.4 and not 1.2.3
        dev_port_path = "2-1.2.4.7"
        assert not Hierarchy.dev_on_hub_port_from_sysfs(hub_port_stub, dev_port_path)

    def test_no_dev_on_hub_port_on_common_ancestor_hub(self):
        """DevOnHubPort is False on conforming devices not sharing the same hub.

        This test has a common ancestor hub which is a common scenario on
        workstations.
        """
        # This might be the path of the v4 device on a workstation with a hub
        # at 4.1
        hub_port_stub = "2-4.1.2"
        # This might be the path of a servo micro device on a workstation
        # on that same 4.1 hub. Micro has no internal hub so this is
        # one port shorter.
        dev_port_path = "2-4.1.4"
        assert not Hierarchy.dev_on_hub_port_from_sysfs(hub_port_stub, dev_port_path)

    def test_dev_on_hub_port_same_path_different_root_hub(self):
        """DevOnHubPort is False when the root hub is different."""
        # To test the hub-port logic as above you really only need the port path
        # string. This test is to make sure that while that is true, the entire
        # path i.e. the root-hub is also taken into consideration
        hub_port_stub = "2-1.2"
        dev_port_path = "3-1.2.3"
        assert not Hierarchy.dev_on_hub_port_from_sysfs(hub_port_stub, dev_port_path)

    def test_dev_direct_on_hub_port(self):
        """DevDirectOnHubPort is True when the device is a direct child of
        the hub stub.
        """
        hub_port_stub = "2-1.2"
        dev_port_path = "2-1.2.3"
        assert Hierarchy.dev_direct_on_hub_port_from_sysfs(hub_port_stub, dev_port_path)

    def test_dev_direct_on_root_hub_port(self):
        """DevDirectOnHubPort is True when the device is a direct child of the
        root hub stub.
        """
        hub_port_stub = "2"
        dev_port_path = "2-1"
        assert Hierarchy.dev_direct_on_hub_port_from_sysfs(hub_port_stub, dev_port_path)

    def test_dev_not_direct_on_hub_port(self):
        """DevDirectOnHubPort is False when the root hub is different."""
        # To test the hub-port logic as above you really only need the port path
        # string. This test is to make sure that while that is true, the entire
        # path i.e. the root-hub is also taken into consideration
        hub_port_stub = "2-1"
        dev_port_path = "2-1.2.3"
        assert not Hierarchy.dev_direct_on_hub_port_from_sysfs(
            hub_port_stub, dev_port_path
        )

    def test_dev_num_from_sysfs_no_file(self):
        """HierarchyError is raised on missing devnum file."""
        # Note: as all the *FromSysfs methods use the same underlying method,
        # this one test is a proxy for all of them failing due to missing file.
        devd = add_fake_usb_entry(
            usb_devices_dir=self._usb_dir,
            hub_port_path=self._hub_port_path,
            # Note the omission of devnum  here
            busnum=self._busnum,
            serial=self._serial,
            vid=self._vid,
            pid=self._pid,
        )
        with self.assertRaisesRegex(
            HierarchyError,
            "Requested sysfs attribute "
            ".* cannot be read because the file cannot "
            "be found.",
        ):
            Hierarchy.dev_num_from_sysfs(devd)

    def test_dev_num_from_sysfs(self):
        """devnum is read out correctly and cast to be an int."""
        # Note: this test is a proxy for all *FromSysfs methods that cast to int:
        # - DevNum
        # - BusNum
        devd = add_fake_usb_entry(
            usb_devices_dir=self._usb_dir,
            hub_port_path=self._hub_port_path,
            devnum=self._devnum,
            busnum=self._busnum,
            serial=self._serial,
            vid=self._vid,
            pid=self._pid,
        )
        devnum = Hierarchy.dev_num_from_sysfs(devd)
        assert isinstance(devnum, int)
        assert devnum == self._devnum

    def test_dev_num_from_sysfs_no_int(self):
        """HierarchyError is raised if devnum's content cannot be cast to int()."""
        # Note: this test is a proxy for all *FromSysfs methods that cast to int:
        # - DevNum
        # - BusNum
        devd = add_fake_usb_entry(
            usb_devices_dir=self._usb_dir,
            hub_port_path=self._hub_port_path,
            busnum=self._busnum,
            serial=self._serial,
            vid=self._vid,
            pid=self._pid,
        )
        # The add_fake_usb_entry call casts the contents so we need to write it
        # ourselves here.
        devnum_f = os.path.join(devd, Hierarchy.DEV_FILE)
        content = "not-int-castable"
        with open(devnum_f, "w", encoding="utf-8") as f:
            f.write(content)
        with self.assertRaisesRegex(
            HierarchyError,
            "Unexpected content %r at sysfs file %r" % (content, devnum_f),
        ):
            _unused = Hierarchy.dev_num_from_sysfs(devd)

    def test_vendor_id_from_sysfs(self):
        """idVendor is read out correctly and cast to be an int with base 16."""
        # Note: this test is a proxy for all *FromSysfs methods that cast to int:
        # - VendorID
        # - ProductID
        devd = add_fake_usb_entry(
            usb_devices_dir=self._usb_dir,
            hub_port_path=self._hub_port_path,
            devnum=self._devnum,
            busnum=self._busnum,
            serial=self._serial,
            pid=self._pid,
        )
        # We manually write the content here to ensure that it would not
        # pass a standard int cast, and that add_fake_usb_entry does not do
        # the cast for us.
        vid = "fe"
        vid_f = os.path.join(devd, Hierarchy.VID_FILE)
        with open(vid_f, "w", encoding="utf-8") as f:
            f.write(vid)
        retrieved_vid = Hierarchy.vendor_id_from_sysfs(devd)
        assert isinstance(retrieved_vid, int)
        assert retrieved_vid == 0xFE

    def test_vendor_id_from_sysfs_no_int(self):
        """HierarchyError is raised if idVendor's contents are not base 16 int."""
        # Note: this test is a proxy for all *FromSysfs methods that cast to int:
        # - VendorID
        # - ProductID
        devd = add_fake_usb_entry(
            usb_devices_dir=self._usb_dir,
            hub_port_path=self._hub_port_path,
            devnum=self._devnum,
            busnum=self._busnum,
            serial=self._serial,
            pid=self._pid,
        )
        # The add_fake_usb_entry call casts the contents so we need to write it
        # ourselves here.
        bad_vid = "ge"
        vid_f = os.path.join(devd, Hierarchy.VID_FILE)
        with open(vid_f, "w", encoding="utf-8") as f:
            f.write(bad_vid)
        with self.assertRaisesRegex(
            HierarchyError,
            "Unexpected content %r at sysfs file %r" % (bad_vid, vid_f),
        ):
            _unused = Hierarchy.vendor_id_from_sysfs(devd)


def add_fake_usb_entry(
    usb_devices_dir,
    hub_port_path,
    root_hub=2,
    devnum=None,
    busnum=None,
    serial=None,
    vid=None,
    pid=None,
):
    """Helper to add a fake sysfs-like device file for a usb device.

    Args:
      usb_devices_dir: directory mocking /sys/bus/usb/devices
      hub_port_path: the 'x.x.x' port path of the device on the root hub
      root_hub: the usb root hub number
      devnum: content for the dev-num file. File not created if omitted
      busnum: content for the bus-num file. File not created if omitted
      serial: content for the serial file. File not created if omitted
      vid: content for the idVendor file. File not created if omitted
      pid: content for the idProduct file. File not created if omitted

    Returns:
      devdir: directory in |usb_devices_dir| that was created
    """
    dev_dir_path = "%d-%s" % (root_hub, hub_port_path)
    dev_dir_path_full = os.path.join(usb_devices_dir, dev_dir_path)
    # Create the fake device path entry
    os.mkdir(dev_dir_path_full)
    # Create a file for each attribute that is present
    for attr, attr_file, fmt in [
        (devnum, Hierarchy.DEV_FILE, "d"),
        (busnum, Hierarchy.BUS_FILE, "d"),
        (vid, Hierarchy.VID_FILE, "x"),
        (pid, Hierarchy.PID_FILE, "x"),
        (serial, Hierarchy.SERIAL_FILE, "s"),
    ]:
        if attr:
            attr_path = os.path.join(dev_dir_path_full, attr_file)
            with open(attr_path, "w", encoding="utf-8") as f:
                f.write(format(attr, fmt))
    return dev_dir_path_full


if __name__ == "__main__":
    unittest.main()


class TestUsbHierarchyPyTest:
    def test_get_usb_device(self, mock_v4p1_usb_device, mock_pyusb):
        _mock_usb = mock_pyusb
        device = mock_v4p1_usb_device("serialno", 1, 1)
        _mock_usb.devices.append(device)
        found_device = Hierarchy.get_usb_device(
            device.idVendor, device.idProduct, device.iSerial
        )
        assert found_device.iSerial == device.iSerial

    def test_get_usb_device_no_found(self, mock_v4p1_usb_device, mock_pyusb):
        _mock_usb = mock_pyusb
        device = mock_v4p1_usb_device("serialno", 1, 1)
        _mock_usb.devices.append(device)
        found_device = Hierarchy.get_usb_device(
            device.idVendor, device.idProduct, "garbage"
        )
        assert found_device is None

    def test_get_usb_device_multiple(self, mock_v4p1_usb_device, mock_pyusb):
        _mock_usb = mock_pyusb
        device = mock_v4p1_usb_device("serialno", 1, 1)
        device2 = mock_v4p1_usb_device("serialno2", 2, 2)
        _mock_usb.devices.append(device)
        _mock_usb.devices.append(device2)
        found_device = Hierarchy.get_usb_device(
            device.idVendor, device.idProduct, device.iSerial
        )
        assert found_device.iSerial == device.iSerial

    def test_get_usb_device_duplicate(self, mock_v4p1_usb_device, mock_pyusb):
        _mock_usb = mock_pyusb
        device = mock_v4p1_usb_device("serialno", 1, 1)
        device2 = mock_v4p1_usb_device("serialno", 2, 2)
        _mock_usb.devices.append(device)
        _mock_usb.devices.append(device2)
        with pytest.raises(HierarchyError):
            Hierarchy.get_usb_device(device.idVendor, device.idProduct, device.iSerial)

    def test_get_usb_device_bad_usb(self, mocker, mock_v4p1_usb_device, mock_pyusb):
        _mock_usb = mock_pyusb
        device = mock_v4p1_usb_device("serialno", 1, 1)
        device2 = mock_v4p1_usb_device("serialno2", 2, 2)
        device2.iSerial = ValueError("This is a test")
        _mock_usb.devices.append(device)
        _mock_usb.devices.append(device2)
        found_device = Hierarchy.get_usb_device(
            device.idVendor, device.idProduct, device.iSerial
        )
        assert found_device.iSerial == device.iSerial

    def test_get_usb_device_all_bad_usb(self, mocker, mock_v4p1_usb_device, mock_pyusb):
        _mock_usb = mock_pyusb
        device = mock_v4p1_usb_device("serialno", 1, 1)
        device2 = mock_v4p1_usb_device("serialno2", 2, 2)
        device2.iSerial = ValueError("This is a test")
        device.iSerial = ValueError("This is a test")
        _mock_usb.devices.append(device)
        _mock_usb.devices.append(device2)
        found_device = Hierarchy.get_usb_device(
            device.idVendor, device.idProduct, device.iSerial
        )
        assert found_device is None

    def test_get_usb_device_all_bad_core_usb(
        self, mocker, mock_v4p1_usb_device, mock_pyusb
    ):
        _mock_usb = mock_pyusb
        device = mock_v4p1_usb_device("serialno", 1, 1)
        device2 = mock_v4p1_usb_device("serialno2", 2, 2)
        device2.iSerial = usb.core.USBError("This is a test")
        device.iSerial = usb.core.USBError("This is a test")
        _mock_usb.devices.append(device)
        _mock_usb.devices.append(device2)
        found_device = Hierarchy.get_usb_device(
            device.idVendor, device.idProduct, device.iSerial
        )
        assert found_device is None
