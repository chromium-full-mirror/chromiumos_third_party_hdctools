# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Servo device hierarchy based on the USB hierarchy."""

import collections
import logging

from servo import servo_dev_templates
from servo.utils.usb_hierarchy import Hierarchy as UsbHierarchy

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
    end_device: whether the servo device is a leaf of a cluster, i.e. has
                no child servo devices plugged onto it
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
    self.end_device = True
    if self.dev_template.IS_HUB_SERVO:
      self.cluster_members = None
      self.hub_stub = UsbHierarchy.GetSysfsParentHubStub(dev_path)

  def __repr__(self):
    return str(self)

  def __str__(self):
    return '%s (%04x:%04x) %s USB path: %s' % (self.dev_template.TYPE, self.vid, self.pid,
      self.serial, self.dev_path)

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
    if not root_servo.cluster_members:
      root_servo.cluster_root = root_servo
      root_servo.cluster_members = {root_servo.id: root_servo}
      root_servo.end_device = False
    self.cluster_root = root_servo
    self.cluster_root.cluster_members[self.id] = self

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
      elif self.cluster_root == self:
        raise ServoDeviceHierarchyError('Currently servod does not support chaining '
                                        '3 or more levels of servo devices (e.g. '
                                        'servo v4 -> servo v4 -> ccd). Failed to set '
                                        '%r as the root servo of %r because the latter '
                                        'is already a root servo.' % (
                                        root_servo.dev_path, self.dev_path))
      else:
        raise ServoDeviceHierarchyError('A servo device entry cannot have more than '
                                        'one root servo. Device sysfs dev path: %r.'
                                        'Current root servo sysfs dev path: %r.'
                                        'Trying to also set %r as root servo.' % (
                                        self.dev_path, self.cluster_root.dev_path,
                                        root_servo.dev_path))

  def _validate_root_is_hub(self, root_servo):
    """Validate root_servo has a USB hub and other servo devices can connect to it

    Args:
      root_servo: ServoDeviceEntry that is the root servo of this device's cluster

    Raises:
      ServoDeviceHierarchyError: if this entry already has a different root servo.
      ServoDeviceHierarchyError: if root_servo cannot be a root servo
    """
    if not root_servo.dev_template.IS_HUB_SERVO:
      raise ServoDeviceHierarchyError('Failed to set %r as the root servo of %r'
                                      'because the former is not a hub servo.' % (
                                      root_servo.dev_path, self.dev_path))

  def _validate_two_level_cluster(self, root_servo):
    """Validate the cluster only has two levels.

    Args:
      root_servo: ServoDeviceEntry that is the root servo of this device's cluster

    Raises:
      ServoDeviceHierarchyError: if this entry already has a different root servo.
      ServoDeviceHierarchyError: if root_servo cannot be a root servo
    """
    if root_servo.cluster_root and root_servo.cluster_root != root_servo:
      raise ServoDeviceHierarchyError('Currently servod does not support chaining '
                                      '3 or more levels of servo devices (e.g. '
                                      'servo v4 -> servo v4 -> ccd). Failed to set'
                                      ' %r as the root servo of %r because the former'
                                      'is already on the 2nd level.' % (
                                      root_servo.dev_path, self.dev_path))

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
    self._servo_dev_index = collections.defaultdict(lambda: None)
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
      entry.validate_entry_uniqueness(self._servo_dev_index[entry.id])
      self._servo_dev_index[entry.id] = entry
      all_servo_devs.append(entry)
      if entry.dev_template.IS_HUB_SERVO:
        hub_servos.append(entry)
      self._solo_devices[entry.id] = entry
    # Go over the devices that are not hub servos, and see if they belong
    # to a cluster by checking if they have a hub for them.
    while all_servo_devs:
      a_servo = all_servo_devs.pop()
      for hub_servo in hub_servos:
        if a_servo == hub_servo:
          continue
        if UsbHierarchy.DevOnHubPortFromSysfs(hub_servo.hub_stub,
                                              a_servo.dev_path):
          a_servo.set_cluster_root(hub_servo)
          self._cluster_root_servos[hub_servo.id] = hub_servo
          self._cluster_non_root_servos[a_servo.id] = a_servo
          self._solo_devices.pop(hub_servo.id, None)
          self._solo_devices.pop(a_servo.id, None)
          break

  def get_entry(self, vid, pid, serial):
    """Return ServoDeviceEntry for specific identifier.

    Args:
      vid: device vendor ID
      pid: device product ID
      serial: device serial name

    Returns:
      ServoDeviceEntry for the device if known, None otherwise.
    """
    return self._servo_dev_index[(vid, pid, serial)]

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
        return list(dev.cluster_root.cluster_members.values())
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