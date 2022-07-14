# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Discover devices for a servod instance."""

import logging
import sys

from servo import servo_dev_templates
from servo import servo_parsing
from servo.utils import servo_dev_hierarchy

class ServoDeviceFinderError(Exception):
  """ServoDeviceFinderError error class."""

class ServoDeviceFinder(object):
  """ Discover devices to be served by a servod instance."""

  def __init__(self, devopts, dev_hierarchy, scratch):
    """Set up the servo device finder.

    Args:
      devopts: a list of device opts parsed from the servod starting commandline
      dev_hierarchy: a ServoDeviceHierarchy generated when the servod starts
      scratch: ServoSratch that manages information across different servod instances.
    """
    self._logger = logging.getLogger(type(self).__name__)
    self._devopts = devopts
    self._dev_hierarchy = dev_hierarchy
    self._scratch = scratch

  def discover_servos(self, complete_cluster=True):
    """Complete the device list of servod from servod commandline device opts
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
      complete_cluster: whether to complete device clusters in the device list

    Returns:
      A list representing the complete device list of servo. Each entry is a
      ServoDeviceEntry.
    """
    if not self._devopts:
      return list(self._dev_hierarchy.get_all_entries().values())
    invocation_devs = set()
    for one_dev_opts in self._devopts:
      (vid, pid, serial) = (one_dev_opts.vendor, one_dev_opts.product,
         one_dev_opts.serialname)
      dev_entry = self._find_one_device(vid, pid, serial)
      dev_entry._devopts = one_dev_opts
      self._logger.info('Pull in device %s as it is included in invocation args.', dev_entry)
      self._pull_in_device(dev_entry, invocation_devs)
    dev_list = invocation_devs.copy()
    for dev_entry in invocation_devs:
      if dev_entry.is_cluster_root():
        for member in dev_entry.cluster_members:
          if member == dev_entry:
            continue
          self._logger.info('Pull in device %s as it is a child of device %s.', member, dev_entry)
          self._complete_devopts(member, dev_entry)
          self._pull_in_device(member, dev_list)
      elif dev_entry.is_in_cluster():
        self._logger.info('Pull in device %s as it is the parent hub of device %s.',
          dev_entry.cluster_root, dev_entry)
        self._complete_devopts(dev_entry.cluster_root, dev_entry)
        self._pull_in_device(dev_entry.cluster_root, dev_list)
        if complete_cluster:
          for member in dev_entry.cluster_root.cluster_members:
            if member == dev_entry:
              continue
            self._logger.info('Pull in device %s as it is a sibling of device %s.', member)
            self._complete_devopts(member, dev_entry)
            self._pull_in_device(member, dev_list)
    # TODO(konmari): validate that all devices are available based on scratch
    return list(dev_list)

  def _find_one_device(self, vid, pid, serial, smart_selection=True):
    """Find 1 device given a dev_id (vid, pid, serial) from the device hierarchy.

    Any of the vid, pid, serial can be None.

    Args:
      vid: vendor id of a device
      pid: product id of a device
      serial: serial name of a device
      smart_selection: when user does not provide enough information for picking a
          device (e.g. when vid/pid/serial is None), try selecting a device based
          on each device's priority.

    Returns:
      A device matching the given dev_id in the device hierarchy.

    Raises:
      ServoDeviceFinderError: 0 or more than 1 device found with the dev_id
    """
    if (not vid) and (not pid) and (not serial):
      candidates = list(self._dev_hierarchy.get_all_entries().values())
    else:
      candidates = list(self._dev_hierarchy.get_entries(vid, pid, serial))

    if len(candidates) < 1:
      self._logger.error('Cannot find a servo device with pid: %s, vid: %s, serial: %s'
        % (vid, pid, serial))
      sys.exit(1)
    if len(candidates) > 1:
      # when user does not provide enough information for picking a device (e.g. when
      # vid/pid/serial is None), try selecting a device based on each device's priority.
      if smart_selection:
        self._logger.info('Found > 1 servo devices with pid: %s, vid: %s, serial: %s. '
          'Try to smartly select a device among device candidates: %s'
          % (vid, pid, serial, candidates))
        prioritized_devs = servo_dev_hierarchy.ServoDeviceHierarchy.generate_device_priority(candidates)
        candidates = servo_dev_hierarchy.ServoDeviceHierarchy.most_prirotized_devices(prioritized_devs)
      if len(candidates) > 1:
        # TODO(konmari): add a device choosing interactive menu
        self._logger.error('Found more than 1 servo device with pid: %s, vid: %s, serial: %s. '
          'Device candidates: %s' % (vid, pid, serial, candidates))
        sys.exit(1)
    self._logger.debug('Found device %s with pid: %s, vid: %s, serial: %s'
      % (candidates[0], vid, pid, serial))
    return candidates[0]

  def _complete_devopts(self, new_dev, old_dev):
    """
    """
    # TODO(konmari): find out what args based on device type
    servo_parsing.inherit_opts(new_dev.devopts, old_dev.devopts, ['board', 'model', 'config'])
    # TODO(konmari): if prefix is missing, generate something

  def _pull_in_device(self, dev, dev_list):
    # TODO(konmari): check through scratch that the device is not served by another servod instance
    dev_list.add(dev)