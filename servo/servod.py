#!/usr/bin/env python2
# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Python version of Servo hardware debug & control board server."""

# pylint: disable=g-bad-import-order
# pkg_resources is erroneously suggested to be in the 3rd party segment
from __future__ import print_function
import collections
import errno
import itertools
import logging
import os
import pkg_resources
import signal
try:
  from SimpleXMLRPCServer import SimpleXMLRPCServer
except ImportError:
  from xmlrpc.server import SimpleXMLRPCServer
  # TODO(crbug.com/999878): This is for python3 compatibility.
  # Remove once fully moved to python3.
import socket
import sys
import threading
import time
import weakref

from servo import interface
from servo import recovery
from servo import servo_dev
from servo import servo_dev_finder
from servo import servo_dev_templates
from servo import servo_logging
from servo import servo_parsing
from servo import servo_postinit
from servo import servo_server
from servo import system_config
from servo import terminal_freezer
from servo import watchdog
from servo.utils import scratch
from servo.utils import servo_dev_hierarchy
from servo.utils import usb_hierarchy


# If user does not specify a log directory, use this one.
DEFAULT_LOG_DIR = '/var/log'

# If user does not specify a port to use, try ports in this range. Traverse
# the range from high to low addresses to maintain backwards compatibility
# (the first checked default port is 9999, the range is such that all possible
# port numbers are 4 digits).
DEFAULT_PORT_RANGE = (9200, 9999)

# pylint: disable=g-bad-exception-name
class ServodError(Exception):
  """Exception class for servod server."""
  pass


class ServodStarter(object):
  """Class to manage servod instance and rpc server its being served on."""

  # Timeout period after which to just turn down, regardless of threads
  # needing to clean up.
  EXIT_TIMEOUT_S = 20

  def __init__(self, cmdline):
    """Prepare servod invocation.

    Parse cmdline and prompt user for missing information if necessary to start
    servod. Prepare servod instance & thread for it to be served from.

    Args:
      cmdline: list, cmdline components to parse

    Raises:
      ServodError: if automatic config cannot be found
    """
    # The scratch initialization here ensures that potentially stale entries
    # are removed from the scratch before attempting to create a new one.
    self._scratchutil = scratch.Scratch()
    # Initialize logging up here first to ensure log messages from parsing
    # can go through.
    loglevel, fmt = servo_logging.LOGLEVEL_MAP[servo_logging.DEFAULT_LOGLEVEL]
    logging.basicConfig(level=loglevel, format=fmt)
    self._logger = logging.getLogger(os.path.basename(sys.argv[0]))
    sopts, devopts_list = self._parse_args(cmdline)
    self._host = sopts.host

    # Turn on recovery mode if requested.
    if sopts.recovery_mode:
      recovery.set_recovery_active()

    if servo_parsing.ArgMarkedAsUserSupplied(sopts, 'port'):
      start_port = sopts.port
      end_port = sopts.port
    else:
      end_port, start_port = DEFAULT_PORT_RANGE
    for self._servo_port in range(start_port, end_port - 1, -1):
      try:
        self._server = SimpleXMLRPCServer((self._host, self._servo_port),
                                          logRequests=False)
        break
      except socket.error as e:
        if e.errno == errno.EADDRINUSE:
          continue  # Port taken, see if there is another one next to it.
        self._logger.fatal("Problem opening Server's socket: %s", e)
        sys.exit(-1)
    else:
      if start_port == end_port:
        # This condition indicates that a specific port was being requested.
        # Report that the port itself is busy.
        err_msg = ('Port %d is busy' % sopts.port)
      else:
        err_msg = ('Could not find a free port in %d..%d range' % (end_port,
                                                                   start_port))

      self._logger.fatal(err_msg)
      sys.exit(-1)
    servo_logging.setup(logdir=sopts.log_dir, port=self._servo_port,
                        debug_stdout=sopts.debug,
                        backup_count=sopts.log_dir_backup_count)

    if sopts.dual_v4:
      # Leave the right breadcrumbs for servo_postinit to know whether to setup
      # a dual instance or not.
      os.environ[servo_postinit.DUAL_V4_VAR] = servo_postinit.DUAL_V4_VAR_EMPTY

    self._logger.info('Start')

    dev_hierarchy = servo_dev_hierarchy.ServoDeviceHierarchy()
    finder = servo_dev_finder.ServoDeviceFinder(devopts=devopts_list,
                                                dev_hierarchy=dev_hierarchy,
                                                scratch=self._scratchutil)
    try:
      servo_devs = finder.discover_servos()
      main_dev = finder.choose_main_device(servo_devs)
      finder.generate_prefixes(servo_devs, main_dev)
      finder.validate_devopts(servo_devs)
    except servo_dev_finder.ServoDeviceFinderError as e:
      self._logger.fatal("Failure during discovering servo devices: %s", e)
      sys.exit(-1)

    # TODO(konmari): refactor the below section to support multi devices
    #                below is a temporary hack that works for current servo_postinit
    if main_dev.cluster_root and main_dev.dev_template.DUT_CONTROLLER:
      servo_device = main_dev.cluster_root
      servo_device.devopts.prefix = servo_dev_templates.MAIN_DEV_PREFIX
    else:
      servo_device = main_dev
    devopts = devopts_list[0]
    if not servo_device:
      sys.exit(-1)

    vid, pid, serial = servo_device.vid, servo_device.pid, servo_device.serial
    dev_tmpl = servo_dev_templates.GetTemplateClass(vid=vid, pid=pid,
                                                    serial=serial)
    board_version = dev_tmpl.TYPE
    self._logger.debug('board_version = %s', board_version)
    all_configs = []
    if not devopts.noautoconfig:
      all_configs.append(dev_tmpl.DEFAULT_CONFIG)

    if devopts.config:
      for config in devopts.config:
        # quietly ignore duplicate configs for backwards compatibility
        if config not in all_configs:
          all_configs.append(config)

    if not all_configs:
      raise ServodError('No automatic config found,'
                        ' and no config specified with -c <file>')

    scfg = system_config.SystemConfig()

    if devopts.board:
      # Handle differentiated model case.
      board_config = None
      if devopts.model:
        board_config = 'servo_%s_%s_overlay.xml' % (
            devopts.board, devopts.model)

        if not scfg.find_cfg_file(board_config):
          self._logger.info('No XML overlay for model '
                            '%s, falling back to board %s default',
                            devopts.model, devopts.board)
          board_config = None
        else:
          self._logger.info('Found XML overlay for model %s:%s',
                            devopts.board, devopts.model)

      # Handle generic board config.
      if not board_config:
        board_config = 'servo_' + devopts.board + '_overlay.xml'
        if not scfg.find_cfg_file(board_config):
          self._logger.error('No XML overlay for board %s', devopts.board)
          sys.exit(-1)

        self._logger.info('Found XML overlay for board %s', devopts.board)

      all_configs.append(board_config)
      scfg.set_board_cfg(board_config)

    for cfg_file in all_configs:
      scfg.add_cfg_file(cfg_file)

    self._logger.debug('\n%s', scfg.display_config())

    self._logger.debug('Servo is vid:0x%04x pid:0x%04x sid:%s', vid, pid, serial)

    self._servod = servo_server.Servod(usbkm232=devopts.usbkm232)
    template = servo_dev_templates.GetTemplateClass(vid=vid, pid=pid, serial=serial)
    main_servo_dev = servo_dev.ServoDevice(template=template, config=scfg,
      name=servo_device.devopts.prefix, serialname=serial,
      interfaces=devopts.interfaces.split(), board=devopts.board, model=devopts.model,
      version=board_version, servod=weakref.proxy(self._servod))

    # Small timeout to allow interface threads to initialize.
    time.sleep(0.5)

    self._servod.hwinit(verbose=True)
    self._server.register_introspection_functions()
    self._server.register_multicall_functions()
    self._server.register_instance(self._servod)
    self._server_thread = threading.Thread(target=self._serve)
    self._server_thread.daemon = True
    self._turndown_initiated = False
    # pylint: disable=protected-access
    # Needs access to the servod instance.
    self._watchdog_thread = watchdog.DeviceWatchdog(self._servod)
    self._exit_status = 0

  def handle_sig(self, signum):
    """Handle a signal by turning off the server & cleaning up servod."""
    if not self._turndown_initiated:
      self._turndown_initiated = True
      self._logger.info('Received signal: %d. Attempting to turn off', signum)
      self._server.shutdown()
      self._server.server_close()
      self._servod.close()
      self._logger.info('Successfully turned off')

  def _parse_args(self, cmdline):
    """Parse commandline arguments.

    Args:
      cmdline: list of cmdline arguments

    Returns:
      tuple: (server, dev) args Namespaces after parsing & processing cmdline
        server: holds --port, --host, --log-dir, --allow-dual-v4, --debug flags
        dev: holds all the device flags (serialname, interfaces, configs etc -
             see below) necessary to configure a servo device.
    """
    description = (
        '%(prog)s is server to interact with servo debug & control board. '
        'This server communicates to the board via USB and the client via '
        'xmlrpc library. Launcher most specify at least one --config <file> '
        'in order for the server to provide any functionality. In most cases, '
        'multiple configs will be needed to expose complete functionality '
        'between debug & DUT board.')
    examples = [('-c <path>/data/servo.xml',
                 'Launch server on default host:port with native servo config'),
                ('-c <file> -p 8888', 'Launch server listening on port 8888'),
                ('-c <file> --vendor 0x18d1 --product 0x5001',
                 'Launch targetting usb device with vid:pid == 0x18d1:0x5001 '
                 '(Google/Servo)')]
    # BaseServodParser adds port, host, debug args.
    server_pars = servo_parsing.BaseServodParser(add_help=False)
    log_dir = server_pars.add_mutually_exclusive_group()
    log_dir.add_argument('--no-log-dir', default=False, action='store_true',
                         help='Turn off log dir functionality.')
    log_dir.add_argument('--log-dir', type=str, default=DEFAULT_LOG_DIR,
                         help='path where to dump servod debug logs as a file. '
                         'If flag omitted default path is used')
    server_pars.add_argument('--log-dir-backup-count', type=int,
                             default=servo_logging.LOG_BACKUP_COUNT,
                             help='Max number of backup logs that will be '
                             'kept per loglevel for one servod port. Reminder: '
                             'files get rotated on new instance, by user '
                             'request or when they grow past %d bytes.' %
                             servo_logging.MAX_LOG_BYTES)
    server_pars.add_argument('--allow-dual-v4', dest='dual_v4', default=False,
                             action='store_true',
                             help='Allow dual micro and ccd on servo v4.')
    server_pars.add_argument('--recovery_mode', default=False,
                             action='store_true',
                             help='Start servod through issues to allow for '
                             'inspection and recovery mechanisms.')
    # ServodRCParser adds configs for -name/-rcfile & serialname & parses them.
    dev_pars = servo_parsing.ServodRCParser(add_help=False)
    dev_pars.add_argument('--vendor', default=None, type=lambda x: int(x, 0),
                          help='vendor id of device to interface to')
    dev_pars.add_argument('--product', default=None, type=lambda x: int(x, 0),
                          help='USB product id of device to interface with')
    dev_pars.add_argument('-c', '--config', default=None, type=str,
                          action='append', help='system config file (XML) to '
                                                'read')
    dev_pars.add_argument('-b', '--board', default='', type=str,
                          action='store', help='include config file (XML) for '
                                               'given board')
    dev_pars.add_argument('-m', '--model', default='', type=str, action='store',
                          help='optional config for a model of the given board,'
                          ' requires --board')
    dev_pars.add_argument('--noautoconfig', action='store_true', default=False,
                          help='Disable automatic determination of config '
                               'files')
    dev_pars.add_argument('-i', '--interfaces', type=str, default='',
                          help='ordered space-delimited list of interfaces. '
                               'Valid choices are gpio|i2c|uart|gpiouart|empty')
    dev_pars.add_argument('-u', '--usbkm232', type=str,
                          help='path to USB-KM232 device which allow for '
                               'sending keyboard commands to DUTs that do not '
                               'have built in keyboards. Used in FAFT tests. '
                               '(Optional), e.g. /dev/ttyUSB0')
    # TODO(konmari): finish the doc of prefix
    dev_pars.add_argument('--prefix', type=str, default='', action='store')
    # Create a unified parser with both server & device arguments to display
    # meaningful help messages to the user.
    # pylint: disable=protected-access
    # The parser here is used for its base ability to format examples.
    help_displayer = servo_parsing._BaseServodParser(description=description,
                                                     examples=examples,
                                                     parents=[server_pars,
                                                              dev_pars])
    if any([True for argstr in cmdline if argstr in ['-h', '--help']]):
      help_displayer.print_help()
      help_displayer.exit()
    # Both parsers should display the same usage information when an
    # argument is not found. Fix it here by pointing both of their methods
    # to the help_displayer.
    server_pars.format_usage = help_displayer.format_usage
    dev_pars.format_usage = help_displayer.format_usage
    server_args, dev_cmdline = server_pars.parse_known_args(cmdline)
    # Adjust log-dir to be None if no_log_dir is requested.
    if server_args.no_log_dir:
      server_args.log_dir = None

    # The dev cmdline uses ' --- ' to indicate that a new device is being
    # configured. Thus, parse each segment individually.
    dev_cmdline_chunks = [list(group) for is_delimiter, group in
                          itertools.groupby(dev_cmdline,
                          lambda delimiter: delimiter == '---')
                          if not is_delimiter]
    # There will be no chunks if the user did not specify a single device
    # argument in the commandline. That's fine however, as servod can assume
    # they intended to invoke at least one device. This ensures that at least
    # one device will be initialized.
    dev_cmdline_chunks = dev_cmdline_chunks if dev_cmdline_chunks else [[]]
    dev_args_list = [dev_pars.parse_args(dev_cmdline) for dev_cmdline in
                     dev_cmdline_chunks]
    return (server_args, dev_args_list)

  def cleanup(self):
    """Perform any cleanup related work after servod server shut down."""
    self._scratchutil.RemoveEntry(self._servo_port)
    self._logger.info('Server on %s port %s turned down', self._host,
                      self._servo_port)

  def _serve(self):
    """Wrapper around rpc server's serve_forever to catch server errors."""
    # pylint: disable=broad-except
    self._logger.info('Listening on %s port %s', self._host, self._servo_port)
    try:
      self._server.serve_forever()
    except Exception:
      self._exit_status = 1

  def serve(self):
    """Add signal handlers, start servod on its own thread & wait for signal.

    Intercepts and handles stop signals so shutdown is handled.
    """
    handler = lambda signal, unused, starter=self: starter.handle_sig(signal)
    stop_signals = [signal.SIGHUP, signal.SIGINT, signal.SIGQUIT,
                    signal.SIGTERM, signal.SIGTSTP]
    for ss in stop_signals:
      signal.signal(ss, handler)
    serials = set(self._servod.get_servo_serials().values())
    try:
      self._scratchutil.AddEntry(self._servo_port, serials, os.getpid())
    except scratch.ScratchError:
      self._servod.close()
      sys.exit(1)
    self._watchdog_thread.start()
    self._server_thread.start()
    # Indicate that servod is running for any process waiting to know.
    self._scratchutil.MarkActive(self._servo_port)
    signal.pause()
    # Set watchdog thread to end
    self._watchdog_thread.deactivate()
    # Collect servo and watchdog threads
    self._server_thread.join(self.EXIT_TIMEOUT_S)
    if self._server_thread.isAlive():
      self._logger.error('Server thread not turned down after %s s.',
                         self.EXIT_TIMEOUT_S)
    self._watchdog_thread.join(self.EXIT_TIMEOUT_S)
    if self._watchdog_thread.isAlive():
      self._logger.error('Watchdog thread not turned down after %s s.',
                         self.EXIT_TIMEOUT_S)
    self.cleanup()
    sys.exit(self._exit_status)


# pylint: disable=dangerous-default-value
# Ability to pass an arbitrary or artifical cmdline for testing is desirable.
def main(cmdline=sys.argv[1:]):
  try:
    starter = ServodStarter(cmdline)
  except ServodError as e:
    print('Error: ', e.message)
    sys.exit(1)
  starter.serve()

if __name__ == '__main__':
  main()
