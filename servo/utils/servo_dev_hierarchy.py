# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Servo device hierarchy based on the USB hierarchy."""

import collections
import logging

from servo.common import servo_dev_templates
from servo.utils.usb_hierarchy import Hierarchy as UsbHierarchy


# Priorities of different kinds of servo devices.
# The priorities should be consecutive integers starting from 0, because
# they are used as index of the prioritized devices list. Smaller integer
# indicates a device is more prioritized and more likely to be the targeted
# device for a servod control command.
PRIORITY_MAIN_DEV = 0
PRIORITY_DEBUG_HEADER_SERVO = 1
PRIORITY_CCD_SERVO = 2
PRIORITY_DUT_CONTROLLER_DEFAULT = 3
PRIORITY_DEFAULT = 4
PRIORITY_CLUSTER_ROOT_DEV = 5


class ServoDeviceHierarchyError(Exception):
    """ServoDeviceHierarchy error class."""


class ServoDeviceEntry:
    """A summarized entry for a servo device on the system.

    Attributes:
      vid: idVendor of the servo device
      pid: idProduct of the servo device
      serial: serial of the servo device
      id: tuple of (vid, pid, serial)
      type: servo device type string
      dev_path: /sys/bus/usb/devices/... path of the servo device file
      dev_template: device template of the servo device
      cluster_root: the root servo of the cluster the device is currently
                    a part of
      hub_stub: stub of dev_path that up to and excluding the device's own port
                i.e. if the device is at 1-3.3.4 the stub would be 1-3.3
      cluster_members: the members in the cluster this device is currently a
                      root servo to
    """

    def __init__(self, vid, pid, serial, dev_path):
        """Setup entry.

        Args:
          vid: idVendor of the servo device
          pid: idProduct of the servo device
          serial: serial of the servo device
          dev_path: /sys/bus/usb/devices/... path of the servo device file
        """
        self.__vid = vid
        self.__pid = pid
        self.__serial = serial
        self.__dev_path = dev_path
        # (vid, pid, serial) tuple is used by users of these objects as unique id.
        # This should be replaced with the (vid, pid, serial, dev_path) key.
        self.__id = vid, pid, serial
        self.__key = vid, pid, serial, dev_path
        self.__dev_template = servo_dev_templates.get_template_class(vid, pid, serial)
        if not self.dev_template:
            raise ServoDeviceHierarchyError(
                "Cannot retrieve device template for device vid %r pid %r serial %r "
                "dev_path %r" % (vid, pid, serial, dev_path)
            )
        self.cluster_root = None
        self.cluster_members = set()
        if self.dev_template.HUB_SERVO:
            self.hub_stub = UsbHierarchy.get_sysfs_parent_hub_stub(dev_path)
        # Device options of this device. Will be filled by device finder.
        self.devopts = None
        # This is used to hold a pointer to its own ServoDevice object
        self.servo_device = None

    @property
    def vid(self):
        return self.__vid

    @property
    def pid(self):
        return self.__pid

    @property
    def serial(self):
        return self.__serial

    @property
    def dev_path(self):
        return self.__dev_path

    @property
    def key(self):
        return self.__key

    # This should be renamed to avoid reusing a builtin name.
    # Or delete in favor of using the newer "key" attribute.
    @property
    def id(self):
        return self.__id

    @property
    def dev_template(self):
        return self.__dev_template

    def __repr__(self):
        return str(self)

    def __str__(self):
        return "[%s (%04x:%04x) %s]" % (
            self.dev_template.TYPE,
            self.vid,
            self.pid,
            self.serial,
        )

    def __hash__(self):
        return hash(self.key)

    def __eq__(self, other):
        if isinstance(other, ServoDeviceEntry):
            return self.key == other.key
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, ServoDeviceEntry):
            return self.key != other.key
        return NotImplemented

    def __lt__(self, other):
        if isinstance(other, ServoDeviceEntry):
            return self.key < other.key
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, ServoDeviceEntry):
            return self.key <= other.key
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, ServoDeviceEntry):
            return self.key > other.key
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, ServoDeviceEntry):
            return self.key >= other.key
        return NotImplemented

    def set_cluster_root(self, root_servo):
        """Set root_servo to be this device's cluster's root servo.

        Each cluster has a hub servo as the root.
        Each cluster can have multiple hub servos.
        Each cluster should form a 2-level tree, e.g. the root and its children.
        Setups like ServoV4->ServoV4->ServoV4 are not supported now.

        Args:
          root_servo: ServoDeviceEntry that is the root servo of this device's cluster

        Raises:
          ServoDeviceHierarchyError: if this entry already has a different root servo.
          ServoDeviceHierarchyError: if root_servo cannot be a root servo
        """
        # validate setting the root_servo as cluster_root is a legitimate action
        self._validate_root(root_servo)
        self.cluster_root = root_servo
        self.cluster_root.cluster_members.add(self)

    def is_cluster_root(self):
        """Check if this device is a root_servo."""
        return self.cluster_root == self

    def _validate_root(self, root_servo):
        """Validate that setting the proposed root_servo will not violate any
        servo hierarchy constraints.

        Args:
          root_servo: ServoDeviceEntry that is the root servo of this device's cluster

        Raises:
          ServoDeviceHierarchyError: if this entry already has a different root servo.
          ServoDeviceHierarchyError: if root_servo cannot be a root servo
        """
        if self.cluster_root is None or self.cluster_root is root_servo:
            return
        # validate cluster_root is the only entry representing the physical device
        self.cluster_root.validate_entry_uniqueness(root_servo)
        if root_servo is self or self.cluster_root is self:
            raise ServoDeviceHierarchyError(
                "Currently servod does not support chaining "
                "3 or more levels of servo devices (e.g. "
                "servo v4 -> servo v4 -> ccd). Failed to set "
                "%s as the root servo of %r because the latter "
                "is already a root servo." % (root_servo, self)
            )
        raise ServoDeviceHierarchyError(
            "A servo device entry cannot have more than "
            "one root servo. Current device: %r."
            "Current device root servo: %r."
            "Trying to also set %r as root servo."
            % (self, self.cluster_root, root_servo)
        )

    def validate_entry_uniqueness(self, other_entry):
        """Validate each physical device only corresponds to a device entry.

        Args:
          other_entry: Another ServoDeviceEntry

        Raises:
          ServoDeviceHierarchyError: if this entry corresponds to the same entry
            as the other entry but are 2 different entries
        """
        if other_entry is None or other_entry is self:
            return
        if other_entry == self or (
            self.vid == other_entry.vid
            and self.pid == other_entry.pid
            and self.serial == other_entry.serial
        ):
            raise ServoDeviceHierarchyError(
                "Device (%04x:%04x) %s corresponds to 2 ServoDeviceEntry."
                % (self.vid, self.pid, self.serial)
            )


class ServoDeviceHierarchy:
    """A usb hierarchy of servo devices."""

    def __init__(self):
        """Initialize servo hierarchy from a UsbHierarchy.

        Create a UsbHierarchy and get all entries that have a servo vid/pid
        associated with it. From those entries, this then generates the
        device relationships e.g. what device is in a cluster with what
        other device (v4 + micro) etc.
        """
        self._logger = logging.getLogger("ServoDeviceHierarchy")

        # Collect all servod devices on the system.
        self._dev_by_id = collections.defaultdict(lambda: None)
        self._dev_by_vid = collections.defaultdict(set)
        self._dev_by_pid = collections.defaultdict(set)
        self._dev_by_serial = collections.defaultdict(set)
        self._cluster_root_servos = {}
        self._cluster_non_root_servos = {}
        hub_servos = []
        all_servo_devs = []
        # Filter the dev paths by servo id defaults (vid/pid pairs)
        ids = servo_dev_templates.SERVO_ID_DEFAULTS
        for dev_path in UsbHierarchy.get_all_usb_device_sysfs_paths(ids):
            dev_vid = UsbHierarchy.vendor_id_from_sysfs(dev_path)
            dev_pid = UsbHierarchy.product_id_from_sysfs(dev_path)
            dev_serial = UsbHierarchy.serial_from_sysfs(dev_path)
            entry = ServoDeviceEntry(
                vid=dev_vid, pid=dev_pid, serial=dev_serial, dev_path=dev_path
            )
            self.add_entry(entry)
            all_servo_devs.append(entry)
            if entry.dev_template.HUB_SERVO:
                hub_servos.append(entry)
        # Go over the devices that are not hub servos, and see if they belong
        # to a cluster by checking if they have a hub for them.
        for a_servo in all_servo_devs:
            for hub_servo in hub_servos:
                if a_servo == hub_servo:
                    continue
                # if a servo has an internal hub, then we want to test if the
                # internal hub hangs directly on some other hub
                if a_servo.dev_template.HUB_SERVO:
                    a_servo_dev_path = a_servo.hub_stub
                else:
                    a_servo_dev_path = a_servo.dev_path
                if UsbHierarchy.dev_direct_on_hub_port_from_sysfs(
                    hub_servo.hub_stub, a_servo_dev_path
                ):
                    # We only support one level of hub servo.
                    hub_servo.set_cluster_root(hub_servo)
                    a_servo.set_cluster_root(hub_servo)
                    self._cluster_non_root_servos[a_servo.id] = a_servo
                    break
            else:
                # No parent hub servo found, so this servo is a root servo.
                a_servo.set_cluster_root(a_servo)
                self._cluster_root_servos[a_servo.id] = a_servo

    def add_entry(self, entry):
        """Add a ServoDeviceEntry to hierarchy."""
        entry.validate_entry_uniqueness(self._dev_by_id[entry.id])
        self._dev_by_id[entry.id] = entry
        self._dev_by_vid[entry.vid].add(entry)
        self._dev_by_pid[entry.pid].add(entry)
        self._dev_by_serial[entry.serial].add(entry)

    def get_entry(self, vid, pid, serial):
        """Return ServoDeviceEntry for specific identifier.

        Args:
          vid: device vendor ID
          pid: device product ID
          serial: device serial name

        Returns:
          ServoDeviceEntry for the device if known, None otherwise.
        """
        return self._dev_by_id[(vid, pid, serial)]

    def get_entries(self, vid, pid, serial):
        """Return a set of ServoDeviceEntry for the specific identifiers.

        Args:
          vid: device vendor ID. If none, we will match to all vids.
          pid: device product ID. If none, we will match to all pids.
          serial: device serial name. If none, we will match to all serialnames.

        Returns:
          A set of ServoDeviceEntry for the device identifier.
        """
        if vid and pid and serial:
            dev = self.get_entry(vid, pid, serial)
            return {dev} if dev else {}
        setlist = []
        if vid:
            setlist.append(self._dev_by_vid[vid])
        if pid:
            setlist.append(self._dev_by_pid[pid])
        if serial:
            setlist.append(self._dev_by_serial[serial])
        return set.intersection(*setlist) if setlist else {}

    def get_all_entries(self):
        """Return all the ServoDeviceEntry in this hierarchy.

        Returns:
          A map of ServoDeviceEntry keyed by (vid, pid, serial).
        """
        return self._dev_by_id

    def get_cluster(self, vid, pid, serial):
        """Get all devices in the same cluster as device at vid/pid/serial.

        Args:
          vid: device vendor ID
          pid: device product ID
          serial: device serial name

        Returns:
          List with device and any other devices in its cluster
          List with only device if device not part of a cluster
          Empty list if device not found
        """
        dev = self.get_entry(vid, pid, serial)
        if dev:
            # Find the root servo of the cluster and return all members
            return sorted(dev.cluster_root.cluster_members)
        return []

    # Note on the following three methods. In a functional system:
    # d = set(get_cluster_root_servos())
    # c = set(get_cluster_non_root_servos())
    # c & d == empty set
    # c | d == all servo devices on the system
    def get_cluster_root_servos(self):
        """Return all root servo devices on the system in a cluster."""
        return self._cluster_root_servos.values()

    def get_cluster_non_root_servos(self):
        """Return all non root servo devices on the system in a cluster."""
        return self._cluster_non_root_servos.values()

    @staticmethod
    def generate_device_priority(devices):
        """Generate the priority for each device to be the targeting device.

        Each device gets an integer as the priority to be the targeting device.
        A higher priority indicates that the device is
        (1) more likely to be the main device that by default handles all requests to
            servod
        (2) more likely to be the device targeted by the user when they only provide
            partial information for selecting a device

        Currently priority is decided in the following way:
        0: the device chosen to be the main device in the command line. If the main
           device chosen by the user is a cluster root, then we substitute with the
           device with the highest priority in the cluster.
        1: Debug header servos, e.g. Servo Micro, C2D2, Servo V2
        2: CCD DUT controllers, e.g. CCD CR50, CCD TI50
        3. Other DUT controllers (currently there are no such controllers)
        4: non-dut-controller non-cluster-root devices, e.g. Sweetberry
        5: cluster-root devices, e.g. a cluster-root Servo V4

        Args:
          devices: A list of ServoDeviceEntry.

        Returns:
          A list of lists representing the priority of each given device. The list index
          indicates the priority for a device to be the main device.
          Example. [[], ["servo micro 1", "servo micro 2"], ["ccd_cr50"], [""],
                    ["sweetberry"], ["servo v4"]]
                  - list[0] is empty as the user does not specify a main device in the
                  command line.
                  - list[1] has 2 entries "servo micro 1" and "servo micro 2", so they
                  share the highest priority to be the main device. We will let the user
                  decide which one is the main device through an interactive menu.
                  - list[2] only contains "c2d2". Its priority to be the main device is
                    lower than the debug headers but higher than other dut controllers.
                  - list[3] contains nothing. Its priority to be the main device is
                  the lowest among all dut controllers.
                  - list[4] only contains "sweetberry". Its priority to be the main
                    device is lower than all dut controllers and higher than the cluster
                    root hub
                  servo v4.
                  - list[5] only contains "servo v4". Its priority to be the main device
                  is the lowest.
        """
        prioritized_devs = [[], [], [], [], [], []]
        user_chosen_main_roots = []
        for device in devices:
            if device.devopts and set(device.devopts.prefix).intersection(
                servo_dev_templates.MAIN_DEV_PREFIXES
            ):
                if device.is_cluster_root():
                    user_chosen_main_roots.append(device)
                else:
                    prioritized_devs[PRIORITY_MAIN_DEV].append(device)
            elif (
                device.dev_template.TYPE in servo_dev_templates.DEBUG_HEADER_SERVO_TYPES
            ):
                prioritized_devs[PRIORITY_DEBUG_HEADER_SERVO].append(device)
            elif device.dev_template.TYPE in servo_dev_templates.CCD_SERVO_TYPES:
                prioritized_devs[PRIORITY_CCD_SERVO].append(device)
            elif device.dev_template.DUT_CONTROLLER:
                prioritized_devs[PRIORITY_DUT_CONTROLLER_DEFAULT].append(device)
            elif device.is_cluster_root():
                prioritized_devs[PRIORITY_CLUSTER_ROOT_DEV].append(device)
            else:
                prioritized_devs[PRIORITY_DEFAULT].append(device)

        # Do substitution if the main device chosen by the user is a cluster root
        for root in user_chosen_main_roots:
            for idx, devs in enumerate(prioritized_devs):
                # Only do substitution for children of the main root devices not
                # yet chosen as main devices
                if idx in (PRIORITY_MAIN_DEV, PRIORITY_CLUSTER_ROOT_DEV):
                    continue
                root_children = [dev for dev in devs if dev in root.cluster_members]
                # Substitution is done when some children are chosen to substitute the
                # main root devices
                if root_children:
                    prioritized_devs[PRIORITY_MAIN_DEV].extend(root_children)
                    prioritized_devs[idx] = [
                        dev for dev in devs if dev not in root_children
                    ]
                    prioritized_devs[PRIORITY_CLUSTER_ROOT_DEV].append(root)
                    break
        return prioritized_devs

    @staticmethod
    def most_prioritized_devices(prioritized_devs):
        """Choose the devices with the highest priority from generate_device_priority.

        Args:
          prioritized_devs: A list of lists representing the priority of devices.
                            The list index indicates the priority for a device to
                            be the main device.

        Returns:
          A list representing the devices with the highest priority.
        """
        for level in prioritized_devs:
            if level:
                return level
        return []
