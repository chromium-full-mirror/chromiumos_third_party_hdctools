# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""USB hierarchy class and helpers."""
import collections
import fcntl
import logging
import os
import re

import backoff
import usb

from servo.utils.retry_util import retry_hardware


backoff_logger = logging.getLogger("backoff")
backoff_logger.removeHandler(backoff_logger.handlers[0])


class HierarchyError(Exception):
    """Hierarchy error class."""


class Hierarchy:
    """A helper class to analyze the sysfs hierarchy of USB devices."""

    # Default sysfs path to use to for USB device information.
    DEFAULT_SYSFS_PATH = "/sys/bus/usb/devices"
    # Actually used sysfs path for USB device information. Split here is to
    # allow safe mocking and restoring of the default path.
    SYSFS_PATH = DEFAULT_SYSFS_PATH
    # Regex to discover usb device folders in |SYSFS_PATH|. The match group
    # here is to extract the usb hub port path to the device.
    DEV_RE = re.compile(r"\d+-\d+(\.\d+)*\Z")
    # Name of sysfs file containing the bus number.
    BUS_FILE = "busnum"
    # Name of sysfs file containing the device number.
    DEV_FILE = "devnum"
    # Name of sysfs file containing the device vendor id.
    VID_FILE = "idVendor"
    # Name of sysfs file containing the device product id.
    PID_FILE = "idProduct"
    # Name of sysfs file containing the serial number.
    SERIAL_FILE = "serial"
    # Value to write into the dev-file to trigger a reset.
    # Source of the macro vales:
    # elixir.bootlin.com/linux/v5.8-rc4/source/include/uapi/linux/usbdevice_fs.h
    # Source of the macro calculation:
    # elixir.bootlin.com/linux/v5.8-rc4/source/include/uapi/asm-generic/ioctl.h
    USBDEVFS_RESET = ord("U") << 8 | 20

    @classmethod
    def mock_usb_sysfs_path_for_test(cls, mock_dir):
        """Set the sysfs usb devices path to |mock_dir| for testing.

        Args:
          mock_dir: directory where mock [...]/usb/devices/ directories will be
        """
        cls.SYSFS_PATH = mock_dir

    @classmethod
    def restore_default_usb_sysfs_path_for_test(cls):
        """Restore the sysfs usb devices path to its default value."""
        cls.SYSFS_PATH = cls.DEFAULT_SYSFS_PATH

    def __init__(self):
        """Initialize UsbHierarchy by refreshing the hierarchy once."""
        # Get the current USB sysfs hierarchy.
        self.refresh_hierarchy()

    @staticmethod
    def reset_device_sysfs(sysfs_path):
        """Perform ioctl reset on the usb device.

        Args:
          path: /sys/bus/usb/devices path of the device

        Raises:
          HierarchyError: if |sysfs_path| does not exist
          HierarchyError: any issue writing to the device file
        """
        if not os.path.exists(sysfs_path):
            raise HierarchyError("No device at %r" % sysfs_path)
        busnum = Hierarchy.bus_num_from_sysfs(sysfs_path)
        devnum = Hierarchy.dev_num_from_sysfs(sysfs_path)
        dev_path = "/dev/bus/usb/%03d/%03d" % (busnum, devnum)
        if not os.path.exists(dev_path):
            raise HierarchyError("No device at %r but expected." % dev_path)
        try:
            with open(dev_path, "w", encoding="utf-8") as f:
                fcntl.ioctl(f, Hierarchy.USBDEVFS_RESET, 0)
        except Exception as e:
            # We want to repackage any issue here as HierarchyError to allow for
            # more robust code.
            raise HierarchyError(
                "Unhandled issue resetting device at busnum: %d "
                "devnum: %d sysfs_path: %r. %s" % (busnum, devnum, sysfs_path, str(e))
            ) from e

    @staticmethod
    def get_all_usb_devices(vid_pid_list=None):
        """Return all associated USB devices which match the given VID/PID's.

        Args:
          vid_pid_list: List of tuple (vid, pid).
        Notes:
          - vid_pid_list can be set to None. In that case, all devices ar returned
          - in the list, a pid can be None. In that case, all devices that match
            the vid will be returned irrespective of pid

        Returns:
          List of usb.core.Device objects.
        """
        all_devices = []
        if vid_pid_list is None:
            vid_pid_list = [None, None]
        for vid, pid in vid_pid_list:
            args = {"find_all": True}
            if vid is not None:
                args["idVendor"] = vid
            if pid is not None:
                args["idProduct"] = pid
            dev_gen = usb.core.find(**args)
            devs = list(dev_gen)
            if devs:
                all_devices.extend(devs)
        return all_devices

    @staticmethod
    def get_all_usb_device_sysfs_paths(vid_pid_list=None):
        """Return all USB devices sysfs path which match the given VID/PID's.

        Args:
          vid_pid_list: List of tuple (vid, pid).
        Notes:
          - vid_pid_list can be set to None. In that case, all devices ar returned
          - in the list, a pid can be None. In that case, all devices that match
            the vid will be returned irrespective of pid

        Returns:
          list of /sys/bus/usb/devices/... path to the devices that match vid/pid
          pairs
        """
        usb_hierarchy = Hierarchy()
        dev_paths = []
        if vid_pid_list is None:
            # Return all paths if the list is None
            return list(usb_hierarchy.hierarchy.values())
        # The |vid_lookup| maps all acceptable pid's for that vid.
        vid_lookup = collections.defaultdict(list)
        for vid, pid in vid_pid_list:
            vid_lookup[vid].append(pid)
        for path in usb_hierarchy.hierarchy.values():
            vid = Hierarchy.vendor_id_from_sysfs(path)
            pid = Hierarchy.product_id_from_sysfs(path)
            if None in vid_lookup[vid] or pid in vid_lookup[vid]:
                # A device only matches if the vid/pid pair is known, or if the pid
                # is a wildcard (pid = None)
                dev_paths.append(path)
        return dev_paths

    @staticmethod
    def get_usb_device_sysfs_path(vid, pid, serial):
        """Given vendor id, product id, and serial return usb sysfs directory.

        Args:
          vid: vendor id
          pid: product id
          serial: serial name

        Returns:
          /sys/bus/usb/devices/... path to the device at vid:pid serial

        Raises:
          HierarchyError: if more than one device are found with those attributes.
        """
        usb_hierarchy = Hierarchy()
        dev_paths = []
        for path in usb_hierarchy.hierarchy.values():
            path_vid = Hierarchy.vendor_id_from_sysfs(path)
            path_pid = Hierarchy.product_id_from_sysfs(path)
            try:
                path_serial = Hierarchy.serial_from_sysfs(path)
            except HierarchyError:
                # Not all devices have a serial file. In that case, ignore the device.
                continue
            if (path_vid, path_pid, path_serial) == (vid, pid, serial):
                dev_paths.append(path)
        if len(dev_paths) > 1:
            if serial:
                suffix = (
                    "Devices that share the same vid/pid should have a unique "
                    "serial. Please reprogram the serial"
                )
            else:
                suffix = "Please program a serialname as it currently reads empty"
            raise HierarchyError(
                "Found %d devices with vid: 0x%04x pid: 0x%04x "
                "sid: %r. %s." % (len(dev_paths), vid, pid, serial, suffix)
            )
        return dev_paths[0] if dev_paths else None

    @staticmethod
    @backoff.on_predicate(backoff.expo, lambda x: x == [], max_tries=5)
    @retry_hardware(
        exceptions=(HierarchyError, ValueError, usb.core.USBError), max_tries=5
    )
    def get_all_usb_devices_with_retry(vid, pid):
        return Hierarchy.get_all_usb_devices([(vid, pid)])

    @staticmethod
    @backoff.on_exception(
        backoff.expo,
        (ValueError, usb.core.USBError),
        max_tries=3,
        raise_on_giveup=False,
        giveup=lambda x: None,
    )
    def get_usb_device(vid, pid, serial):
        """Given vendor id, product id, and serial return usb device object.

        Args:
          vid: vendor id
          pid: product id
          serial: serial name

        Returns:
          usb.core.Device object if found otherwise None

        Raises:
          HierarchyError: if more than one device are found with those
                             attributes.
        """
        devices = Hierarchy.get_all_usb_devices_with_retry(vid, pid)
        devs = []
        bad_serial_read = False
        for device in devices:
            try:
                d_serial = usb.util.get_string(device, device.iSerialNumber)
            except (ValueError, usb.core.USBError):
                bad_serial_read = True
                continue
            if d_serial == serial:
                devs.append(device)
        if bad_serial_read and not devs:
            # Check all the devices and did not find the correct serial
            # number and at least one serial number failed to read so
            # force a retry from the start.
            raise ValueError("Unable to read device serial number.")
        if len(devs) > 1:
            raise HierarchyError(
                "Found %d devices with |vid:%s|, |pid:%s|, "
                "|serial:%s|. Should not happen."
                % (len(devs), str(vid), str(pid), str(serial))
            )
        return devs[0] if devs else None

    @staticmethod
    def _read_from_sysfs(sysfs_path, dev_file, cast=str):
        """Read |dev_file| from |sysfs_path| and return result cast into |cast|.

        Args:
          sysfs_path: full path, or port-hub stub in /sys/bus/usb/devices for device
          dev_file: file name under the directory at |syfs_path| to read out
          cast: function to cast the file content into before returning

        Returns:
          Content at |sysfs_path|/|dev_file| cast into |cast| on success

        Raises:
          HierarchyError: if |sysfs_path|/|dev_file| does not exist
          HierarchyError: if |sysfs_path|/|dev_file|'s contents fail with |cast|
        """
        if not os.path.isabs(sysfs_path):
            sysfs_path = os.path.join(Hierarchy.SYSFS_PATH, sysfs_path)
        dev_file_full = os.path.join(sysfs_path, dev_file)
        if not os.path.exists(dev_file_full):
            raise HierarchyError(
                "Requested sysfs attribute at %r cannot be read "
                "because the file cannot be found." % dev_file_full
            )
        with open(dev_file_full, "r", encoding="utf-8") as devf:
            try:
                content = devf.read().strip()
                return cast(content)
            except ValueError as e:
                raise HierarchyError(
                    "Unexpected content %r at sysfs file %r. %s"
                    % (content, dev_file_full, str(e))
                ) from e

    @staticmethod
    def dev_num_from_sysfs(sysfs_path):
        """Look for |DEV_FILE| under |sysfs_path| and return its value.

        Args:
          sysfs_path: path to a device folder under /sys/bus/usb/devices

        Returns:
          Contents of the file, cast to an int
        """
        return Hierarchy._read_from_sysfs(sysfs_path, Hierarchy.DEV_FILE, cast=int)

    @staticmethod
    def bus_num_from_sysfs(sysfs_path):
        """Look for |BUS_FILE| under |sysfs_path| and return its value.

        Args:
          sysfs_path: path to a device folder under /sys/bus/usb/devices

        Returns:
          Contents of the file, cast to an int
        """
        return Hierarchy._read_from_sysfs(sysfs_path, Hierarchy.BUS_FILE, cast=int)

    @staticmethod
    def vendor_id_from_sysfs(sysfs_path):
        """Look for |VID_FILE| under |sysfs_path| and return its value.

        Args:
          sysfs_path: path to a device folder under /sys/bus/usb/devices

        Returns:
          Contents of the file, interpreted as a hex value, cast to an int
        """
        return Hierarchy._read_from_sysfs(
            sysfs_path, Hierarchy.VID_FILE, lambda x: int("0x%s" % x, 0)
        )

    @staticmethod
    def product_id_from_sysfs(sysfs_path):
        """Look for |PID_FILE| under |sysfs_path| and return its value.

        Args:
          sysfs_path: path to a device folder under /sys/bus/usb/devices

        Returns:
          Contents of the file, interpreted as a hex value, cast to an int
        """
        return Hierarchy._read_from_sysfs(
            sysfs_path, Hierarchy.PID_FILE, lambda x: int("0x%s" % x, 0)
        )

    @staticmethod
    def serial_from_sysfs(sysfs_path):
        """Look for |SERIAL_FILE| under |sysfs_path| and return its value.

        Args:
          sysfs_path: path to a device folder under /sys/bus/usb/devices

        Returns:
          Contents of the file, cast to a string
        """
        return Hierarchy._read_from_sysfs(sysfs_path, Hierarchy.SERIAL_FILE)

    @staticmethod
    def complement_bus_num(busnum):
        """Find the complement bus to |busnum|.

        Assuming that |busnum| runs on usb3, this will find the busnum for the same
        host controller that runs on usb2 (and vice-versa).

        Assumptions (to aid debugging if/when the logic breaks):
        1. all usb buses are enumerated under `/sys/bus/usb/devices/usb$d`
        2. complement buses (usb2 and usb3 of the same controller) have the same
           pci device
        -> use sysfs pci paths to check for complement buses

        Args:
          busnum: int, busnum of the bus of interest

        Returns:
          busnum, int, the complement speed's busnum, or None if the controller
          is a single-speed controller with only one bus

        Raises:
          HierarchyError: if |busnum| is not a real usb bus on the system
          HierarchyError: if more than one complement bus are found
        """
        busdir = "usb%d" % busnum
        sysfs_buspath = "/sys/bus/usb/devices/" + busdir
        if not os.path.exists(sysfs_buspath):
            raise HierarchyError("No usb bus %d found" % busnum)
        pci_dev_path = os.path.dirname(os.path.realpath(sysfs_buspath))
        # let's search for the other candidates
        complement_candidates = [
            c for c in os.listdir(pci_dev_path) if re.match(r"usb\d+$", c)
        ]
        # remove |busnum| as a candidate
        if busdir in complement_candidates:
            complement_candidates.remove(busdir)
        if not complement_candidates:
            return None
        # Turn into busnum int
        complement_candidates = [int(c[3:]) for c in complement_candidates]
        if len(complement_candidates) > 1:
            raise HierarchyError(
                "%r all potential complement buses to %d"
                % (complement_candidates, busnum)
            )
        return complement_candidates[0]

    def _refresh_hierarchy(self):
        """Walk through usb sysfs files and gather device information.

        The usb sysfs dir contains dirs of the following format:
        - 1-2
        - 1-2:1.0
        - 1-2.4
        - 1-2.4:1.0

        The naming convention works like so:
          <roothub>-<hub port>[.port[.port]]:config.interface

        We are only going to be concerned with the roothub, hub port and port.
        We are going to create a hierarchy where each device will store the usb
        sysfs path of its roothub and hub port.  We will also grab the device's
        bus and device number to help correlate to a usb.core.Device object.

        We will walk through each dir and only match on device dirs
        (e.g. '1-2.4') and ignore config.interface dirs.  When we get a hit, we'll
        grab the bus/dev and infer the roothub and hub port from the dir name
        ('1-2' from '1-2.4') and store the info into a dict.

        The dict key will be a tuple of (bus, dev) and value be the sysfs path.

        """
        hierarchy = {}
        if not os.path.exists(self.SYSFS_PATH):
            logging.warning(
                "SYSFS_PATH %s not found. No devices will be found.", self.SYSFS_PATH
            )
            return hierarchy

        for usb_dir in os.listdir(self.SYSFS_PATH):
            if self.DEV_RE.match(usb_dir):
                usb_dir = os.path.join(self.SYSFS_PATH, usb_dir)
                try:
                    dev = Hierarchy.dev_num_from_sysfs(usb_dir)
                    bus = Hierarchy.bus_num_from_sysfs(usb_dir)
                except (IOError, HierarchyError):
                    # This means no bus/dev files. Skip
                    continue

                hierarchy[(bus, dev)] = usb_dir
        return hierarchy

    def refresh_hierarchy(self):
        self.hierarchy = self._refresh_hierarchy()

    @staticmethod
    def get_sysfs_parent_hub_stub(sysfs_dev_path):
        """Retrieve the usb port hub path up to and not including the device itself.

        This helper retrieves the ParentHubStub. This is useful to determine if two
        devices hang on the same usb hub (e.g. the internal usb hub on a servo).
        The anatomy of a usb sysfs dev file name is:

        The usb port path has to be the last element in sysfs_dev_path

        [d]-(d.)*[d]
         |   |    |
         |   |    device port i.e. the port on the previous hub where the device
         |   |    is attached.
         |   port hub path (i.e. ports on hubs until we get to the device.
         usb root hub

        For example a device could show up under
        '2-1.3.4'
        In this example:
          the root hub is 2:
          there are 2 hubs chained to that root hub.
          - |hub A| is attached the root hub's port |1|
          - |hub B| is attached to |hub A|'s port |3|
          - the device itself is attached to |hub B|'s port |4|

        Args:
          sysfs_dev_path: path to a device folder under /sys/bus/usb/devices

        Returns:
          Full path excluding the last hub (this is an invalid path usually)
        """
        # Need to ensure that this works whether the passed in path ends in /
        # or not.
        usbdir, dev_path = os.path.split(sysfs_dev_path.rstrip("/"))
        parent = ".".join(dev_path.split(".")[:-1])

        # If the device is mounted just behind the root hub (b/192534977), with no
        # additional hub, then parent will be None.
        # In that case, we still want to extract the root hub.
        if not parent:
            parent = dev_path.split("-")[0]

        return os.path.join(usbdir, parent) if parent else None

    def get_dev_port_path(self, usb_device):
        """Return the USB sysfs path of the supplied usb_device.

        Args:
          usb_device: usb.core.Device object.

        Returns:
          SysFS path string of parent of the supplied usb device,
          or None if not found.
        """
        dev_port_path = self.hierarchy.get(
            (int(usb_device.bus), int(usb_device.address)), None
        )
        return dev_port_path

    def get_parent_hub_stub(self, usb_device):
        """Return the USB sysfs path of the supplied usb_device's parent.

        Args:
          usb_device: usb.core.Device object.

        Returns:
          SysFS path string of parent of the supplied usb device,
          or None if not found.
        """
        dev_port_path = self.get_dev_port_path(usb_device)
        if dev_port_path:
            return Hierarchy.get_sysfs_parent_hub_stub(dev_port_path)
        return None

    def dev_on_dev_hub(self, dev_with_internal_hub, dev):
        """Check if |dev| is connected to |dev_with_internal_hub|'s internal hub.

        This also works in multiple layers e.g. if there are more hubs attached
        to the internal hub.

        Args:
          dev_with_internal_hub: usb.core.Device with an internal hub
          dev: usb.core.Device to check

        Returns:
          True if |dev| on the internal hub; False otherwise.
        """
        hub_dev_port_path = self.get_dev_port_path(dev_with_internal_hub)
        if not hub_dev_port_path:
            return False
        internal_hub_path = Hierarchy.get_sysfs_parent_hub_stub(hub_dev_port_path)
        dev_port_path = self.get_dev_port_path(dev)
        return Hierarchy.dev_on_hub_port_from_sysfs(internal_hub_path, dev_port_path)

    @staticmethod
    def dev_on_hub_port_from_sysfs(hub_stub, dev_port_path):
        """Static helper to see if |hub_stub| is an ancestor to |dev_port_path|.

        |hub_stub| is not a valid /sys/bus/usb/devices path but rather
        the parent hub stub of a device i.e. the port path of the hub that the
        device is connected on. For static configurations like v4's internal hub
        this can be used to determine if |dev_port_path| hangs (directly, or
        over more hubs) on that internal hub.

        Args:
          hub_stub: /dev/bus/usb/devices sysfs hub stub
          dev_port_path: /dev/bus/usb/devices sysfs path for device of interest

        Returns:
          True if |dev_port_path| hangs on |hub_stub|; False otherwise.
        """

        if hub_stub is None or dev_port_path is None:
            # This means at least one of them either is directly attached to a bus,
            # or has an invalid path.
            return False

        # Check the hierarchy:
        #   internal hub <-- servo v4 mcu
        #         \--------- external hub
        #                          \--------- USB candidate
        # Check having '.' to make sure it is one of the ports of the internal hub.
        if dev_port_path.startswith(hub_stub + "."):
            return True

        # In some special cases (b/192534977 for example), the device port can also
        # be just behind the root hub.
        # 'dev_port_path' will look like: /<path>/<root_hub>-<device_port>
        # Check if 'hub_stub' and 'dev_port_path' start with this same prefix
        if dev_port_path.startswith(hub_stub + "-"):
            return True

        return False

    @staticmethod
    def dev_direct_on_hub_port_from_sysfs(hub_stub, dev_port_path):
        """Static helper to see if |hub_stub| is a direct ancestor to |dev_port_path|.

        |hub_stub| is not a valid /sys/bus/usb/devices path but rather
        the parent hub stub of a device i.e. the port path of the hub that the
        device is connected on. For static configurations like v4's internal hub
        this can be used to determine if |dev_port_path| hangs directly on that
        internal hub.

        Args:
          hub_stub: /dev/bus/usb/devices sysfs hub stub
          dev_port_path: /dev/bus/usb/devices sysfs path for device of interest

        Returns:
          True if |dev_port_path| hangs directly on |hub_stub|; False otherwise.
        """

        if hub_stub is None or dev_port_path is None:
            # This means at least one of them either is directly attached to a bus,
            # or has an invalid path.
            return False

        dev_port_hub = Hierarchy.get_sysfs_parent_hub_stub(dev_port_path)
        return hub_stub == dev_port_hub
