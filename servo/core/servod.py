#!/usr/bin/env python3
# pylint: disable=logging-fstring-interpolation
# Copyright 2012 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Python version of Servo hardware debug & control board server."""

# pkg_resources is erroneously suggested to be in the 3rd party segment

from concurrent import futures
import errno
import fcntl
import itertools
import logging
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from typing import Any, List, Optional, Tuple
import urllib.request
import weakref
from xmlrpc.server import SimpleXMLRPCServer

# pylint: disable=E0401
import grpc
import usb

from servo.common import grpc_server_interceptor
from servo.common import servo_parsing
from servo.common.proto import servo_dev_grpc  # type: ignore
from servo.common.proto import system_config_grpc  # type: ignore
from servo.common.utils import servo_logging
from servo.core import recovery
from servo.core import servo_dev
from servo.core import servo_dev_finder
from servo.core import servo_server
from servo.core import watchdog
from servo.core.grpc_server.impl import servo_impl
from servo.utils import scratch
from servo.utils import servo_dev_hierarchy


# If user does not specify a log directory, use this one.
DEFAULT_LOG_DIR = "/var/log"

# If user does not specify a port to use, try ports in this range. Traverse
# the range from high to low addresses to maintain backwards compatibility
# (the first checked default port is 9999, the range is such that all possible
# port numbers are 4 digits).
DEFAULT_PORT_RANGE = (9200, 9999)

# Kernel modules that are known to cause issues with servod.
# If these are detected at startup, servod will exit.
EXCLUDED_KERNEL_MODULES = frozenset(["GobiNet", "qtiDevInf"])

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


def _get_bool_env_var(env_name, default_val):
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

    def __init__(self, cmdline: List[str]) -> None:
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
        loglevel, fmt = servo_logging.SHORT_LOGLEVEL_MAP[servo_logging.DEFAULT_LOGLEVEL]
        default_handler = logging.StreamHandler()
        default_handler.setLevel(loglevel)
        default_handler.formatter = servo_logging.ShortUTCFormatter(fmt=fmt)
        logging.basicConfig(level=loglevel, handlers=[default_handler])
        self._logger = logging.getLogger(os.path.basename(sys.argv[0]))

        # Check for excluded kernel modules.
        self._check_for_excluded_modules()

        env_vars = sorted(servo_parsing.get_servod_env_vars())
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
        self.opts = sopts
        self._host = sopts.host

        if sopts.disable_host_usb3:
            disable_unusable_usb3_hubs()

        # Turn on recovery mode if requested.
        if sopts.servo_recovery:
            recovery.set_recovery_active()

        servo_port = self._start_xml_server(sopts)

        self._data_service_proc: Optional[subprocess.Popen[bytes]] = None
        self._resolve_fission_ports(sopts)

        servo_logging.setup(
            logdir=sopts.log_dir,
            module="servod",
            port=servo_port,
            debug_stderr=sopts.debug,
            backup_count=sopts.log_dir_backup_count,
        )

        if self.exit_if_in_chroot():
            self._spawn_data_service(sopts)

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

        try:
            with scratch.ConcurrencyGuard(max_concurrency=3, name="startup"):
                (dev_entries, main_dev_entry) = self._discover_servos(
                    sopts, devopts_list
                )

                self._servod = servo_server.Servod(usbkm232=sopts.usbkm232)

                self._logger.info("Connecting to gRPC")
                while True:
                    try:
                        self._servod.clear()
                        self._setup_servos(
                            dev_entries,
                            main_dev_entry,
                            (sopts.grpc_data_host, sopts.grpc_data_port),
                        )
                        break
                    except grpc.RpcError as e:
                        if e.code() != grpc.StatusCode.UNAVAILABLE:
                            raise
                        time.sleep(1)

                options = [
                    ("grpc.keepalive_permit_without_calls", True),
                    ("grpc.http2.min_recv_ping_interval_without_data_ms", 5000),
                    ("grpc.http2.max_ping_strikes", 0),
                    ("grpc.max_metadata_size", 64 * 1024),
                ]

                self._grpc_server = grpc.server(
                    futures.ThreadPoolExecutor(max_workers=10),
                    options=options,
                    interceptors=(
                        grpc_server_interceptor.ExceptionTruncatingInterceptor(),
                    ),
                )
                servo = servo_impl.ServoImpl(
                    ("localhost", sopts.grpc_core_port), self._servod
                )
                servo_dev_grpc.add_ServoServiceServicer_to_server(
                    servo, self._grpc_server
                )
                self._grpc_server.add_insecure_port(
                    "0.0.0.0:{}".format(sopts.grpc_core_port)
                )
                self._grpc_server.start()
                self._logger.info("Core Server started....")

                # Small timeout to allow interface threads to initialize.
                time.sleep(0.5)

                self._servod.validate_dut_controller()
                if sopts.no_hwinit:
                    self._logger.info("Skipping hwinit as requested by --no-hwinit")
                else:
                    self._servod.hwinit(verbose=True, step_init=sopts.step_init)
        except servo_dev_finder.ServoDeviceFinderError as e:
            self._logger.fatal("-" * 60)
            self._logger.fatal("FATAL: %s", e)
            self._logger.fatal("-" * 60)
            sys.exit(-1)

        if sopts.dump_xml:
            devices = self._servod.get_devices()
            if not devices:
                self._logger.warning("No devices found, skipping XML dump")
            elif len(devices) == 1:
                devices[0].dump_to_xml(sopts.dump_xml)
                self._logger.info("Dumped XML config to %s", sopts.dump_xml)
            else:
                base, ext = os.path.splitext(sopts.dump_xml)
                for dev in devices:
                    prefixes = dev.get_prefixes()
                    prefix = prefixes[0] if prefixes else dev.template.TYPE
                    # Clean up empty prefixes (e.g., the main DUT connection)
                    if not prefix:
                        prefix = "main"

                    # If base points to a dir, avoid files like "_main.xml"
                    # and instead create "main.xml" directly.
                    if (
                        base.endswith(os.sep)
                        or not os.path.basename(base)
                        or os.path.isdir(sopts.dump_xml)
                    ):
                        # Ensure trailing slash if missing and base is meant to be a dir
                        if not base.endswith(os.sep):
                            base += os.sep
                        dev_filename = f"{base}{prefix}{ext if ext else '.xml'}"
                    else:
                        dev_filename = f"{base}_{prefix}{ext}"
                    dev.dump_to_xml(dev_filename)
                    self._logger.info(
                        "Dumped XML config for %s to %s", dev, dev_filename
                    )

        self._setup_servod_server()
        self._server_thread = threading.Thread(target=self._serve)
        self._server_thread.daemon = True
        self._turndown_initiated = False
        # Needs access to the servod instance.
        self._watchdog_thread = watchdog.DeviceWatchdog(
            self._servod, reconnect_timeout=sopts.reconnect_timeout
        )
        self._servod.set_watchdog(self._watchdog_thread)
        self._exit_status = 0

    def handle_sig(self, signum):
        """Handle a signal by turning off the server & cleaning up servod."""
        if not self._turndown_initiated:
            self._turndown_initiated = True
            self._logger.info("Received signal: %d. Attempting to turn off", signum)
            self._grpc_server.stop(0)
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
            "--no-hwinit",
            default=False,
            action="store_true",
            help="Skip the hardware initialization (hwinit) phase during startup. "
            "Useful for starting servod quickly when the DUT is unresponsive "
            "or in hibernate.",
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
            default=_get_bool_env_var("SERVOD_DISABLE_HOST_USB3", True),
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
        server_pars.add_argument(
            "--dump-xml",
            type=str,
            default=None,
            help="Path to dump the full parsed system config as an XML file. "
            "If multiple devices exist, they will be written with a prefix.",
        )
        server_pars.add_argument(
            "--grpc-core-port",
            type=int,
            default=None,
            help="gRPC port that Core service will listen on",
        )
        server_pars.add_argument(
            "--grpc-data-host",
            type=str,
            default=os.environ.get("SERVOD_GRPC_DATA_HOST", "localhost"),
            help="gRPC Data service host to connect to",
        )
        server_pars.add_argument(
            "--grpc-data-port",
            type=int,
            default=None,
            help="gRPC Data service port to connect to",
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
            action=servo_parsing.StoreAndMarkAction,
            help="include config file (XML) for given board",
        )
        dev_pars.add_argument(
            "-m",
            "--model",
            default="",
            type=str,
            action=servo_parsing.StoreAndMarkAction,
            help="optional config for a model of the given board, requires --board",
        )
        dev_pars.add_argument(
            "--noboard",
            action=servo_parsing.StoreTrueAndMarkAction,
            default=False,
            help="Explicitly indicate no board is intended",
        )
        dev_pars.add_argument(
            "--nomodel",
            action=servo_parsing.StoreTrueAndMarkAction,
            default=False,
            help="Explicitly indicate no model is intended",
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
        server_pars.format_usage = help_parser.format_usage  # type: ignore
        dev_pars.format_usage = help_parser.format_usage  # type: ignore
        self.help_parser = help_parser
        self.server_pars = server_pars
        self.dev_pars = dev_pars
        # Generator function for an empty namespace for a servo device.
        self.devopts_generator = lambda: self.dev_pars.parse_args([])

    def _parse_args(self, cmdline: List[str]) -> Tuple[Any, List[Any]]:
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
        if servo_parsing.arg_marked_as_user_supplied(sopts, "port"):
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
        dev_entries = finder.discover_servos()
        main_dev_entry = finder.choose_main_device(dev_entries)
        finder.generate_prefixes(dev_entries, main_dev_entry)
        finder.validate_devopts(dev_entries)
        return (dev_entries, main_dev_entry)

    def _setup_servos(self, dev_entries, _main_dev_entry, grpc_data_addr):
        """Setup servo devices for this servod instance.

        Args:
          dev_entries: all the devices' ServoDeviceEntry
          main_dev_entry: the main device's ServoDeviceEntry
          grpc_data_addr: tuple of host and port of data grpc service
        """

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

            data_host, data_port = grpc_data_addr
            channel = grpc.insecure_channel(f"{data_host}:{data_port}")
            system_config_client = system_config_grpc.SystemConfig(channel)

            for config in all_configs:
                response = system_config_client.AddCfgFile(
                    prefix=devopts.prefix[0] if devopts.prefix else "",
                    filename=config,
                    vid=dev_entry.vid,
                    pid=dev_entry.pid,
                    serial=dev_entry.serial,
                )
                for line in response.loglines:
                    self._logger.info(line.strip())

            system_config_client.Finalize(
                vid=dev_entry.vid, pid=dev_entry.pid, serial=dev_entry.serial
            )

            servo_device = servo_dev.ServoDevice(
                dev_entry=dev_entry,
                grpc_data_addr=grpc_data_addr,
                interfaces=devopts.interfaces,
                servod=weakref.proxy(self._servod),
            )

            board_supplied = getattr(devopts, "board_supplied_by_user", False)
            model_supplied = getattr(devopts, "model_supplied_by_user", False)

            if servo_device.template.DUT_CONTROLLER and not board_supplied:
                self._logger.warning(
                    "No board provided for DUT controller %s. "
                    "Start device without board specific config.",
                    servo_device,
                )
                servo_device.set_base_board(devopts.board)

            if getattr(devopts, "noboard", False) and board_supplied:
                raise ServodError("Cannot provide both --board and --noboard.")

            if getattr(devopts, "nomodel", False) and model_supplied:
                raise ServodError("Cannot provide both --model and --nomodel.")

            if not getattr(devopts, "noboard", False):
                if not getattr(devopts, "board", ""):
                    raise ServodError(
                        "No board provided. Please provide "
                        "--board <board> or use --noboard to explicitly "
                        "indicate no board is intended."
                    )

                if (
                    devopts.board
                    and not model_supplied
                    and not getattr(devopts, "nomodel", False)
                ):
                    models_response = system_config_client.GetAvailableModels(
                        board=devopts.board
                    )
                    if models_response.models:
                        raise ServodError(
                            "Board %s has models: %s. Please specify "
                            "--model or use --nomodel."
                            % (devopts.board, ", ".join(models_response.models))
                        )

            # Set the board and the model for a DUT
            if devopts.board:
                if not servo_device.set_board_and_model(devopts.board, devopts.model):
                    if not getattr(devopts, "noboard", False):
                        raise ServodError(
                            "Cannot find XML overlay for board %s (model: %s). "
                            "Please check the board/model name."
                            % (
                                devopts.board,
                                devopts.model if devopts.model else "None",
                            )
                        )

                    self._logger.warning(
                        "Cannot set up board %s for device %s. "
                        "Start device without board specific config.",
                        devopts.board,
                        servo_device,
                    )

            if self.opts.debug:
                self._logger.debug(
                    "System configs for device %s\n%s",
                    dev_entry,
                    servo_device.doc_all(),
                )

            for prefix in dev_entry.devopts.prefix:
                self._servod.add_device(servo_device, prefix)

        self._servod.update_known_ctrls()
        for servo_device in self._servod.get_devices():
            # Real init this time i.e. initialization will fail if there are issues
            # with creating the servo interfaces
            servo_device.init_servo_interfaces()
        self._servod.update_known_ctrls()

    def _resolve_fission_ports(self, sopts):
        """Resolve gRPC ports for Fission architecture."""
        if sopts.grpc_core_port is None:
            sopts.grpc_core_port = int(f"1{self._servo_port}")
            self._logger.info("Resolved gRPC Core Port: %d", sopts.grpc_core_port)
        if sopts.grpc_data_port is None:
            sopts.grpc_data_port = int(f"2{self._servo_port}")
            self._logger.info("Resolved gRPC Data Port: %d", sopts.grpc_data_port)

    def _spawn_data_service(self, sopts):
        """Spawn the servod_data subprocess."""
        # Find the path to grpc_server_setup.py relative to this file
        # This file is in servo/core/servod.py
        # Script is in servo/data/grpc_server/grpc_server_setup.py

        current_dir = os.path.dirname(os.path.abspath(__file__))
        data_script = os.path.abspath(
            os.path.join(
                current_dir, "..", "data", "grpc_server", "grpc_server_setup.py"
            )
        )

        # Base logdir is where servod placed its logs, e.g. /var/log/servod_9999
        # The data service will create its own subdirectory under it.
        nested_logdir = os.path.join(sopts.log_dir, f"servod_{self._servo_port}")

        try:
            os.makedirs(nested_logdir, exist_ok=True)
        except OSError as e:
            self._logger.warning(
                "Failed to create nested data log dir %s: %s", nested_logdir, e
            )

        cmd = [
            sys.executable,
            data_script,
            "--grpc-core-host",
            "localhost",
            "--grpc-core-port",
            str(sopts.grpc_core_port),
            "--grpc-data-port",
            str(sopts.grpc_data_port),
            "--logs",
            nested_logdir,
        ]

        if sopts.debug:
            cmd.append("--debug")

        env = os.environ.copy()
        env["GRPC_POLL_STRATEGY"] = "epoll1"

        self._logger.info(
            "Cleaning up any orphaned Data Service on port %d...", sopts.grpc_data_port
        )
        try:
            pattern = f"grpc_server_setup.py.*--grpc-data-port {sopts.grpc_data_port}"
            subprocess.run(
                ["pkill", "-f", pattern],
                check=False,
                stderr=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
            )
            time.sleep(0.5)
        except Exception as e:
            self._logger.debug("Failed to clean up orphaned data service: %s", e)

        self._logger.info("Spawning Data Service: %s", " ".join(cmd))
        self._data_service_proc = subprocess.Popen(cmd, env=env, start_new_session=True)

    def cleanup(self):
        """Perform any cleanup related work after servod server shut down."""
        if hasattr(self, "_data_service_proc") and self._data_service_proc:
            self._logger.info("Terminating Data Service subprocess...")
            self._data_service_proc.terminate()
            try:
                self._data_service_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._logger.warning("Data Service did not exit, killing it.")
                self._data_service_proc.kill()
        self._scratchutil.remove_entry(self._servo_port)
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

        def handler(signum, _unused, starter=self):
            starter.handle_sig(signum)

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
            self._scratchutil.add_entry(self._servo_port, serials, os.getpid())
        except scratch.ScratchError as e:
            self._logger.error(f"Failed to add scratch entry: {e}")
            self._servod.close()
            sys.exit(1)
        self._watchdog_thread.start()
        self._server_thread.start()
        # Indicate that servod is running for any process waiting to know.
        self._scratchutil.mark_active(self._servo_port)
        signal.pause()
        # Set watchdog thread to end
        self._watchdog_thread.deactivate()
        # Collect servo and watchdog threads
        self._server_thread.join(self.EXIT_TIMEOUT_S)
        if self._server_thread.is_alive():
            self._logger.error(
                "Server thread not turned down after %s s.", self.EXIT_TIMEOUT_S
            )

        self._grpc_server.stop(0)
        self._watchdog_thread.join(self.EXIT_TIMEOUT_S)
        if self._watchdog_thread.is_alive():
            self._logger.error(
                "Watchdog thread not turned down after %s s.", self.EXIT_TIMEOUT_S
            )
        self.cleanup()
        sys.exit(self._exit_status)

    def exit_if_in_chroot(self):
        """Check if we are running in the cros_sdk (chroot).

        Returns:
            bool: True if in chroot and orchestration is requested, False otherwise.
        """
        in_chroot = os.environ.get("CROS_WORKON_SRCROOT") is not None or os.path.exists(
            "/etc/cros_chroot_version"
        )

        if in_chroot:
            if os.environ.get("I_NEED_SERVOD") == "1":
                self._logger.info(
                    "Running in cros_sdk with I_NEED_SERVOD=1. "
                    "Orchestrating Fission services."
                )
                return True

            self._logger.fatal(
                "\nRunning servod in the cros_sdk is no longer supported.\n"
                "Please refer to https://chromium.googlesource.com/"
                "chromiumos/third_party/hdctools/+/main/docs/"
                "servod_outside_chroot.md"
            )
            sys.exit(1)
        return False

    def _check_for_excluded_modules(self):
        """Check for excluded kernel modules and exit if found."""
        proc_modules_path = "/host_proc_modules"
        if not os.path.exists(proc_modules_path):
            proc_modules_path = "/proc/modules"

        if not os.path.exists(proc_modules_path):
            return

        try:
            with open(proc_modules_path, "r", encoding="utf-8") as f:
                loaded_modules = {line.split()[0] for line in f if line.strip()}
        except OSError as e:
            self._logger.warning("Could not read %s: %s", proc_modules_path, e)
            return

        found = EXCLUDED_KERNEL_MODULES & loaded_modules
        if found:
            self._logger.fatal(
                "Problematic kernel modules detected: %s. "
                "These modules are known to cause issues with servod. "
                "Please unload them (e.g., 'sudo rmmod <module>') before "
                "starting servod.",
                ", ".join(found),
            )
            sys.exit(1)


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
    try:
        hubs = list(
            usb.core.find(
                find_all=True,
                idVendor=_GENESYS_USB3_HUB_VID,
                idProduct=_GENESYS_USB3_HUB_PID,
                serial_number=None,
            )
        )
    except usb.core.NoBackendError:
        logging.warning("No USB backend available. Skipping USB3 hub check.")
        return

    for hub in hubs:
        try:
            # We don't care if it's already detached.
            try:
                hub.detach_kernel_driver(0)
            except usb.core.USBError:
                pass
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
        except usb.core.USBError as e:
            logging.warning("Failed to disable USB3 hub %s: %s", hub, e)

    if len(hubs) > 0:
        time.sleep(3)


# pylint: disable=dangerous-default-value
# Ability to pass an arbitrary or artificial cmdline for testing is desirable.
def main(cmdline=sys.argv[1:]):
    """Main function for servod."""
    try:
        starter = ServodStarter(cmdline)
    except (ServodError, servo_dev.ServoDeviceError) as error:
        logging.getLogger(os.path.basename(sys.argv[0])).error("Error: %s", error)
        sys.exit(1)
    except Exception as error:
        logging.getLogger(os.path.basename(sys.argv[0])).exception(
            "Fatal error during servod startup: %s", error
        )
        sys.exit(1)
    starter.serve()


if __name__ == "__main__":
    main()
