# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Discover devices for a servod instance."""

import logging
import os
import select
import sys

from servo import servo_dev_templates
from servo import servo_parsing
from servo.utils import servo_dev_hierarchy

# Timeout in seconds of user interactive menu
INTERATIVE_MENU_TIMEOUT_SECONDS = 30

class ServoDeviceFinderError(Exception):
  """ServoDeviceFinderError error class."""

class ServoDeviceFinder(object):
  """ Discover devices to be served by a servod instance."""

  def __init__(self, devopts, dev_hierarchy, scratch, choose_device=None):
    """Set up the servo device finder.

    Args:
      devopts: a list of device opts parsed from the servod starting commandline
      dev_hierarchy: a ServoDeviceHierarchy generated when the servod starts
      scratch: ServoSratch that manages information across different servod instances.
      choose_device: a param used to mock behavior for user interactively choose
        device on the cmd line. It should only be not None in tests.
    """
    self._logger = logging.getLogger('ServoDeviceFinder')
    self._devopts = devopts
    self._dev_hierarchy = dev_hierarchy
    self._scratch = scratch
    self.choose_device = choose_device if choose_device is not None else self._choose_device

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

    Raises:
      ServoDeviceFinderError: if a device cannot be pulled because it is already served
      by another servod instance
    """
    self._logger.info('Start discovering all devices for this servod instance.')
    if not self._devopts:
      return list(self._dev_hierarchy.get_all_entries().values())

    # First pull in all the devices included in the command line invocation
    invocation_devs = set()
    for one_dev_opts in self._devopts:
      (vid, pid, serial) = (one_dev_opts.vendor, one_dev_opts.product,
         one_dev_opts.serialname)
      dev_entry = self._find_one_device(vid, pid, serial)
      dev_entry.devopts = one_dev_opts
      self._logger.info('Pull in device %s as it is included in invocation args.', dev_entry)
      invocation_devs.add(dev_entry)

    # Then pull in all the devices connecting to the devices included in command
    # line invocation
    dev_list = invocation_devs.copy()
    for dev_entry in invocation_devs:
      # for a root hub device, include all its cluster member
      if dev_entry.is_cluster_root():
        for member in dev_entry.cluster_members:
          if member not in dev_list:
            self._logger.info('Pull in device %s as it is a child of device %s.', member, dev_entry)
            self._complete_devopts(member, dev_entry)
            dev_list.add(member)
      # for a non-root device in a cluster, include its root hub
      elif dev_entry.is_in_cluster():
        if dev_entry.cluster_root not in dev_list:
          self._logger.info('Pull in device %s as it is the parent hub of device %s.',
          dev_entry.cluster_root, dev_entry)
          self._complete_devopts(dev_entry.cluster_root, dev_entry)
          dev_list.add(dev_entry.cluster_root)
        # also include the other cluster members if we would like complete clusters served
        # by one servod instance
        if complete_cluster:
          for member in dev_entry.cluster_root.cluster_members:
            if member not in dev_list:
              self._logger.info('Pull in device %s as it is a sibling of device %s.', member, dev_entry)
              self._complete_devopts(member, dev_entry)
              dev_list.add(member)

    # TODO(konmari): validate that all devices are available based on scratch
    # TODO(konmari): validate that all devices have valid devopts
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
      ServoDeviceFinderError: no device can be found
      ServoDeviceFinderError: multiple devices are found and user fail to pick one from them
    """
    input_str = 'vid: %s pid: %s serial: %s' % (vid, pid, serial)
    if (not vid) and (not pid) and (not serial):
      candidates = list(self._dev_hierarchy.get_all_entries().values())
    else:
      candidates = list(self._dev_hierarchy.get_entries(vid, pid, serial))

    if len(candidates) < 1:
      raise ServoDeviceFinderError('Cannot find a servo device with %s' % input_str)
    candidate = candidates[0]
    if len(candidates) > 1:
      self._logger.info('Found > 1 servo devices with %s', input_str)
      # when user does not provide enough information for picking a device (e.g. when
      # vid/pid/serial is None), try selecting a device based on each device's priority.
      if smart_selection:
        self._logger.info('Try to smartly select a device among device candidates: %s', candidates)
        prioritized_devs = servo_dev_hierarchy.ServoDeviceHierarchy.generate_device_priority(candidates)
        candidates = servo_dev_hierarchy.ServoDeviceHierarchy.most_prirotized_devices(prioritized_devs)
        candidate = candidates[0]
      if len(candidates) > 1:
        self._logger.info('')
        self._logger.info('We have found multiple devices that match args provided %s', input_str)
        candidate = self.choose_device(candidates)
        if not candidate:
          raise ServoDeviceFinderError('User does not choose a valid device for %s. Device candidates: %s' %
            (input_str, candidates))
    self._logger.debug('Found device %s with %s', candidate, input_str)
    return candidate

  def _complete_devopts(self, new_dev, old_dev):
    """Complete the device options for a device based on the ones of another device.

    Args:
      new_dev: a ServoDeviceEntry whose device options is to be generated
      old_dev: a ServoDeviceEntry which already has device options
    """
    # TODO(konmari): find out what args based on device type
    servo_parsing.inherit_opts(new_dev.devopts, old_dev.devopts, ['board', 'model', 'config'])
    # TODO(konmari): if prefix is missing, generate a prefix

  def choose_main_device(self, devs):
    """Choose the main device of the servod instance.

    The main device is the servo device that processes controls sent to the servod instance
    by default. It receives the prefix '' and 'main'.

    Args:
      devs: a list representing the complete device list of servo. Each entry is a ServoDeviceEntry.

    Returns:
      A device as the main device.

    Raises:
      ServoDeviceFinderError: User does not pick a main device from multiple candidates
    """
    prioritized_devs = servo_dev_hierarchy.ServoDeviceHierarchy.generate_device_priority(devs)
    user_chosen_mains = prioritized_devs[servo_dev_hierarchy.PRIORITY_MAIN_DEV]
    if user_chosen_mains:
      self._logger.info('User have selected the main device.')
      candidate = user_chosen_mains[0]
      if len(user_chosen_mains) > 1:
        self._logger.info('')
        self._logger.info('Please pick 1 of the following devices as the main device.')
        candidate = self.choose_device(user_chosen_mains)
    else:
      self._logger.info('User did not select the main device. Servod will try to choose one.')
      candidates = servo_dev_hierarchy.ServoDeviceHierarchy.most_prirotized_devices(prioritized_devs)
      candidate = candidates[0]
      if len(candidates) > 1:
        self._logger.info('')
        self._logger.info('Please pick 1 of the following devices as the main device.')
        candidate = self.choose_device(candidates)
    if not candidate:
      raise ServoDeviceFinderError('No device is picked as the main device.')
    self._logger.info('Main device is chosen as the device %s', candidate)
    return candidate

  def _choose_device(self, devs):
    """Let user choose a device from available list of unique devices.

    Args:
      devs: a list of ServoDeviceEntry devices

    Returns:
      ServoDeviceEntry for a single device, or None if user does not choose
    """
    logging.info('')
    for i, dev in enumerate(devs):
      logging.info("Press '%d' for device %s", i, dev)

    # Check if stdin exists
    if not os.isatty(sys.stdin.fileno()):
      logging.warning('No stdin exists for user to choose a device.')
      return None

    (rlist, _, _) = select.select([sys.stdin], [], [], INTERATIVE_MENU_TIMEOUT_SECONDS)
    if not rlist:
      logging.warning('Timed out waiting for your choice\n')
      return None

    rsp = rlist[0].readline().strip()
    try:
      rsp = int(rsp)
    except ValueError:
      logging.warning('%s not a valid choice ... ignoring', rsp)
      return None

    if rsp < 0 or rsp >= len(devs):
      logging.warning('%s outside of choice range ... ignoring', rsp)
      return None

    logging.info('')
    dev = devs[rsp]
    logging.info('Chose %d ... device %s', rsp, dev)
    logging.info('')
    return dev

  def generate_prefixes(self, devs, main_dev):
    """Generate a prefix for the device if it does not have one.

    Args:
      devs: a list of ServoDeviceEntry devices
    """
    known_prefixes = set()
    devs_without_prefix = []
    for dev in devs:
      if dev == main_dev:
        dev.devopts.prefix = servo_dev_templates.MAIN_DEV_PREFIX
        known_prefixes.update(servo_dev_templates.MAIN_DEV_PREFIXES)
        self._logger.debug('Device %s is the main device and is given prefix %s',
            dev, servo_dev_templates.MAIN_DEV_PREFIXES)
      else:
        if dev.devopts.prefix in servo_dev_templates.MAIN_DEV_PREFIXES:
          dev.devopts.prefix = None
        if dev.devopts.prefix:
          known_prefixes.add(dev.devopts.prefix)
          self._logger.debug('Device %s is given prefix %s during invocation',
            dev, dev.devopts.prefix)
        else:
          devs_without_prefix.append(dev)
    # auto generate prefix use device type and the last 4 digit of serial
    for dev in devs_without_prefix:
      prefix = '%s-%s' % (dev.dev_template.TYPE, dev.serial[-4:])
      if prefix not in known_prefixes:
        dev.devopts.prefix = prefix
      else:
        suffix = 2
        while ('%s-%s' % (prefix, suffix)) in known_prefixes:
          suffix += 1
        dev.devopts.prefix = '%s-%s' % (prefix, suffix)
      known_prefixes.add(dev.devopts.prefix)
      self._logger.debug('Device %s is given prefix %s which is automatically generated',
        dev, dev.devopts.prefix)
