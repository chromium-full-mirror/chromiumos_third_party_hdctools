# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Find all devices for a servod instance."""

import logging
import sys

from servo import servo_dev_templates
from servo import servo_parsing
from servo.utils import servo_dev_hierarchy

LOGGER = logging.getLogger('ServoDeviceFinder')

class ServoDeviceFinderError(Exception):
  """ServoDeviceFinderError error class."""

def complete_servod_device_list(devopts, dev_hierarchy, complete_cluster=True):
  """Complete the device list of servod from servod commandline parsing results
  and servo device hierarchy.

  The complete device list is derived from the dev_ids (parsed from the servod
  starting commandline) and the servo device hierarchy in the following ways:
  (1) If dev_ids is empty or all-inclusive, return all the devices in the hierarchy.
  (2) If complete_cluster is True, all member devices in a cluster will be served
      with this servod instance. 
      For any device (e.g. ServoV4) in dev_ids, all its cluster member (i.e. servo
      devices attached to it and its root hub) get pulled into the device list.
  (3) If complete_cluster is False, only the bare minimum devices are pulled into
      this servod instance. 
      For any cluster root device (e.g. ServoV4) in dev_ids, all its cluster member
      get pulled into the device list. For any non-root device in dev_ids, only its
      cluster root gets pulled in. Other devices in the same cluster are not pulled
      in, uless they are already specified in dev_ids.
  (4) If any device cannot be pulled in because it is already used in another servod
      instance, we throw an error and exit servod.

  Args:
    devopts: devopts parsed from the servod starting commandline, which may include
             a list of device ids (vid, pid, serialname)
    dev_hierarchy: a ServoDeviceHierarchy generated when the servod starts

  Returns:
    A list representing the complete device list of servo. Each entry is a
    ServoDeviceEntry.
  """
  if not devopts:
    return list(dev_hierarchy.get_all_entries().values())
  dev_list = set()
  for one_dev_opts in devopts:
    (vid, pid, serial) = (one_dev_opts.vendor, one_dev_opts.product,
       one_dev_opts.serialname)
    dev_entry = _find_one_device(vid, pid, serial, dev_hierarchy)
    dev_entry.devopts = one_dev_opts
    dev_list.add(dev_entry)
    if dev_entry.is_cluster_root():
      dev_list.update(dev_entry.cluster_members)
    if dev_entry.is_in_cluster():
      if complete_cluster:
        for member in dev_entry.cluster_root.cluster_members:
          # TODO(konmari): find out what args based on device type
          servo_parsing.inherit_opts(member.devopts, one_dev_opts,
            ['board', 'model', 'config'])
          dev_list.add(member)
      else:
        dev_list.add(dev_entry.cluster_root)
  return list(dev_list)

def _find_one_device(vid, pid, serial, dev_hierarchy, smart_selection=True):
  """Find 1 device given a dev_id (vid, pid, serial) from the device hierarchy.

  Any of the vid, pid, serial can be None.

  Args:
    vid: vendor id of a device
    pid: product id of a device
    serial: serial name of a device
    dev_hierarchy: a ServoDeviceHierarchy generated when the servod starts
    smart_selection: when user does not provide enough information for picking a
        device (e.g. when vid/pid/serial is None), try selecting a device based
        on each device's priority.

  Returns:
    A device matching the given dev_id in the device hierarchy.

  Raises:
    ServoDeviceFinderError: 0 or more than 1 device found with the dev_id
  """
  if (not vid) and (not pid) and (not serial):
    candidates = list(dev_hierarchy.get_all_entries().values())
  else:
    candidates = list(dev_hierarchy.get_entries(vid, pid, serial))

  # TODO(konmari): remove all busy devices based on scratch

  if len(candidates) < 1:
    LOGGER.error('Cannot find a servo device with pid: %s, vid: %s, serial: %s'
      % (vid, pid, serial))
    sys.exit(1)
  if len(candidates) > 1:
    # when user does not provide enough information for picking a device (e.g. when
    # vid/pid/serial is None), try selecting a device based on each device's priority.
    if smart_selection:
      prioritized_devs = servo_dev_hierarchy.ServoDeviceEntry.generate_device_priority(candidates)
      candidates = servo_dev_hierarchy.ServoDeviceEntry.most_prirotized_devices(prioritized_devs)
    if len(candidates) > 1:
      # TODO(konmari): add a device choosing interactive menu
      LOGGER.error('Found more than 1 servo device with pid: %s, vid: %s, serial: %s'
        % (vid, pid, serial))
      sys.exit(1)
  return candidates[0]
