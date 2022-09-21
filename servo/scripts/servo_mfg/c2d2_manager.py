# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Module to manage one manufacturing round for one c2d2 device."""

import re

from servo_mfg import device_util
from servo_mfg import manager
from servo_mfg import user_input
from servo_mfg.c2d2_manufacturer import C2D2Manufacturer
from servo_mfg.c2d2_tester import C2D2Tester


# pylint: disable=g-bad-exception-name
class C2D2ManagerError(Exception):
  """Manager error class for c2d2."""


class C2D2Manager(manager.Manager):
  """Class to handle one manufacteuring round for one device type."""

  TITLE = 'c2d2'

  PARSER_DESC = 'Run manufacturing flow for c2d2.'

  # Note that c2d2 does not have a legacy system for serialno as other
  # devices do. This is why this section is significantly shorter.
  SERIALNO_RE = re.compile(r'^(C2D2-)?'                  # device type
                           r'[CGS](-)?'                  # supplier
                           r'[0-9]{2}'                   # YY
                           r'(0[1-9]|1[0-2])'            # MM
                           r'(0[1-9]|[12][0-9]|3[0-1])'  # DD
                           r'[0-9]{4}$')                 # serialno suffix

  def __init__(self, args, outdir):
    """Initialize the manufacturing."""
    self.board = 'c2d2'
    manager.Manager.__init__(self, outdir=outdir, validation=args.validation)
    self.manufacturer = C2D2Manufacturer(self.validation, args)
    self.tester_cls = C2D2Tester

  @staticmethod
  def add_manager_args(parser):
    """Helper to add the arguments that this type of manager requires."""
    manager.Manager.add_manager_args(parser)
    parser.add_argument('-s', '--serialno', type=str,
                        help='serial number to program', default=None)
    devices = ['flash', 'serial']
    for dev in devices:
      g = parser.add_mutually_exclusive_group()
      g.add_argument('--no-%s' % dev, action='store_false', dest=dev,
                     default=True,
                     help='Skip any %s validation or writing. This '
                     'takes precedence over force-.' % dev)
      if dev == 'flash':
        # You cannot force the dfu mode through software, so either it's on
        # through a cable, or it's not. There is no point in having a
        # force flag here.
        continue
      g.add_argument('--force-%s' % dev, action='store_true', default=False,
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
      if args.serialno:
        self._logger.info('This is continious mode. Single device args are '
                          'requested one at a time. These will be ignored.')
        self._logger.info('Provided serialno %r will be ignored.',
                          args.serialno)
        args.serialno = None
      return True
    else:
      if args.serialno and not user_input.serial_is_valid(args.serialno,
                                                          self.SERIALNO_RE):
        self._logger.error('Provided serialno %r invalid.', args.serialno)
        return self.abort(1)
      return True

  def wait_for_disconnect(self):
    """Wait for the user to remove the c2d2."""
    servo_vid = C2D2Manufacturer.SERVO_VID
    servo_pid = C2D2Manufacturer.SERVO_PID
    device_util.wait_for_usb_disconnect(vid=servo_vid, pid=servo_pid)

  def extract_single_device_data(self, args):
    """Extract out of the command line args the single device args."""
    if args.serial and not args.serialno:
      return self._req_arg_missing(args)
    return {'serial': args.serialno}

  def prompt_data(self, args):
    """Helper to request data in continous mode. Serial and mac address.

    Note: this method does not return anything but rather sets the serialno
          attribute on |args| after successful prompting.

    Args:
      args: argparse Namespace object for the programming
    """
    serial = None
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
    args.serialno = serial
