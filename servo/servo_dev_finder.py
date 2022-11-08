# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Discover devices for a servod instance."""

from enum import Enum
import collections
import logging
import os
import select
import sys

from servo import servo_dev_templates
from servo import servo_parsing
from servo.utils import scratch
from servo.utils import servo_dev_hierarchy

# Timeout in seconds of user interactive menu
INTERATIVE_MENU_TIMEOUT_SECONDS = 30


class ServoDeviceFinderError(Exception):
  """ServoDeviceFinderError error class."""

class ServoDeviceDiscoveryMode(Enum):
  """Indicates how much auto discovery can be performed by ServoDeviceFinder."""

  # Enable full auto discovery
  # 1. Pull in complete clusters of the devices provided through cmdline and rc file
  # 2. When user does not provide enough information for a device on cmdline
  #    and rc file (e.g. when vid/pid/serial is None), try selecting a device based
  #    on each device's priority.
  FULL_AUTO = 0

  # Enable minimum auto discovery
  # 1. Pull in bare minimum devices that relate to the devices provided through
  #    cmdline and rc file. For any root hub device (e.g. ServoV4), all its cluster
  #    member are pulled in. For any non-root-hub device, only its
  #    cluster root gets pulled in.
  # 2. When user does not provide enough information for a device on cmdline
  #    and rc file (e.g. when vid/pid/serial is None), try selecting a device based
  #    on each device's priority.
  MIN_AUTO = 1

  # No auto discovery
  # 1. Only pull in the devices provided through cmdline and rc file.
  # 2. When user does not provide enough information for a device on cmdline
  #    and rc file (e.g. when vid/pid/serial is None), let user choose through
  #    an interactive cmdline menu.
  NO_AUTO = 2

class ServoDeviceFinder(object):
  """ Discover devices to be served by a servod instance."""

  def __init__(self, devopts, devopts_generator, dev_hierarchy, scratch, discover_mode,
    choose_device=None):
    """Set up the servo device finder.

    Args:
      devopts: a list of device opts parsed from the servod starting commandline
      default_devopts_generator: a function that generates a default devopts
        for devices pulled in during device auto-discovery.
      dev_hierarchy: a ServoDeviceHierarchy generated when the servod starts
      scratch: ServoSratch that manages information across different servod instances.
      discover_mode: ServoDeviceDiscoveryMode that indicates how much auto discovery
        can be performed by the finder when discovering devices.
      choose_device: a param used to mock behavior for user interactively choose
        device on the cmd line. It should only be not None in tests.
    """
    self._logger = logging.getLogger('ServoDeviceFinder')
    self._devopts = devopts
    self._devopts_generator = devopts_generator
    self._dev_hierarchy = dev_hierarchy
    self._scratch = scratch
    self.discover_mode = discover_mode
    self.choose_device = choose_device if choose_device is not None else self._choose_device

  def discover_servos(self):
    """Complete the device list of servod from servod commandline device opts
    and servo device hierarchy.

    The complete device list is derived from the invocation_devs (parsed from the servod
    starting commandline) and the servo device hierarchy in the following ways:
    (1) If invocation_devs is empty or all-inclusive, return all the devices in the hierarchy.
    (2) If discover_mode is FULL_AUTO, all member devices in a cluster will be served
        with this servod instance.
        For any device (e.g. ServoV4) in invocation_devs, all its cluster member (i.e. servo
        devices attached to it and its root hub) get pulled into the device list.
    (3) If discover_mode is MIN_AUTO, only the bare minimum devices are pulled into
        this servod instance.
        For any cluster root device (e.g. ServoV4) in invocation_devs, all its cluster member
        get pulled into the device list. For any non-root device in invocation_devs, only its
        cluster root gets pulled in. Other devices in the same cluster are not pulled
        in, uless they are already specified in invocation_devs.
    (4) If discover_mode is NO_AUTO, only pull in the devices in invocation_devs.
    (5) If any device cannot be pulled in because it is already used in another servod
        instance, we throw an error and exit servod.

    Returns:
      A list representing the complete device list of servo. Each entry is a
      ServoDeviceEntry.

    Raises:
      ServoDeviceFinderError: if a device cannot be pulled because it is already served
      by another servod instance
    """
    self._logger.info('Start discovering all devices for this servod instance.')
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
    if self.discover_mode != ServoDeviceDiscoveryMode.NO_AUTO:
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
          if  self.discover_mode == ServoDeviceDiscoveryMode.FULL_AUTO:
            for member in dev_entry.cluster_root.cluster_members:
              if member not in dev_list:
                self._logger.info('Pull in device %s as it is a sibling of device %s.', member, dev_entry)
                self._complete_devopts(member, dev_entry)
                dev_list.add(member)

    dev_list = list(dev_list)
    self.validate_device_availability(dev_list)
    return dev_list

  def _find_one_device(self, vid, pid, serial):
    """Find 1 device given a dev_id (vid, pid, serial) from the device hierarchy.

    Any of the vid, pid, serial can be None.

    Args:
      vid: vendor id of a device
      pid: product id of a device
      serial: serial name of a device

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
      if self.discover_mode != ServoDeviceDiscoveryMode.NO_AUTO:
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
    new_dev.devopts = self._devopts_generator()
    for arg in ['board', 'model', 'config', 'noautoconfig']:
      setattr(new_dev.devopts, arg, getattr(old_dev.devopts, arg))

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
    # a dictionary of devices without prefix, keyed by device type
    devs_without_prefix = collections.defaultdict(lambda: [])
    for dev in devs:
      dev_prefix = set(dev.devopts.prefix) - known_prefixes
      # handle main device's prefix
      if dev == main_dev:
        if len(dev_prefix) == 0:
          devs_without_prefix[dev.dev_template.TYPE].append(dev)
        dev_prefix.update(servo_dev_templates.MAIN_DEV_PREFIXES)
        dev.devopts.prefix = list(dev_prefix)
        known_prefixes.update(dev_prefix)
        self._logger.debug('Device %s is the main device and is given prefix %s',
          dev, servo_dev_templates.MAIN_DEV_PREFIXES)
        continue

      # prevent non-main device to have main device's prefix
      dev_prefix = dev_prefix - set(servo_dev_templates.MAIN_DEV_PREFIXES)

      # handle root device's prefix
      if dev == main_dev.cluster_root:
        if len(dev_prefix) == 0:
          devs_without_prefix[dev.dev_template.TYPE].append(dev)
        dev_prefix.add(servo_dev_templates.ROOT_DEV_PREFIX)
        dev.devopts.prefix = list(dev_prefix)
        known_prefixes.update(dev_prefix)
        self._logger.debug('Device %s is the root device and is given prefix %s',
          dev, servo_dev_templates.ROOT_DEV_PREFIX)
        continue

      # prevent non-root device to have root device's prefix
      dev_prefix = dev_prefix - set([servo_dev_templates.ROOT_DEV_PREFIX])

      # handle all other device's prefix
      dev.devopts.prefix = list(dev_prefix)
      known_prefixes.update(dev_prefix)
      if len(dev_prefix) == 0:
        devs_without_prefix[dev.dev_template.TYPE].append(dev)
      else:
        self._logger.debug('Device %s is given prefix %s during invocation',
          dev, dev_prefix)

    # auto generate prefix based on device type
    for dev_type, devs in devs_without_prefix.items():
      for dev in devs:
        # use the device type as the prefix if it is the only 1 device of the kind
        if len(devs) == 1 and dev_type not in known_prefixes:
          prefix = dev_type
        # otherwise, use device type and the last 4 digit of serial
        else:
          prefix = '%s-%s' % (dev_type, dev.serial[-4:])
        if prefix in known_prefixes:
          suffix = 2
          while ('%s-%s' % (prefix, suffix)) in known_prefixes:
            suffix += 1
          prefix = '%s-%s' % (prefix, suffix)
        dev.devopts.prefix.append(prefix)
        known_prefixes.add(prefix)
        self._logger.debug('Device %s is given prefix %s which is automatically generated',
          dev, prefix)

  def validate_device_availability(self, devs):
    """Check against ServoScratch that all devices are not served by another servod instance.

    Args:
      devs: a list of ServoDeviceEntry devices

    Raises:
      ServoDeviceFinderError: some device is servoed by another servod instance.
    """
    has_error = False
    for servod_instance in self._scratch.GetAllEntries():
      for dev in devs:
        if dev.serial in servod_instance[scratch.SERIAL_KEY]:
          has_error = True
          self._logger.error("Device %s is already served by another servod instance"
            "on port %s", dev, servod_instance[scratch.PORT_KEY])
    if has_error:
      raise ServoDeviceFinderError("Not all devices requested are available right now.")


  def validate_devopts(self, devs):
    """Validate devices have valid devopts.

    Args:
      devs: a list of ServoDeviceEntry devices

    Raises:
      ServoDeviceFinderError: some device does not have 'prefix' attribute
      ServoDeviceFinderError: multiple devices have "main" or "" as 'prefix'
    """
    main_prefix_count = 0
    for dev in devs:
      if not dev.devopts.prefix:
        raise ServoDeviceFinderError("Device %s does not have a prefix." % dev)
      if set(dev.devopts.prefix).intersection(set(servo_dev_templates.MAIN_DEV_PREFIXES)):
        main_prefix_count += 1
    if main_prefix_count > 1:
      raise ServoDeviceFinderError("Multiple devices are chosen as the main device.")
