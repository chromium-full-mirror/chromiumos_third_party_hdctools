# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Device tool to manage the (usb) servo device."""

import collections
import os
import subprocess
import time

import servo.servo_interfaces
from servo.drv.pty_driver import ptyError
import servo.utils.usb_hierarchy as uh
from . import tool
from servo_mfg import tiny_servod
import usb

# VID to find all servo devices.
SERVO_VID = 0x18d1

# List of PID supported for power-cycle. For now, it's only v4 and v4p1.
# 0x520d: v4p1, 0x501b: v4
PWR_CYCLE_PIDS = [0x520d, 0x501b]


class DeviceError(Exception):
  """Device tool error class."""
  pass


class Device(tool.Tool):
  """Class to implement various subtools to manage a servo devices."""

  # Lookup table for action on uhubctl.
  ACTION_DICT = {'on': 1,
                 'off': 0,
                 'reset': 2}

  # Repetitions to perform on the uhubctl command to get it to trigger.
  REPS = 100

  # Time to sleep after reset to let kernel handle sysfs files
  RESET_DEBOUNCE_S = 2

  # time to sleep for the servo device to reenumerate.
  MAX_REINIT_SLEEP_S = 8

  # Polling intervals to find the |devnum| file for reset device.
  REINIT_POLL_SLEEP_S = 0.1

  # Time to sleep and attempts to interact with servo console after reboot.
  REBOOT_SLEEP_S = 1
  REBOOT_TIMEOUT_ATTEMPTS = 4

  # Time to sleep after power off
  PWR_OFF_SLEEP_S = 1

  # Dictionary to look up the device's servo console USB interface number.
  # TODO(coconutruben): remove this once we have servo device templates that
  # contain all this information.
  USB_CONSOLE_IFACE = collections.defaultdict(dict)
  USB_CONSOLE_IFACE[0x18d1][0x501a] = 3 # servo_micro
  USB_CONSOLE_IFACE[0x18d1][0x501b] = 0 # servo_v4
  USB_CONSOLE_IFACE[0x18d1][0x5020] = 0 # sweetberry
  USB_CONSOLE_IFACE[0x18d1][0x520d] = 0 # servo_v4p1
  USB_CONSOLE_IFACE[0x18d1][0x5041] = 0 # c2d2

  @property
  def help(self):
    """Tool help message for parsing."""
    return 'Manage servo device.'

  def _usb_path(self, serial):
    """Helper to get the device path.

    Args:
      serial: str, servo serial

    Returns:
      /sys/bus/usb/devices/ path to servo with |serial| or None if not found
    """
    # This list is used to find all servos on the system.
    vid_pid_list = [(SERVO_VID, None)]
    devs = uh.Hierarchy.GetAllUsbDeviceSysfsPaths(vid_pid_list)
    for dev_path in devs:
      dev_serial = uh.Hierarchy.SerialFromSysfs(dev_path)
      if dev_serial == serial:
        return dev_path
    return None

  def reboot(self, args):
    """Reboot the device."""
    # First, let's make sure the device exists.
    e = None
    dev_path = self._usb_path(args.serial)
    if not dev_path:
      self.error('Device with serial %r not found.', args.serial)
    vid = uh.Hierarchy.VendorIDFromSysfs(dev_path)
    pid = uh.Hierarchy.ProductIDFromSysfs(dev_path)
    devnum = uh.Hierarchy.DevNumFromSysfs(dev_path)
    if (vid not in self.USB_CONSOLE_IFACE or
        pid not in self.USB_CONSOLE_IFACE[vid]):
      self.error('Device %04x:%04x %s does not support reboot',
                 vid, pid, args.serial)
    iface = self.USB_CONSOLE_IFACE[vid][pid]
    ts = tiny_servod.TinyServod(vid, pid, iface, args.serial)
    ts.pty._issue_cmd_get_results('chan 0', ['>'])
    try:
      ts.pty._issue_cmd_get_results('reboot', ['>'])
    except ptyError as e:
      # We except a no-data error here occasionally, if the reboot
      # was too quick for the console to send a newline. That's fine.
      if 'No data was sent from the pty' not in str(e):
        raise
    # Make sure the device comes back with a new devnum before attempting
    # to comminucate with it.
    self._check_devnum_reset(dev_path, devnum, 'reboot')
    for i in range(self.REBOOT_TIMEOUT_ATTEMPTS):
      try:
        # Make sure the device is back
        self._logger.debug('Attempt %d to interact with console post reboot',
                           i+1)
        ts.reinitialize()
        ts.pty._issue_cmd_get_results('chan 0', ['>'])
        ts.pty._issue_cmd_get_results('serialno',
                                      [r'Serial number: ([^\r\n]+)[\n\r]+'])
        ts.pty._issue_cmd_get_results('chan restore', ['>'])
        return
      except Exception as e:
        # store the exception in e here so that we have access to it later
        # if we need to print it.
        self._logger.debug(e)
      time.sleep(self.REBOOT_SLEEP_S)
    self.error('Device %04x:%04x %s issue after reboot: %s',
               vid, pid, args.serial, e)

  def usb_path(self, args):
    """Retrieve the usb sysfs path for a serial number."""
    dev_path = self._usb_path(args.serial)
    if dev_path:
      self._logger.info(dev_path)
    else:
      self.error('Device with serial %r not found.', args.serial)

  def usb_comms(self, args):
    """Test whether usb communication works for device at |args.serial|.

    This tool tries to identify USB devices that are still enumerated on the
    the system, but that fail to respond to USB communication e.g. because their
    data lines have been muxed off but the system has not registered that.

    The detection is done by using cached values of the device on sysfs to find
    the device on pyusb, and then attempting to read the iSerial, as this
    requires opening the device and communicating with it.
    """
    dev_path = self._usb_path(args.serial)
    if not dev_path:
      self.error('Device with serial %r not found.', args.serial)
    # Now, retrieve busnum and devnum using sysfs as those values are cached.
    devnum = uh.Hierarchy.DevNumFromSysfs(dev_path)
    busnum = uh.Hierarchy.BusNumFromSysfs(dev_path)
    dev = usb.core.find(address=devnum, bus=busnum)
    if dev is None:
      self.error('Device with serial %r not found on pyusb.', args.serial)
    # The real experiment - reading some data.
    try:
      _ = usb.util.get_string(dev, dev.iSerialNumber)
    except ValueError as e:
      self.error('Device with serial %r has USB comms issues. %s', args.serial,
                 e)

  def _run_uhubctl_command(self, hub, port, action):
    """Build |uhubctl| command performing |action| on |hub|'s |port|.

    Args:
      hub: hub-port path i.e. /sys/bus/usb/devices/ dirname of the hub
      port: str, port number on the hub
      action: one of 'on', 'off', 'reset'
    """
    cmd = self._build_and_assert_uhubctl(hub=hub, port=port)
    if action not in self.ACTION_DICT:
      self.error('Action %s unknown', action)
    action_number = self.ACTION_DICT[action]
    # expand command to perform the uhubctl action.
    cmd = cmd + ['-a', str(action_number), '-r', str(self.REPS)]
    try:
      subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
      self.error('Error performing the uhubctl command. ran: "%s". %s.',
                 ' '.join(cmd), str(e))

  def _build_and_assert_uhubctl(self, hub=None, port=None):
    """Assert uhubctl exists and hub/port are known to it (if provided).

    Args:
      hub: hub-port path i.e. /sys/bus/usb/devices/ dirname of the hub
      port: str, port number on the hub

    Returns:
      cmd: a list of args to call the uhubctl command (at hub/port if provided)
    """
    cmd = ['sudo', 'uhubctl']
    try:
      subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
      self.error('uhubctl not available. Be sure to run as sudo. %s',
                 str(e))
    if hub is not None and port is not None:
      # expand the command to check for hub and port existing.
      # casting port to str to ensure we don't accidently pass an int.
      cmd = cmd + ['-l', hub, '-p', str(port)]
      try:
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)
      except subprocess.CalledProcessError as e:
        self.error('hub %s with port %s unknown to uhubctl. '
                   'Be sure the hub is a supported smart hub. %s', hub, port,
                   str(e))
    return cmd

  def _get_hub_and_port(self, dev_path, pid):
    """Get the external hub and port paths for a given |pid|.

    This is its own function, as different devices might have a different
    internal topology. This method has to guarantee to implement all pids
    in PWR_CYCLE_PIDS.

    Args:
      dev_path: /sys/bus/usb/devices/ path for servo
      pid: servo pid

    Returns:
      (hub, port, hub3,) tuple, where hub is the external hub that the
                         servo is on port is the port on that hub that the
                         servo is on. hub3 is the usb3 virtual hub of the same
                         physical hub. It will be None if it does not exist
                         (hub only enumerated in usb2)
    """
    # NOTE: if a servo device or configuration should be supported, this is the
    # spot to implement it. If more devices get implemented here, make sure to
    # document the setup under which the user can expect it to work and for the
    # code to guard against other setups.
    # For example: if a servo micro is attached to a servo v4, the code to reset
    # the micro should not just reset the hub that the v4 is hanging on, as that
    # would reset both.
    # TODO(coconutruben): make pid permission more robust once we have device
    # templates.
    if pid in PWR_CYCLE_PIDS:
      # For servo v4(p1), the dev_path points to the stm that's hanging on
      # an internal usb hub.
      internal_hub = uh.Hierarchy.GetSysfsParentHubStub(dev_path)
      smart_hub_path = uh.Hierarchy.GetSysfsParentHubStub(internal_hub)
      if smart_hub_path:
        # The internal hub is hanging on the smart hub's port. So the last
        # index is the port number.
        port = internal_hub.rsplit('.', 1)[-1]
        smart_hub = os.path.basename(smart_hub_path)
        # |internal_hub| is always on usb2. Let's see if this hub also
        # enumerated on usb3.
        smart_hub_bus, smart_hub_port_path = smart_hub.split('-')
        busnum = int(smart_hub_bus)
        busnum3 = uh.Hierarchy.ComplementBusNum(busnum)
        smart_hub3 = None
        if busnum3:
          smart_hub3 = '%d-%s' % (busnum3, smart_hub_port_path)
          smart_hub3_path = os.path.join(os.path.dirname(smart_hub_path),
                                         smart_hub3)
          if not os.path.exists(smart_hub3_path):
            # set back to None
            smart_hub3 = None
        return (smart_hub, port, smart_hub3)
      self.error('Device does not seem to be hanging on a (smart) hub. %r',
                 dev_path)

    self.error('Unimplemented pid: %04x', pid)

  def _check_devnum_reset(self, dev_path, devnum, action):
    """Check that the |devnum| has changed after a reset/reboot/power-cycle

    Args:
      dev_path: device sysfs path
      devnum: int, usb devnum (original devnum, before reset action)
      action: str, action performed (used to print better errors/logs

    Note: this helper will call self.error() (and thus exit) if
    - the devnum does not change
    - it fails to read the devnum after self.MAX_REINIT_SLEEP_S
    """
    # Sleep a bit to let the device fully fall off, and the sysfs files be
    # renewed.
    time.sleep(self.RESET_DEBOUNCE_S)
    # For |MAX_REINIT_SLEEP_S| seconds, try to find the new devnum for the
    # device.
    end = time.time() + self.MAX_REINIT_SLEEP_S
    while time.time() < end:
      try:
        # check devnum reset
        if devnum == uh.Hierarchy.DevNumFromSysfs(dev_path):
          self.error('%r likely unsuccessful. devnum stayed the same.', action)
        # If |devnum| changed, then the goal is fulfilled. Move on.
        break
      except uh.HierarchyError:
        # The device might not have reenumerated yet. Sample again.
        time.sleep(self.REINIT_POLL_SLEEP_S)
    else:
      # The while loop finished without breaking out e.g. we never read the
      # |devnum| file successfully.
      self.error('unable to read device |devnum| file after %ds. Giving up.',
                 self.MAX_REINIT_SLEEP_S)

  def power_cycle_force(self, args):
    """Perform a full power-cycle with off/on rather than just reset."""
    self.power_cycle(args, force=True)

  def power_cycle(self, args, force=False):
    """Perform a power-cycle on the device using uhubctl.

    uhubctl exposes multiple knobs to control the power-cycling of a port.
    This method uses the 'reset' knob by default. However, if the user
    specifies |force|=True, it will issue an 'off' request, wait for
    |PWR_OFF_SLEEP_S| seconds, before issueing an 'on' request. For some hubs
    this has proven itself more reliably than a reset request.

    Args:
      force: bool, whether to perform a full power-cycle or just a reset
    """
    self._build_and_assert_uhubctl()
    dev_path = self._usb_path(args.serial)
    if not dev_path:
      self.error('Device with serial %r not found.', args.serial)
    pid = uh.Hierarchy.ProductIDFromSysfs(dev_path)
    if pid not in PWR_CYCLE_PIDS:
      self.error('pid: 0x%04x currently not supported for usb power cycling. '
                 'Please use one of: %s', pid, ', '.join('0x%04x' % p for p in
                                                         PWR_CYCLE_PIDS))
    # get devnum, and store it
    devnum = uh.Hierarchy.DevNumFromSysfs(dev_path)
    # extract the hub and check whether it's on uhubctl
    hub, port, hub3 = self._get_hub_and_port(dev_path, pid)
    if force:
      # The sandwich (if usb2 and usb3 are available) is to first turn
      # off usb2 and then usb3, before unrolling that operation.
      self._run_uhubctl_command(hub=hub, port=port, action='off')
      if hub3 is not None:
        self._run_uhubctl_command(hub=hub3, port=port, action='off')
      time.sleep(self.PWR_OFF_SLEEP_S)
      if hub3 is not None:
        self._run_uhubctl_command(hub=hub3, port=port, action='on')
      self._run_uhubctl_command(hub=hub, port=port, action='on')
    else:
      # Just perform a reset. Do not perform a reset on hub3 and hub, as
      # this will lead to a double reset. For reset, rely on the uhubctl
      # internal duality management.
      self._run_uhubctl_command(hub=hub, port=port, action='reset')

    self._check_devnum_reset(dev_path, devnum, 'power-cycle')
    # At the end, no error was encountered, so indicate belief that reset was
    # successful.
    self._logger.info('Successfully power-cycled device with serial %r. '
                      '(At least reasonably confident).', args.serial)

  def add_args(self, tool_parser):
    """Add the arguments needed for this tool."""
    subcommands = tool_parser.add_subparsers(dest='command')
    tool_parser.add_argument('-s', '--serial', required=True,
                             help='serial of servo device on the system.')
    subcommands.add_parser('power-cycle-force',
                           help='Issue full off/on sequence rather than reset.')
    subcommands.add_parser('power-cycle',
                           help='Power cycle device using uhubctl if on smart '
                                'hub')
    subcommands.add_parser('reboot', help='Reboot the device MCU')
    subcommands.add_parser('usb-comms',
                           help='Test whether USB communication on the device '
                           'works. Exit code 1 if USB communication broken, '
                           'and exit code 0 otherwise. Requires root.')
    subcommands.add_parser('usb-path',
                           help='Show /sys/bus/usb/devices path of the device')
