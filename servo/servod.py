#!/usr/bin/env python3
# Copyright 2012 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Python version of Servo hardware debug & control board server."""

# pkg_resources is erroneously suggested to be in the 3rd party segment

import errno
import fcntl
import itertools
import json
import logging
import multiprocessing
import os
import signal
import socket
import sys
import threading
import time
import urllib.request
import weakref
from xmlrpc.server import SimpleXMLRPCServer

# pylint: disable=E0401
import grpc
import usb

from servo import recovery
from servo import servo_dev
from servo import servo_dev_finder
from servo import servo_logging
from servo import servo_parsing
from servo import servo_server
from servo import watchdog
from servo.common.config.system_config import SystemConfig
from servo.common.proto import system_config_grpc
from servo.grpc_server import grpc_server_setup
from servo.utils import scratch
from servo.utils import servo_dev_hierarchy
from servo.utils import servo_dev_prober


# If user does not specify a log directory, use this one.
DEFAULT_LOG_DIR = "/var/log"

# grpc server host
GRPC_SERVER = "localhost"

# grpc server running port
GRPC_PORT = 50051

# If user does not specify a port to use, try ports in this range. Traverse
# the range from high to low addresses to maintain backwards compatibility
# (the first checked default port is 9999, the range is such that all possible
# port numbers are 4 digits).
DEFAULT_PORT_RANGE = (9200, 9999)

_GENESYS_USB3_HUB_VID = 0x05E3
_GENESYS_USB3_HUB_PID = 0x0625

_BOOL_ENV_VAR_VALUES = {
    "0": False,
    "false": False,
    "1": True,
    "true": True,
}


class ServodError(Exception):
    """Exception class for servod server."""


def _GetBoolEnvVar(env_name, default_val):
    """Get the bool value of a boolean environment variable.

    Args:
      env_name: str - the environment variable name
      default_val: bool - the default value to use if the environment variable
          is not set or empty

    Returns:
      bool

    Raises:
      ServodError: the environment variable is set to an unrecognized value
    """
    env_val = os.environ.get(env_name)
    if not env_val:  # deliberately match None or ""
        return default_val
    bool_val = _BOOL_ENV_VAR_VALUES.get(env_val.lower())
    if bool_val is None:
        raise ServodError(
            "environment variable {!r} value {!r} is not supported, try these "
            "boolean values: {}".format(
                env_name,
                env_val,
                " ".join(repr(s) for s in sorted(_BOOL_ENV_VAR_VALUES)),
            ),
        )
    return bool_val


class ServodStarter:
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

        # Initialize logging up here first to ensure log messages from parsing
        # can go through.  servo_logging:setup() will change the root logger
        # level, so be sure to set the level in the StreamHandler.
        loglevel, fmt = servo_logging.LOGLEVEL_MAP[servo_logging.DEFAULT_LOGLEVEL]
        default_handler = logging.StreamHandler()
        default_handler.setLevel(loglevel)
        default_handler.formatter = servo_logging.UTCFormatter(fmt=fmt)
        logging.basicConfig(level=loglevel, handlers=[default_handler])
        self._logger = logging.getLogger(os.path.basename(sys.argv[0]))

        # Running servod in chroot is no longer supported.
        self.exit_if_in_chroot()

        env_vars = sorted(servo_parsing.GetServodEnvVars())
        self._logger.info(
            "Attempting to parse servod command line: %r\n"
            "With environment variables: %r",
            cmdline,
            env_vars,
        )

        # The scratch initialization here ensures that potentially stale entries
        # are removed from the scratch before attempting to create a new one.
        self._scratchutil = scratch.Scratch()
        self._init_parsers_and_option_helpers()
        sopts, devopts_list = self._parse_args(cmdline)
        self._host = sopts.host

        if sopts.disable_host_usb3:
            disable_unusable_usb3_hubs()

        # Turn on recovery mode if requested.
        if sopts.servo_recovery:
            recovery.set_recovery_active()

        servo_port = self._start_xml_server(sopts)

        servo_logging.setup(
            logdir=sopts.log_dir,
            port=servo_port,
            debug_stderr=sopts.debug,
            backup_count=sopts.log_dir_backup_count,
        )

        # Log the command line again now that we've configured logging based on
        # a successfully parsed command line.
        self._logger.info(
            "Successfully parsed servod command line: %r\n"
            "With environment variables: %r",
            cmdline,
            env_vars,
        )
        self._logger.info("Start")

        if not os.environ.get("CROS_WORKON_SRCROOT") and sopts.fetch_token_db:
            token_file = "/var/cache/cros_ec/tokens/historical.bin"
            token_lock_file = token_file + ".lock"
            os.makedirs(os.path.dirname(token_lock_file), exist_ok=True)
            with open(token_lock_file, "wb") as fd:
                fcntl.lockf(fd, fcntl.LOCK_EX)
                self._logger.info("Fetching latest EC token database")
                urllib.request.urlretrieve(
                    "https://storage.googleapis.com/chromeos-localmirror/distfiles/chromeos-ec-token-historical.bin",  # pylint: disable=line-too-long
                    token_file,
                )
                self._logger.info("Successfully fetched EC token database")
                fcntl.lockf(fd, fcntl.LOCK_UN)

        (dev_entries, main_dev_entry) = self._discover_servos(sopts, devopts_list)

        self._servod = servo_server.Servod(usbkm232=sopts.usbkm232)

        prober = servo_dev_prober.DeviceProber()
        self._setup_servos(dev_entries, main_dev_entry, prober)
        grpc_server_process = multiprocessing.Process(
            target=grpc_server_setup.run_grpc_server, args=(self._servod,)
        )
        # Start the process in the background
        grpc_server_process.start()
        # Small timeout to allow interface threads to initialize.
        time.sleep(0.5)

        self._servod.validate_dut_controller()
        self._servod.hwinit(verbose=True, step_init=sopts.step_init)
        self._setup_servod_server()
        self._server_thread = threading.Thread(target=self._serve)
        self._server_thread.daemon = True
        self._turndown_initiated = False
        # Needs access to the servod instance.
        self._watchdog_thread = watchdog.DeviceWatchdog(
            self._servod, reconnect_timeout=sopts.reconnect_timeout
        )
        self._exit_status = 0

    def handle_sig(self, signum):
        """Handle a signal by turning off the server & cleaning up servod."""
        if not self._turndown_initiated:
            self._turndown_initiated = True
            self._logger.info("Received signal: %d. Attempting to turn off", signum)
            self._server.shutdown()
            self._server.server_close()
            self._servod.close()
            self._logger.info("Successfully turned off")

    def _init_parsers_and_option_helpers(self):
        """Initialize parsers and namespace generation.

        Initialize server and servo device argument parsers as well as a unified
        help generator.

        Additionally, store a function to generate an empty servo device namespace.
        This is used to generate new device options for devices pull in through
        device auto-discovery.
        """
        description = (
            "%(prog)s is server to interact with servo debug & control board. "
            "This server communicates to the board via USB and the client via "
            "xmlrpc library."
        )
        examples = [
            (
                "-b brya -m vell",
                "Launch server on default listening port connected to Vell DUT. "
                "The servo device is not specified so any servo device on the system "
                "might get chosen, and it might be incorrect if there are "
                "multiple servo devices.",
            ),
            (
                "-s <serialnum> -b atlas -m atlas -p 8888",
                "Launch server listening on port 8888 using Servo device <serialnum> "
                "connected to Atlas DUT",
            ),
            (
                "-n <name> -b octopus -m ampton",
                "Launch server listening on default listening port using Servo device "
                "named <name> (configured in ~/.servodrc) connected to Ampton DUT",
            ),
        ]
        # BaseServodParser adds port, host, debug args.
        server_pars = servo_parsing.BaseServodParser(add_help=False)
        log_dir = server_pars.add_mutually_exclusive_group()
        log_dir.add_argument(
            "--no-log-dir",
            default=False,
            action="store_true",
            help="Turn off log dir functionality.",
        )
        log_dir.add_argument(
            "--log-dir",
            type=str,
            default=DEFAULT_LOG_DIR,
            help="path where to dump servod debug logs as a file. "
            "If flag omitted default path is used",
        )
        server_pars.add_argument(
            "--log-dir-backup-count",
            type=int,
            default=servo_logging.LOG_BACKUP_COUNT,
            help="Max number of backup logs that will be "
            "kept per loglevel for one servod port. Reminder: "
            "files get rotated on new instance, by user "
            "request or when they grow past %d bytes." % servo_logging.MAX_LOG_BYTES,
        )
        server_pars.add_argument(
            "--servo-recovery",
            default=False,
            action="store_true",
            help="Start servod through normally fatal issues, such as missing "
            "DUT controller servo, to allow for inspection and recovery of "
            "servo devices themselves. (This is not related to CrOS recovery "
            "features.)",
        )
        server_pars.add_argument(
            "--recovery_mode",
            action="store_true",
            dest="servo_recovery",
            help="DEPRECATED. Old name for --servo-recovery",
        )
        server_pars.add_argument(
            "--step-init",
            default=False,
            action="store_true",
            help="Interactively prompt y/n for each control initialization? "
            "This is for troubleshooting purposes only! Do NOT use or depend "
            "on this option for regular servo use. This feature may be changed "
            "or removed without warning.",
        )
        # In the long term we might want to enable pulling in all servo devices
        # including all DUT controllers by default. Currently we default to pull
        # the minimum to be backwards compatible.
        server_pars.add_argument(
            "-D",
            "--device-discovery",
            default="min",
            const="min",
            nargs="?",
            choices=("none", "min", "full"),
            help="Level of auto-discovering devices based "
            "on the deviced provided through command line and "
            "rc file. Default to minimum discovery.",
        )
        # This is included in server_pars because it is shared across all devices
        server_pars.add_argument(
            "-u",
            "--usbkm232",
            type=str,
            help="path to USB-KM232 device which allow for "
            "sending keyboard commands to DUTs that do not "
            "have built in keyboards. Used in FAFT tests. "
            "(Optional), e.g. /dev/ttyUSB0",
        )
        server_pars.add_argument(
            "--reconnect-timeout",
            type=float,
            default=0.0,
            help="number of seconds (approx.) to allow for device "
            "reconnect, default is unspecified but is ~20 "
            "seconds depending on internal polling rate.",
        )
        # TODO: With Python 3.9+ use argparse.BooleanOptionalAction and delete
        # "--no-disable-host-usb3" as a separate option.
        server_pars.add_argument(
            "--disable-host-usb3",
            action="store_true",
            default=_GetBoolEnvVar("SERVOD_DISABLE_HOST_USB3", True),
            help="Early in servod startup, before servo device discovery, "
            "disable USB3 on all Genesys USB3 hub controllers with VID:PID of "
            "%04x:%04x attached to this system. This is a workaround for "
            "https://issuetracker.google.com/233912806 servo_v4p1 bug."
            % (_GENESYS_USB3_HUB_VID, _GENESYS_USB3_HUB_PID),
        )
        server_pars.add_argument(
            "--no-disable-host-usb3",
            action="store_false",
            dest="disable_host_usb3",
            help="Turn off the --disable-host-usb3 option. See its help for details.",
        )
        if not os.environ.get("CROS_WORKON_SRCROOT"):
            server_pars.add_argument(
                "--fetch-token-db",
                action="store_true",
                help="Automatically fetch latest EC token database",
            )
        # ServodRCParser adds configs for -name/-rcfile & serialname & parses them.
        dev_pars = servo_parsing.ServodRCParser(add_help=False)
        dev_pars.add_argument(
            "--vendor",
            default=None,
            type=lambda x: int(x, 0),
            help="vendor id of device to interface to",
        )
        dev_pars.add_argument(
            "--product",
            default=None,
            type=lambda x: int(x, 0),
            help="USB product id of device to interface with",
        )
        dev_pars.add_argument(
            "-c",
            "--config",
            default=None,
            type=str,
            action="append",
            help="system config file (XML) to read",
        )
        dev_pars.add_argument(
            "-b",
            "--board",
            default="",
            type=str,
            action="store",
            help="include config file (XML) for given board",
        )
        dev_pars.add_argument(
            "-m",
            "--model",
            default="",
            type=str,
            action="store",
            help="optional config for a model of the given board, requires --board",
        )
        dev_pars.add_argument(
            "--noautoconfig",
            action="store_true",
            default=False,
            help="Disable automatic determination of config files",
        )
        dev_pars.add_argument(
            "-i",
            "--interfaces",
            type=str,
            nargs="+",
            default="",
            help="ordered space-delimited list of interfaces. "
            "Valid choices are gpio|i2c|uart|gpiouart|empty",
        )
        dev_pars.add_argument(
            "--prefix",
            type=str,
            nargs="+",
            default=[],
            help="prefix(s) used to route controls to this device",
        )
        dev_pars.add_argument(
            "--token-db",
            default="/usr/share/cros_ec/tokens/historical.bin",
            type=str,
            help="Path to CrOS EC token database",
        )
        # Create a unified parser with both server & device arguments to display
        # meaningful help messages to the user.
        # pylint: disable=protected-access
        # The parser here is used for its base ability to format examples.
        help_parser = servo_parsing._BaseServodParser(
            description=description, examples=examples, parents=[server_pars, dev_pars]
        )
        # Both parsers should display the same usage information when an
        # argument is not found. Fix it here by pointing both of their methods
        # to the help_parser.
        server_pars.format_usage = help_parser.format_usage
        dev_pars.format_usage = help_parser.format_usage
        self.help_parser = help_parser
        self.server_pars = server_pars
        self.dev_pars = dev_pars
        # Generator function for an empty namespace for a servo device.
        self.devopts_generator = lambda: self.dev_pars.parse_args([])

    def _parse_args(self, cmdline):
        """Parse commandline arguments.

        Args:
          cmdline: list of cmdline arguments

        Returns:
          tuple: (server, dev) args Namespaces after parsing & processing cmdline
            server: holds server scoped options, such as --port --host --log-dir
            dev: holds servo device scoped options, such as --serialname,
                 that apply to specific servo devices
        """
        if any(True for argstr in cmdline if argstr in ["-h", "--help"]):
            self.help_parser.print_help()
            self.help_parser.exit()
        server_args, dev_cmdline = self.server_pars.parse_known_args(cmdline)
        # Adjust log-dir to be None if no_log_dir is requested.
        if server_args.no_log_dir:
            server_args.log_dir = None
        # The dev cmdline uses ' --- ' to indicate that a new device is being
        # configured. Thus, parse each segment individually.
        dev_cmdline_chunks = [
            list(group)
            for is_delimiter, group in itertools.groupby(
                dev_cmdline, lambda delimiter: delimiter == "---"
            )
            if not is_delimiter
        ]
        # There will be no chunks if the user did not specify a single device
        # argument in the commandline. That's fine however, as servod can assume
        # they intended to invoke at least one device. This ensures that at least
        # one device will be initialized.
        dev_cmdline_chunks = dev_cmdline_chunks if dev_cmdline_chunks else [[]]
        dev_args_list = [
            self.dev_pars.parse_args(dev_cmdline) for dev_cmdline in dev_cmdline_chunks
        ]
        return (server_args, dev_args_list)

    def _start_xml_server(self, sopts):
        """Start the xml server.

        Args:
          sopts: server options parsed from cmdline.

        Returns:
          the port at which the xml server starts at
        """
        if servo_parsing.ArgMarkedAsUserSupplied(sopts, "port"):
            start_port = sopts.port
            end_port = sopts.port
        else:
            end_port, start_port = DEFAULT_PORT_RANGE
        for self._servo_port in range(start_port, end_port - 1, -1):
            try:
                self._server = SimpleXMLRPCServer(
                    (self._host, self._servo_port), logRequests=False
                )
                break
            except socket.error as error:
                if error.errno == errno.EADDRINUSE:
                    continue  # Port taken, see if there is another one next to it.
                self._logger.fatal("Problem opening Server's socket: %s", error)
                sys.exit(-1)
        else:
            if start_port == end_port:
                # This condition indicates that a specific port was being requested.
                # Report that the port itself is busy.
                err_msg = "Port %d is busy" % sopts.port
            else:
                err_msg = "Could not find a free port in %d..%d range" % (
                    end_port,
                    start_port,
                )

            self._logger.fatal(err_msg)
            sys.exit(-1)
        return self._servo_port

    def _setup_servod_server(self):
        """Set up the xml server so that servod is used as the backend."""
        self._server.register_introspection_functions()
        self._server.register_multicall_functions()
        self._server.register_instance(self._servod)

    def _discover_servos(self, sopts, devopts_list):
        """Discover and setup servos for this servod instance.

        Args:
          sopts: server options parsed from cmdline
          devopts_list: device options parsed from cmdline

        Returns:
          a tuple of all the ServoDeviceEntry's, the main device's ServoDeviceEntry
        """
        dev_hierarchy = servo_dev_hierarchy.ServoDeviceHierarchy()
        if sopts.device_discovery == "full":
            discover_mode = servo_dev_finder.ServoDeviceDiscoveryMode.FULL_AUTO
        elif sopts.device_discovery == "min":
            discover_mode = servo_dev_finder.ServoDeviceDiscoveryMode.MIN_AUTO
        else:
            discover_mode = servo_dev_finder.ServoDeviceDiscoveryMode.NO_AUTO
        finder = servo_dev_finder.ServoDeviceFinder(
            devopts=devopts_list,
            devopts_generator=self.devopts_generator,
            dev_hierarchy=dev_hierarchy,
            servo_scratch=self._scratchutil,
            discover_mode=discover_mode,
        )
        try:
            dev_entries = finder.discover_servos()
            main_dev_entry = finder.choose_main_device(dev_entries)
            finder.generate_prefixes(dev_entries, main_dev_entry)
            finder.validate_devopts(dev_entries)
        except servo_dev_finder.ServoDeviceFinderError as exception:
            self._logger.fatal(
                "Failure during discovering servo devices: %s", exception
            )
            sys.exit(-1)
        return (dev_entries, main_dev_entry)

    def _setup_servos(self, dev_entries, _main_dev_entry, prober):
        """Setup servo devices for this servod instance.

        Args:
          dev_entries: all the devices' ServoDeviceEntry
          main_dev_entry: the main device's ServoDeviceEntry
          prober: a ServoDeviceProber to probe the board and model information
        """

        # Create a gRPC channel to the specified host and port
        channel = grpc.insecure_channel(f"{GRPC_SERVER}:{GRPC_PORT}")

        # Create a SystemConfig client using the generated stub
        system_config_client = system_config_grpc.SystemConfig(channel)

        for dev_entry in dev_entries:
            self._logger.debug("Start initializing servo device %s", dev_entry)
            devopts, dev_tmpl = dev_entry.devopts, dev_entry.dev_template

            all_configs = []
            if not devopts.noautoconfig:
                all_configs.append(dev_tmpl.DEFAULT_CONFIG)
            if devopts.config:
                for config in devopts.config:
                    # quietly ignore duplicate configs for backwards compatibility
                    if config not in all_configs:
                        all_configs.append(config)
            if not all_configs:
                raise ServodError(
                    "No automatic config found,"
                    " and no config specified with -c <file>"
                )

            # Create an instance of the SystemConfig
            scfg = SystemConfig()
            try:
                # Load systemConfig using the gRPC server
                # using the 'GetFileContent' system_config_stub
                response = system_config_client.GetFileContent(
                    VID=dev_entry.vid, PID=dev_entry.pid
                )

                # Extract and process the received system configuration data(
                # SystemConfig ProtoMessage)
                for config_object in response.systemConfig:
                    # Deserialize JSON data from the gRPC response and assign it to
                    # 'scfg'
                    scfg.hwinit = json.loads(config_object.hwinit)
                    scfg.control_tags = json.loads(config_object.control_tags)
                    scfg.aliases = json.loads(config_object.aliases)
                    scfg.syscfg_dict = json.loads(config_object.syscfg_dict)

            except grpc.RpcError as e:
                # Handle gRPC errors, such as network issues and exit system
                print(f"Error: {e}")

            servo_device = servo_dev.ServoDevice(
                dev_entry=dev_entry,
                config=scfg,
                interfaces=devopts.interfaces,
                servod=weakref.proxy(self._servod),
            )

            if servo_device.template.DUT_CONTROLLER and not devopts.board:
                # Initialize all interfaces already possible to see if the board
                # can be probed
                servo_device.init_servo_interfaces(fault_tolerant=True)
                ec_board = prober.get_board_from_ec(servo_device)
                if not ec_board:
                    self._logger.warning(
                        "Cannot probe board for DUT controller %s."
                        "Start device without board specific config.",
                        servo_device,
                    )
                else:
                    devopts.board = ec_board
                devopts.model = prober.get_model_from_ec(servo_device)
                servo_device.set_base_board(devopts.board)
            # Set the board and the model for a DUT
            if devopts.board:
                if not servo_device.set_board_and_model(devopts.board, devopts.model):
                    self._logger.warning(
                        "Cannot set up board %s for device %s. "
                        "Start device without board specific config.",
                        devopts.board,
                        servo_device,
                    )

            servo_device.syscfg.finalize()
            self._logger.debug(
                "System configs for device %s\n%s",
                dev_entry,
                servo_device.syscfg.display_config(),
            )

            for prefix in dev_entry.devopts.prefix:
                self._servod.add_device(servo_device, prefix)

        self._servod.update_known_ctrls()
        for servo_device in self._servod.get_devices():
            # Real init this time i.e. initialization will fail if there are issues
            # with creating the servo interfaces
            servo_device.init_servo_interfaces()
        self._servod.update_known_ctrls()

    def cleanup(self):
        """Perform any cleanup related work after servod server shut down."""
        self._scratchutil.RemoveEntry(self._servo_port)
        self._logger.info(
            "Server on %s port %s turned down", self._host, self._servo_port
        )

    def _serve(self):
        """Wrapper around rpc server's serve_forever to catch server errors."""
        # pylint: disable=broad-except
        self._logger.info("Listening on %s port %s", self._host, self._servo_port)
        try:
            self._server.serve_forever()
        except Exception:
            self._exit_status = 1

    def serve(self):
        """Add signal handlers, start servod on its own thread & wait for signal.

        Intercepts and handles stop signals so shutdown is handled.
        """
        handler = lambda signal, unused, starter=self: starter.handle_sig(signal)
        stop_signals = [
            signal.SIGHUP,
            signal.SIGINT,
            signal.SIGQUIT,
            signal.SIGTERM,
            signal.SIGTSTP,
        ]
        for sig in stop_signals:
            signal.signal(sig, handler)
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
        if self._server_thread.is_alive():
            self._logger.error(
                "Server thread not turned down after %s s.", self.EXIT_TIMEOUT_S
            )
        self._watchdog_thread.join(self.EXIT_TIMEOUT_S)
        if self._watchdog_thread.is_alive():
            self._logger.error(
                "Watchdog thread not turned down after %s s.", self.EXIT_TIMEOUT_S
            )
        self.cleanup()
        sys.exit(self._exit_status)

    def exit_if_in_chroot(self):
        if os.environ.get("CROS_WORKON_SRCROOT"):
            self._logger.info(
                "\nRunning servod in the cros_sdk is no longer supported."
                "\nPlease refer to https://chromium.googlesource.com/"
                "chromiumos/third_party/hdctools/+/main/docs/"
                "servod_outside_chroot.md"
            )
            if os.environ.get("I_NEED_SERVOD"):
                self._logger.info(
                    "\n\n*********************************************************\n\n"
                    "You are running servod in an override mode. "
                    "\nProceed at your own risk with the understanding this may "
                    "stop working at any time without notice."
                    "\n\n*********************************************************\n\n"
                )
            else:
                sys.exit(2)


# Disable Genesys USB3 hubs that come without serial number: Genesys USB
# hubs are used on Servo v4.1. servod needs to be able to find USB devices
# attached to servo's ports and due to the way USB3 works, this needs a
# common identifier. USB has the Container ID property for that but despite
# the spec stating that it should be unique, we had hubs with identical IDs,
# and we had IDs changing on firmware updates.
# Since we know how to set the serial number, we set the hub's serial
# number to follow servo's (on the STM32) and work from that. Devices without
# a serial number are out of luck though and we're doing best by disabling
# USB3 there entirely.
# Note that the DUT can still access a USB3 device at USB3 speeds: This
# only affects the host-facing hub.
def disable_unusable_usb3_hubs():
    # The Product ID matches the USB3 side of the hub.
    hubs = list(
        usb.core.find(
            find_all=True,
            idVendor=_GENESYS_USB3_HUB_VID,
            idProduct=_GENESYS_USB3_HUB_PID,
            serial_number=None,
        )
    )
    for hub in hubs:
        hub.detach_kernel_driver(0)
        hub.set_configuration()
        # This request resets the hub, leading to new enumeration of the
        # servo. This won't have detrimental effects on other servod's
        # servos because they underwent this treatment already and have
        # no USB3 side that would respond to this.
        # The setting remains active until servo is powered off (including
        # the separate USB-C power supply).
        hub.ctrl_transfer(
            bmRequestType=usb.util.build_request_type(
                usb.util.CTRL_OUT,
                usb.util.CTRL_TYPE_VENDOR,
                usb.util.CTRL_RECIPIENT_DEVICE,
            ),
            bRequest=0x81,
            wValue=0x5,  # USB2-only. USB2/3 operation is 0x6
            wIndex=0,
            data_or_wLength=0,
        )

    if len(hubs) > 0:
        time.sleep(3)


# pylint: disable=dangerous-default-value
# Ability to pass an arbitrary or artificial cmdline for testing is desirable.
def main(cmdline=sys.argv[1:]):
    """Main function for servod."""
    try:
        starter = ServodStarter(cmdline)
    except ServodError as error:
        print("Error: %s" % error)
        sys.exit(1)
    starter.serve()


if __name__ == "__main__":
    main()
