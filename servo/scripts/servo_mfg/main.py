#!/usr/bin/python2
# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Main module to coordinate servo mfg."""

from __future__ import print_function

import argparse
import collections
import logging
import os
import signal
import sys

from servo_mfg import color_mode as cm
from servo_mfg import reporter
from servo_mfg import user_input
from servo_mfg.c2d2_manager import C2D2Manager
from servo_mfg.micro_manager import MicroManager
from servo_mfg.v4_manager import V4Manager
from servo_mfg.v4p1_manager import V4P1Manager


DESC = 'Flashing and programming tool for cros servo devices.'

# Number of times to need to receive ctrl-c to exit without letting current
# task finish
# TODO(coconutruben): implement this properly, then increment this to |3|
SIGNAL_COUNT_TO_QUIT = 1


class Coordinator(object):
  """Helper class to manage parsing and handing off to right manager."""

  def __init__(self, cmdline):
    """Setup the manager and, output directories, and logging logic.

    Args:
      cmdline: command line arguments to parse
    """
    self._logger = logging.getLogger(type(self).__name__)
    self.signal_map = collections.defaultdict(lambda: SIGNAL_COUNT_TO_QUIT)
    self.args = self.parse(cmdline)
    if self.args.color_mode:
      cm.activate()
    self.outdir = reporter.setup_logging_and_reporting(self.args.debug)
    # If log management is the only job to do here, then do that, before
    # exiting.
    if self.args.collect_logs:
      o = reporter.bundle_all()
      logging.info('All logs compressed at %r', o)
    if self.args.remove_logs:
      reporter.clear_all()
    if self.args.remove_logs or self.args.collect_logs:
      # These are single action items. exit now.
      sys.exit(0)
    # Perform this after setting up logging to avoid generating an extra
    # log handler, and to avoid false information if we only had log management
    # activities going on.
    # inform the user that that's where they can find all the files
    logging.getLogger().info('Logs and output files will be available at: %r',
                             self.outdir)
    if self.args.yes:
      # Set the right switch to ensure users do not get used for confirmation.
      user_input.turn_off_user_confirmation()
    self.manager = None

    # Note: add new device managers here
    if self.args.device == V4P1Manager.TITLE:
      self.manager = V4P1Manager(args=self.args, outdir=self.outdir)

    elif self.args.device == V4Manager.TITLE:
      self.manager = V4Manager(args=self.args, outdir=self.outdir)

    elif self.args.device == MicroManager.TITLE:
      self.manager = MicroManager(args=self.args, outdir=self.outdir)

    elif self.args.device == C2D2Manager.TITLE:
      self.manager = C2D2Manager(args=self.args, outdir=self.outdir)

    if self.manager is None:
      self._logger.error('No manager found for the task. This is a coding '
                         'issue, as there should be one manager per '
                         'subparser. Please file a bug.')
      self.exit(1)

    # This gives the manager an opportunity to validate whether the
    # arguments passed in make sense, or whether there are issues.
    if not self.manager.check_args(self.args):
      # The manager here calls abort() internally. We only need to exit.
      self.exit(self.manager.exit_code)

  def exit(self, code=0):
    """Exit by tarring up the output directory before exiting.

    Args:
      code: exit code to use
    """
    if self.outdir is not None and os.path.exists(self.outdir):
      # Make the outdir read/write for everyone.
      os.chmod(self.outdir, 0o777)
      for f in os.listdir(self.outdir):
        os.chmod(os.path.join(self.outdir, f), 0o666)
      # Bundle outdir into a tarball, and report where that's going.
      self._logger.info('Data for this run can be found at %r', self.outdir)
      outdir_tar = reporter.bundle([self.outdir])
      os.chmod(outdir_tar, 0o666)
      self._logger.info('The data is also compressed at %r', outdir_tar)
    sys.exit(code)

  def handle_sig(self, sig, _):
    """Helper to handle ctrl-c logic.

    This function allow the code to have a two step system where the user can
    request indicate an 'orderly' shutdown by issuing a signal less than
    |SIGNAL_COUNT_TO_QUIT| times. This will just mark the process to be finished
    but will let the code finish what it's currently doing before wrapping up.
    Should the user need to exit right away, issuing the signal
    SIGNAL_COUNT_TO_QUIT or more times, it they can exit right away.

    Args:
      sig: signal received
    """
    # Only process a signal once.
    if self.signal_map[sig] == SIGNAL_COUNT_TO_QUIT:
      if self.manager is not None:
        self.manager.finish()
    self.signal_map[sig] -= 1
    self._logger.info('Reiceived signal %d. Trying to turn down gracefully.',
                      sig)
    if self.signal_map[sig]:
      self._logger.info('Issue %d more times to exit right away.',
                        self.signal_map[sig])
    else:
      self._logger.info('Turning down right away as requested.')
      self.exit(1)

  def parse(self, cmdline):
    """Helper to handle parsing.

    Parse common arguments, and attach all device sub-parsers.

    Args:
      cmdline: command line arguments to parse

    Returns:
      parsed result (Namespace) from common args + chosen device args
    """
    parser = argparse.ArgumentParser(description=DESC)
    parser.add_argument('-d', '--debug', action='store_true', default=False,
                        help='Whether to print debug level output to console.')
    parser.add_argument('--single', action='store_true', default=False,
                        help='Whether to program a single device rather than '
                        'a continous loop')
    parser.add_argument('--developer', action='store_true', default=False,
                        help='Whether to run into developer mode. By default '
                        'the script runs in factory mode. Factory mode means '
                        '--yes, --color-mode, and testing. Use developer mode '
                        'to overwrite those if desired.')
    parser.add_argument('--yes', action='store_true', default=False,
                        help='Never wait for user confirmation, always assume '
                        'it is given. Use this if the user has prepared the '
                        'devices beforehand and will not require time to setup '
                        'testing explicitly.')
    parser.add_argument('--color-mode', action='store_true', default=False,
                        help='Color mode prints color prompts when the user '
                        'needs to take action, and tries to match up the '
                        'text color to the cable coloring (if color was '
                        'prepared). Use this in factory for clearer flow.')
    t = parser.add_mutually_exclusive_group()
    t.add_argument('--no-testing', action='store_false', default=True,
                   dest='testing',
                   help='Whether to run the test loop after programming.')
    # By default, |programming| is done. The overall programming that is.
    # If the user specifies '--only-testing' then no programming is done
    # and only testing is done.
    t.add_argument('--only-testing', action='store_false', default=True,
                   dest='programming',
                   help='only run testing and skip all programming. This makes'
                   'all no_* flags unnecessary.')
    parser.add_argument('-v', '--validation', action='store_true',
                        default=False,
                        help='This indicates that no flashing should take '
                        'place but rather only validation against the '
                        'desired versions should be checked. This overwrites '
                        'any force_ args.')
    # Log management helpers.
    parser.add_argument('--collect-logs', action='store_true', default=False,
                        help='Collect all logs from all runs, and exit.')
    parser.add_argument('--remove-logs', action='store_true', default=False,
                        help='Remove all logs from all runs, and exit.')
    device_parsers = parser.add_subparsers(title='device specific mfg commands',
                                           description=V4P1Manager.PARSER_DESC,
                                           dest='device')
    # Note: add new devices parsers here.
    # servo v4p1 done here.
    v4p1_parser = device_parsers.add_parser(V4P1Manager.TITLE,
                                            help='servo_v4p1 mfg')
    V4P1Manager.add_manager_args(v4p1_parser)

    # servo v4 done here.
    v4_parser = device_parsers.add_parser(V4Manager.TITLE,
                                          help='servo_v4 mfg')
    V4Manager.add_manager_args(v4_parser)

    # servo micro done here.
    micro_parser = device_parsers.add_parser(MicroManager.TITLE,
                                             help='servo micro mfg')
    MicroManager.add_manager_args(micro_parser)

    # c2d2 done here.
    c2d2_parser = device_parsers.add_parser(C2D2Manager.TITLE,
                                            help='c2d2 mfg')
    C2D2Manager.add_manager_args(c2d2_parser)

    args = parser.parse_args(cmdline)
    # If factory mode i.e. not developer mode, overwrite any wrong flags.
    if not args.developer:
      # Write the default factory configuration.
      args.programming = True
      args.testing = True
      args.color_mode = True
      args.yes = True
    return args

  def run(self):
    """Run the manufacturing logic."""
    if self.args.single:
      ret = self.manager.single_device(self.args)
      # On single device mode, we need to call abort from
      # the outside. |ret| is True on success, and False on failure.
      # This is the inverse of the usual exit codes. Need to invert
      # it here.
      self.manager.abort(int(not ret))
    else:
      self.manager.continious_mode(self.args)
    self.exit(self.manager.exit_code)


# pylint: disable=dangerous-default-value
def main(cmdline=sys.argv[1:]):
  """Setup coordinator and signal handlers, before running mfg logic.

  Args:
    cmdline: command line arguments to parse
  """
  coordinator = Coordinator(cmdline)
  stop_signals = [signal.SIGINT, signal.SIGQUIT, signal.SIGTERM]
  for ss in stop_signals:
    signal.signal(ss, lambda s, f, c=coordinator: c.handle_sig(s, f))

  coordinator.run()


if __name__ == '__main__':
  main()
