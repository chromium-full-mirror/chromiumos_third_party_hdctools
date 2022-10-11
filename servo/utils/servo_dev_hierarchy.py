# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Servo device hierarchy based on the USB hierarchy."""

import argparse
import collections
import logging

from servo import servo_dev_templates
from servo import servo_parsing
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

class ServoDeviceEntry(object):
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
    hub_stub: stub of dev_path that up to and exluding the device's own port
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
    self.vid = vid
    self.pid = pid
    self.serial = serial
    self.dev_path = dev_path
    # (vid, pid, serial) tuple is used throughout as unique id.
    self.id = (self.vid, self.pid, self.serial)
    self.dev_template = servo_dev_templates.GetTemplateClass(vid, pid, serial)
    if not self.dev_template:
      raise ServoDeviceHierarchyError('Cannot retrieve device template for device'
                                      'vid %s pid %s serial %s dev_path %s'
                                      % (vid, pid, serial, dev_path))
    self.cluster_root = None
    if self.dev_template.HUB_SERVO:
      self.cluster_members = None
      self.hub_stub = UsbHierarchy.GetSysfsParentHubStub(dev_path)
    # Device options of this device. Will be filled by device finder.
    self.devopts = None
    # This is used to hold a pointer to its own ServoDevice object
    self.servo_device = None

  def __repr__(self):
    return str(self)

  def __str__(self):
    return '[%s (%04x:%04x) %s]' % (self.dev_template.TYPE, self.vid, self.pid,
      self.serial)

  def set_cluster_root(self, root_servo):
    """Set root_servo to be this device's cluster's root servo.

    A Servo device can belong to a cluster if it connects to other servo devices.
    Otherwise, it is considered a solo device.
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
    self._validate_no_duplicate_root(root_servo)
    self._validate_root_is_hub(root_servo)
    self._validate_two_level_cluster(root_servo)

    # ensure the root servo recognizes itself as a root
    if not root_servo.is_cluster_root():
      root_servo.cluster_root = root_servo
      root_servo.cluster_members = [root_servo]
    self.cluster_root = root_servo
    self.cluster_root.cluster_members.append(self)

  def is_cluster_root(self):
    """Check if this device is a root_servo.
    """
    return self.cluster_root == self

  def is_in_cluster(self):
    """Check if this device is in a cluster and is not a solo device.
    """
    return self.cluster_root is not None

  def _validate_no_duplicate_root(self, root_servo):
    """Validate the current servo device has not been configured with a different
    root servo.

    Args:
      root_servo: ServoDeviceEntry that is the root servo of this device's cluster

    Raises:
      ServoDeviceHierarchyError: if this entry already has a different root servo.
      ServoDeviceHierarchyError: if root_servo cannot be a root servo
    """
    if self.cluster_root:
      # validate cluster_root is the only entry representing the physical device
      self.cluster_root.validate_entry_uniqueness(root_servo)
      if self.cluster_root == root_servo:
        return
      elif self.is_cluster_root():
        raise ServoDeviceHierarchyError('Currently servod does not support chaining '
                                        '3 or more levels of servo devices (e.g. '
                                        'servo v4 -> servo v4 -> ccd). Failed to set '
                                        '%s as the root servo of %r because the latter '
                                        'is already a root servo.' % (root_servo, self))
      else:
        raise ServoDeviceHierarchyError('A servo device entry cannot have more than '
                                        'one root servo. Current device: %r.'
                                        'Current device root servo: %r.'
                                        'Trying to also set %r as root servo.' % (
                                        self, self.cluster_root, root_servo))

  def _validate_root_is_hub(self, root_servo):
    """Validate root_servo has a USB hub and other servo devices can connect to it

    Args:
      root_servo: ServoDeviceEntry that is the root servo of this device's cluster

    Raises:
      ServoDeviceHierarchyError: if this entry already has a different root servo.
      ServoDeviceHierarchyError: if root_servo cannot be a root servo
    """
    if not root_servo.dev_template.HUB_SERVO:
      raise ServoDeviceHierarchyError('Failed to set %r as the root servo of %r'
                                      'because the former is not a hub servo.' % (
                                      root_servo, self))

  def _validate_two_level_cluster(self, root_servo):
    """Validate the cluster only has two levels.

    Args:
      root_servo: ServoDeviceEntry that is the root servo of this device's cluster

    Raises:
      ServoDeviceHierarchyError: if this entry already has a different root servo.
      ServoDeviceHierarchyError: if root_servo cannot be a root servo
    """
    if root_servo.cluster_root and (not root_servo.is_cluster_root()):
      raise ServoDeviceHierarchyError('Currently servod does not support chaining '
                                      '3 or more levels of servo devices (e.g. '
                                      'servo v4 -> servo v4 -> ccd). Failed to set'
                                      ' %r as the root servo of %r because the former'
                                      'is already on the 2nd level.' % (
                                      root_servo, self))

  def validate_entry_uniqueness(self, other_entry):
    """Validate each physical device only corresponds to a device entry.

    Args:
      other_entry: Another ServoDeviceEntry

    Raises:
      ServoDeviceHierarchyError: if this entry corresponds to the same entry
        as the other entry but are 2 different entries
    """
    if other_entry is None:
      return
    if other_entry == self:
      return
    if self.vid == other_entry.vid and self.pid == other_entry.pid \
      and self.serial == other_entry.serial:
      raise ServoDeviceHierarchyError('Device (%04x:%04x) %s corresponds to 2 ServoDeviceEntry.'
                                       % (self.vid, self.pid, self.serial))

class ServoDeviceHierarchy(object):
  """A usb hierarchy of servo devices.

  Keeps an index of servo devices and whether or not they are in clusters
  or solo devices.
  """

  def __init__(self):
    """Initialize servo hierarchy from a UsbHierarchy.

    Create a UsbHierarchy and get all entries that have a servo vid/pid
    associated with it. From those entries, this then generates the
    device relationships e.g. what device is in a cluster with what
    other device (v4 + micro) etc.
    """
    self._logger = logging.getLogger('ServoDeviceHierarchy')
    self._logger.debug('')
    # Collect all servod devices on the system.
    self._dev_by_id = collections.defaultdict(lambda: None)
    self._dev_by_vid = collections.defaultdict(lambda: set())
    self._dev_by_pid = collections.defaultdict(lambda: set())
    self._dev_by_serial = collections.defaultdict(lambda: set())
    self._cluster_root_servos = {}
    self._cluster_non_root_servos = {}
    self._solo_devices = {}
    hub_servos = []
    all_servo_devs = []
    # Filter the dev paths by servo id defaults (vid/pid pairs)
    ids = servo_dev_templates.SERVO_ID_DEFAULTS
    for dev_path in UsbHierarchy.GetAllUsbDeviceSysfsPaths(ids):
      dev_vid = UsbHierarchy.VendorIDFromSysfs(dev_path)
      dev_pid = UsbHierarchy.ProductIDFromSysfs(dev_path)
      dev_serial = UsbHierarchy.SerialFromSysfs(dev_path)
      entry = ServoDeviceEntry(vid=dev_vid, pid=dev_pid, serial=dev_serial,
                               dev_path=dev_path)
      self.add_entry(entry)
      all_servo_devs.append(entry)
      if entry.dev_template.HUB_SERVO:
        hub_servos.append(entry)
      self._solo_devices[entry.id] = entry
    # Go over the devices that are not hub servos, and see if they belong
    # to a cluster by checking if they have a hub for them.
    while all_servo_devs:
      a_servo = all_servo_devs.pop()
      for hub_servo in hub_servos:
        if a_servo == hub_servo:
          continue
        # if a servo has an internal hub, then we want to test if the
        # internal hub hangs directly on some other hub
        if a_servo.dev_template.HUB_SERVO:
          a_servo_dev_path = a_servo.hub_stub
        else:
          a_servo_dev_path = a_servo.dev_path
        if UsbHierarchy.DevDirectOnHubPortFromSysfs(hub_servo.hub_stub,
                                                    a_servo_dev_path):
          a_servo.set_cluster_root(hub_servo)
          self._cluster_root_servos[hub_servo.id] = hub_servo
          self._cluster_non_root_servos[a_servo.id] = a_servo
          self._solo_devices.pop(hub_servo.id, None)
          self._solo_devices.pop(a_servo.id, None)
          break

  def add_entry(self, entry):
    """Add a ServoDeviceEntry to hierarchy.
    """
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
      List with device and any other devices in its cluste
      List with only device if device not part of a cluster
      Empty list if device not found
    """
    dev = self.get_entry(vid, pid, serial)
    if dev:
      # check if this device is a solo device
      if not dev.cluster_root:
        return [dev]
      # Find the root servo of the cluster and return all members
      else:
        return dev.cluster_root.cluster_members
    else:
      return []

  # Note on the following three methods. In a functional system:
  # d = set(get_cluster_root_servos())
  # c = set(get_cluster_non_root_servos())
  # s = set(get_solo_devices()
  # s & c & d == empty set
  # s | c | d == all servo devices on the system
  def get_cluster_root_servos(self):
    """Return all root servo devices on the system in a cluster."""
    return self._cluster_root_servos.values()

  def get_cluster_non_root_servos(self):
    """Return all non root servo devices on the system in a cluster."""
    return self._cluster_non_root_servos.values()

  def get_solo_devices(self):
    """Return all devices on the system that are not part of a cluster."""
    return self._solo_devices.values()

  @staticmethod
  def generate_device_priority(devices):
    """Generate the priority for each device to be the targeting device.

    Each device gets an integer as the priority to be the targeting device.
    A higher priority indicates that the device is
    (1) more likely to be the main device that by default handles all requests to servod
    (2) more likely to be the device targeted by the user when they only provide partial
        information for selecting a device

    Currently priority is decided in the following way:
    0: the device chosen to be the main device in the commandline. If the main device
       chosen by the user is a cluster root, then we substitute with the device with
      the highest priority in the cluster.
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
              - list[2] only contains "c2d2". Its priority to be the main device is lower
              than the debug headers but higher than other dut controllers.
              - list[3] contains nothing. Its priority to be the main device is
              the lowest among all dut controllers.
              - list[4] only contains "sweetberry". Its priority to be the main device
              is lower than all dut controllers and higher than the cluster root hub
              servo v4.
              - list[5] only contains "servo v4". Its priority to be the main device
              is the lowest.
    """
    prioritized_devs = [[], [], [], [], [], []]
    user_chosen_main_roots = []
    for device in devices:
      if device.devopts and device.devopts.prefix in servo_dev_templates.MAIN_DEV_PREFIXES:
        if device.is_cluster_root():
          user_chosen_main_roots.append(device)
        else:
          prioritized_devs[PRIORITY_MAIN_DEV].append(device)
      elif device.dev_template.TYPE in servo_dev_templates.DEBUG_HEADER_SERVO_TYPES:
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
      for idx in range(len(prioritized_devs)):
        # Only do substitution for children of the main root devices not yet chosen as main devices
        if idx == PRIORITY_MAIN_DEV or idx == PRIORITY_CLUSTER_ROOT_DEV:
          continue
        root_children = [dev for dev in prioritized_devs[idx] if dev in root.cluster_members]
        # Substitution is done when some children are chosen to substitute the main root devices
        if root_children:
          prioritized_devs[PRIORITY_MAIN_DEV].extend(root_children)
          prioritized_devs[idx] = [dev for dev in prioritized_devs[idx] if dev not in root_children]
          prioritized_devs[PRIORITY_CLUSTER_ROOT_DEV].append(root)
          break
    return prioritized_devs

  @staticmethod
  def most_prirotized_devices(prioritized_devs):
    """Choose the devices with the highest priority from generate_device_priority.

    Args:
      prioritized_devs: A list of lists representing the priority of devices. The list index
        indicates the priority for a device to be the main device.

    Returns:
      A list representing the devices with the highest priority.
    """
    for level in prioritized_devs:
      if level:
        return level
    return []
