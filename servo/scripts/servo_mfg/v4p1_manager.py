# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Module to manage one manufacturing round for one v4p1 device."""

import re

from servo_mfg import device_util
from servo_mfg import manager
from servo_mfg import user_input
from servo_mfg.v4p1_manufacturer import V4P1Manufacturer
from servo_mfg.v4p1_tester import V4P1Tester


# pylint: disable=g-bad-exception-name
class V4P1ManagerError(Exception):
  """Manager error class for v4p1."""


class V4P1Manager(manager.Manager):
  """Class to handle one manufacteuring round for one device type."""

  TITLE = 'v4p1'

  PARSER_DESC = 'Run manufacturing flow for servo v4p1'

  RE = (r'^(SERVOV4P1-)?'             # device type
        r'[CGS](-)?'                  # supplier
        r'[0-9]{2}'                   # YY
        r'(0[1-9]|1[0-2])'            # MM
        r'(0[1-9]|[12][0-9]|3[0-1])'  # DD
        r'[0-9]{4}$')                 # serialno suffix

  LEGACY_RES = [r'^N[PDQ][0-9]{5}$']

  # The serial number is either the standard RE or one of the legacy serial
  # numbers.
  SERIALNO_RE = re.compile('|'.join('(%s)' % e for e in LEGACY_RES + [RE]))

  def __init__(self, args, outdir):
    """Initialize the manufacturing."""
    self.board = 'v4p1'
    manager.Manager.__init__(self, outdir=outdir, validation=args.validation)
    self.manufacturer = V4P1Manufacturer(self.validation, args)
    self.tester_cls = V4P1Tester

  @staticmethod
  def add_manager_args(parser):
    """Helper to add the arguments that this type of manager requires."""
    parser.add_argument('-s', '--serialno', type=str,
                        help='serial number to program', default=None)
    parser.add_argument('-m', '--macaddr', type=str, help='macaddr to program',
                        default=None)
    devices = ['flash', 'usb_hub', 'serial', 'mac', 'kb_emulator']
    for dev in devices:
      g = parser.add_mutually_exclusive_group()
      g.add_argument('--no_%s' % dev, action='store_false', dest=dev,
                     default=True,
                     help='Skip any %s validation or writing. This '
                     'takes precedence over force_.' % dev)
      if dev == 'flash':
        # You cannot force the dfu mode through software, so either it's on
        # through a cable, or it's not. There is no point in having a
        # force flag here.
        continue
      g.add_argument('--force_%s' % dev, action='store_true', default=False,
                     help='Force %s writing. Even if the already has '
                     'the right firmware, write it again.' % dev)

  def check_args(self, args):
    """Check the parsed arguments, perform modifications, or raise error.

    Note: in single device mode, the required arguments are supplied through
    the command line. In continious mode, they are supplied through continious
    prompts to the user. This functions sets the required arguments (serialno,
    macaddr) to None if they are provided in continious mode to force a
    prompting.

    Args:
      args: argparse Namespace object for the programming

    Returns:
      True if the provided arguments match the expectation, False otherwise
    """
    if not args.single:
      if args.serialno or args.macaddr:
        self._logger.info('This is continious mode. Single device args are '
                          'requested one at a time. These will be ignored.')
      if args.serialno:
        self._logger.info('Provided serialno %r will be ignored.',
                          args.serialno)
        args.serialno = None
      if args.macaddr:
        self._logger.info('Provided macaddr %r will be ignored.',
                          args.macaddr)
        args.macaddr = None
      return True
    else:
      if args.serialno and not user_input.serial_is_valid(args.serialno,
                                                          self.SERIALNO_RE):
        self._logger.error('Provided serialno %r invalid.', args.serialno)
        return self.abort(1)
      if args.macaddr and not user_input.mac_is_valid(args.macaddr):
        self._logger.error('Provided macaddr %r invalid.', args.macaddr)
        return self.abort(1)
      return True

  def wait_for_disconnect(self):
    """Wait for the device to disconnect after manufacturing."""
    # Simply wait for both hubs to be disconnected.
    hh_vid, hh_pid = V4P1Manufacturer.HH_VID, V4P1Manufacturer.HH_PID
    dh_vid, dh_pid, dh3_pid = (V4P1Manufacturer.DH_VID,
                               V4P1Manufacturer.DH_PID,
                               V4P1Manufacturer.DH_PID3)
    device_util.wait_for_usb_disconnect(vid=hh_vid, pid=hh_pid)
    device_util.wait_for_usb_disconnect(vid=dh_vid, pid=dh_pid, pid3=dh3_pid)

  def extract_single_device_data(self, args):
    """Extract out of the command line args the single device args."""
    if (args.mac and not args.macaddr) or (args.serial and not args.serialno):
      self._logger.error('Required argument missing. Cannot continue')
      self._logger.debug('Args provided: %s', str(args))
      self.abort(1)
    return {'serial': args.serialno, 'macaddr': args.macaddr}

  def prompt_data(self, args):
    """Helper to request data in continous mode. Serial and mac address.

    Note: this method does not return anything but rather sets the
          - serialno
          - macaddr
          attributes on |args| after successful prompting.

    Args:
      args: argparse Namespace object for the programming
    """
    serial = mac = None
    if args.serial or args.testing:
      serial = user_input.prompt_for_serial(self.SERIALNO_RE)
      if serial is None:
        # This indicates the user ran out of tries to get this right. Abort
        # at this point.
        self._logger.error('Retrieving serialno from user failed. Quitting.')
        self.abort(1)
    else:
      self._logger.info('Serial programming not requested. Skipping '
                        'prompt for serialno.')
    if self._finished:
      # Check in whether we have been declared finished in the meantime.
      return
    if args.mac:
      mac = user_input.prompt_for_mac()
      if mac is None:
        # This indicates the user ran out of tries to get this right. Abort
        # at this point.
        self._logger.error('Retrieving macaddr from user failed. Quitting.')
        self.abort(1)
    else:
      self._logger.info('Mac programming not requested. Skipping '
                        'prompt for macaddr.')
    args.serialno = serial
    args.macaddr = mac
