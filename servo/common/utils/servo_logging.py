# Copyright 2019 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Module for logging on servod.

The logging extension here is meant to support easier debugging and make sure
that no information is lost, and finding the right information is simple.
The basic structure is that inside a directory (by default /var/log/ there
are servod log directories, one per port. As there can only be at most one
instance per port, this removes the need to coordinate file writing and
rotation across instances.
Inside that directory, the logs are rotated. Each log file has the following
naming convention.
log.YYYY-MM-DD--HH-MM-SS.MS.LOGLEVEL[.x]
(prefix).(invocation date & time (local time))(log level)[seq num]
e.g. log.2019-07-01--21-21-06.9582.DEBUG.1.tbz2
When a new instance is started on the same port, the old open log is closed
and rotated, and a new log file with a new timestamp is started.
So all files for one invocation share the same timestamp in the filename,
and can be read sequentially by using the sequence numbers.
We only keep a fixed size of logs for an instance. If the log size grows beyond
the limit, the oldest log of the instance will be removed. Logs of the older
instances will also be cleaned up.
All instances on the same port are in the same directory.
"""
# pylint: disable=invalid-name
# File is an extension to the standard library logger. Conform to their code
# style.

import datetime
import logging
import logging.handlers
import os
import re
import tarfile
import uuid


# Format strings used for servod logging in files.
DEFAULT_FMT_STRING = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEBUG_FMT_STRING = (
    "%(asctime)s - %(name)s - %(levelname)s - "
    "%(filename)s:%(lineno)d:%(funcName)s - %(message)s"
)

# Format strings used for servod logging to stdout/stderr.
SHORT_DEFAULT_FMT_STRING = "%(asctime)s(%(name)s) %(message)s"
SHORT_DEBUG_FMT_STRING = (
    "%(asctime)s(%(name)s) %(filename)s:%(lineno)d:%(funcName)s %(message)s"
)

# Convenience map to have access to format string and level using a shorthand.
LOGLEVEL_MAP = {
    "critical": (logging.CRITICAL, DEFAULT_FMT_STRING),
    "error": (logging.ERROR, DEFAULT_FMT_STRING),
    "warning": (logging.WARNING, DEFAULT_FMT_STRING),
    "info": (logging.INFO, DEFAULT_FMT_STRING),
    "debug": (logging.DEBUG, DEBUG_FMT_STRING),
}

SHORT_LOGLEVEL_MAP = {
    "critical": (logging.CRITICAL, SHORT_DEFAULT_FMT_STRING),
    "error": (logging.ERROR, SHORT_DEFAULT_FMT_STRING),
    "warning": (logging.WARNING, SHORT_DEFAULT_FMT_STRING),
    "info": (logging.INFO, SHORT_DEFAULT_FMT_STRING),
    "debug": (logging.DEBUG, SHORT_DEBUG_FMT_STRING),
}

# Default loglevel used on servod for stdout logger.
DEFAULT_LOGLEVEL = "info"

# Levels used to generate logs in servod in parallel.
# On initialization, a handler for each of these levels is created.
LOGLEVEL_FILES = ["debug", "warning", "info"]

LOGLEVEL_RE_GROUP = "loglevel"

# Regex to extract the loglevel, and rollover_id from a given filename.
extractor_re = re.compile(
    r"(?P<%s>%s)([.]\d+)?$"
    % (LOGLEVEL_RE_GROUP, "|".join(f.upper() for f in LOGLEVEL_FILES))
)

# Max log size for one log file. ~5 MB
MAX_LOG_BYTES = 5 * 1024 * 1024

# Max number of logs to keep around per port.
# Since logging is used for multiple concurrent logfiles (DEBUG, INFO, WARNING)
# this limit is set assuming that the output of INFO + WARNING will not be more
# than DEBUG.
LOG_BACKUP_COUNT = 20

# Filetype suffix used for compressed logs.
COMPRESSION_SUFFIX = "tbz2"

# Each logfile starts with this prefix.
LOG_FILE_PREFIX = "log"

# link name to the latest, open log file
LINK_PREFIX = "latest"

# The timestamp that identifies the instance is cached in this file.
TS_FILE = "ts"

# Format string for the timestamps used instance differentiation.
TS_FORMAT = "%Y-%m-%d--%H-%M-%S.%f"


# Follows servod error naming convention.
class ServoLoggingError(Exception):
    """Error to throw on logging issues."""


def _buildLogdirName(logdir, module, port):
    """Helper to generate the log directory for an instance at |port|.

    Args:
      logdir: path to directory where all of servod logging should reside
      port: port of the instance for the logger

    Returns:
      str, path for directory where servod logs for instance at |port| should go
    """
    # This ensures when running e2e tests in parallel that each run has its own unique
    # path.
    if "PYTEST_XDIST_TESTRUNUID" in os.environ:
        module += os.environ["PYTEST_XDIST_TESTRUNUID"]
    return os.path.join(logdir, "%s_%s" % (module, str(port)))


def _generateTs(time=None):
    """Helper to generate a timestamp to tag per-instance logs.

    Args:
      time: a datetime to generate the timestamp

    Returns:
      formatted timestamp of time when called
    """
    # servo logging uses milliseconds, and %f returns microseconds. Remove the
    # last three digits.
    if time is None:
        time = datetime.datetime.now()
    return time.strftime(TS_FORMAT)[:-3]


def _sortLogTagFn(f):
    """Helper function to pass to .sort for a loglevel.

    If the filename ends with loglevel, it's the lowest priority.
    If it ends with an integer, the priority is the integer.
    Compression suffix does not matter.

    Args:
      f: file to evaluate

    Returns:
      int, sorting priority for |f| within its own tag (rollover number)
    """
    if COMPRESSION_SUFFIX in f:
        # Remove the compression suffix and the period with it.
        f = f[: -(len(COMPRESSION_SUFFIX) + 1)]
    last_component = f.split(".")[-1]
    if last_component.isdigit():
        return int(last_component)
    return 0


def _sortLogs(logfiles, loglevel):
    """Helper to sort logfiles for a given |loglevel|.

    The logfile format is log.[timestamp/instance-tag].[loglevel].[seq#][compress]

    While the timestamp is increasing i.e. later is newer, the sequence number
    is decreasing i.e. no seq number is newer than .1 etc. This is a helper
    to sort first by tags and then within each tag by the sequence numbers.


    Args:
      logfiles: list, files to sort
      loglevel: loglevel string in all the file names

    Returns:
      chronological_logfiles: list, sorted input of logfiles, where the first
                              element is the newest logfile
    """
    chronological_logfiles = []
    # To determine the oldest files, first one needs to sort by instance
    # tag i.e. the newest one is the highest one (reverse). Then, within the
    # instance tag, the newest one is the smallest one (no suffix, .1, etc).
    instance_tags = list(set(f.split(loglevel)[0] for f in logfiles))
    instance_tags.sort(reverse=True)
    for tag in instance_tags:
        tag_logfiles = sorted([f for f in logfiles if tag in f], key=_sortLogTagFn)
        chronological_logfiles.extend(tag_logfiles)
    return chronological_logfiles


class UTCFormatter(logging.Formatter):
    """A formatter that always prints dates in UTC in ISO-8601 format."""

    def formatTime(self, record, datefmt=None):
        return datetime.datetime.fromtimestamp(
            record.created, datetime.timezone.utc
        ).isoformat(timespec="milliseconds")


class ShortUTCFormatter(logging.Formatter):
    """A formatter that prints UTC time without date and with single digit ms."""

    def formatTime(self, record, datefmt=None):
        # Format: HH:MM:SS.f
        # truncate microseconds to tenths of a second
        return datetime.datetime.fromtimestamp(
            record.created, datetime.timezone.utc
        ).strftime("%H:%M:%S.%f")[:-5]


def setup(logdir, module, port, debug_stderr=False, backup_count=LOG_BACKUP_COUNT):
    """Setup servod logging.

    This function handles setting up logging, whether it be normal basicConfig
    logging, or using logdir and file logging in servod.

    Args:
      logdir: str, log directory for all servod logs (*)
      module: str, prefix for log directory, either servod or data.
      port: port used for current instance
      debug_stderr: whether the stderr logs should be debug
      backup_count: max number of compressed and uncompressed files to keep around

    (*) if |logdir| is None, the system will not setup log handlers, but rather
    setup logging using basicConfig()
    """
    # Suppress gRPC C++ core logs which can be very noisy (e.g. keepalive errors).
    # This must be set before grpc is initialized in any subprocess/thread.
    if debug_stderr:
        os.environ.setdefault("GRPC_VERBOSITY", "DEBUG")
    else:
        os.environ.setdefault("GRPC_VERBOSITY", "NONE")
    root_logger = logging.getLogger()
    # Let the root logger process every log message, while the different
    # handlers chose which ones to put out.
    root_logger.setLevel(logging.DEBUG)
    stderr_level = "debug" if debug_stderr else DEFAULT_LOGLEVEL
    # |log_dir| is None iff it's not in the cmdline. Otherwise it contains
    # a directory path to store the servod logs in.

    # Fix the log level on the stderr logger that was created in
    # ServodStarter.__init__
    for handler in root_logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            short_level, short_fmt = SHORT_LOGLEVEL_MAP[stderr_level]
            logging.info(
                "Updating log level & formatter of %s to %s/%s",
                handler,
                short_level,
                short_fmt,
            )
            handler.setLevel(short_level)
            handler.formatter = ShortUTCFormatter(fmt=short_fmt)
    if logdir:
        # Start file loggers for each output file.
        instance_logdir = _buildLogdirName(logdir, module, port)
        logging_ts = _generateTs()
        if not os.path.isdir(instance_logdir):
            os.makedirs(instance_logdir)
        elif os.lstat(instance_logdir).st_uid != os.geteuid():
            raise OSError(1, "Log directory not owned by user", instance_logdir)
        for level in LOGLEVEL_FILES:
            fh_level, fh_fmt = LOGLEVEL_MAP[level]
            if module == "data":
                fh = logging.handlers.WatchedFileHandler(
                    os.path.join(logdir, f"latest.{level.upper()}")
                )
                fh.setLevel(fh_level)
                fh.setFormatter(UTCFormatter(fmt=fh_fmt))
            else:
                fh = ServodRotatingFileHandler(
                    logdir=instance_logdir,
                    ts=logging_ts,
                    fmt=fh_fmt,
                    backup_count=backup_count,
                    level=fh_level,
                )
                # Ensure that the global backup limit is kept across instances.
                fh.pruneOldLogsAcrossInstances()
            root_logger.addHandler(fh)


class ServodRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """Extension to the default RotatingFileHandler.

    The two additions are:
      - rotated files are compressed
      - backup count is applied across the directory and not just the base
    See above for details.
    """

    def __init__(
        self, logdir, ts, fmt, backup_count=LOG_BACKUP_COUNT, level=logging.DEBUG
    ):
        """Wrap original init by forcing one rotation on init.

        Args:
          logdir: str, path to log output directory
          ts: str, timestamp used to create logfile name for this instance
          fmt: str, output format to use
          backup_count: max number of compressed and uncompressed files to keep
                        around
          level: loglevel to use
        """
        self.levelsuffix = logging.getLevelName(level)
        self._logger = logging.getLogger(
            "%s.%s" % (type(self).__name__, self.levelsuffix)
        )
        self.linkname = "%s.%s" % (LINK_PREFIX, self.levelsuffix)
        self.logdir = logdir
        self.levelBackupCount = backup_count
        filename = self._buildFilename(ts)
        logging.handlers.RotatingFileHandler.__init__(
            self, filename=filename, backupCount=backup_count, maxBytes=MAX_LOG_BYTES
        )
        self.updateConvenienceLink()
        # Level and format for ServodRotatingFileHandlers are set once at init
        # and then cannot be changed. Therefore, those methods are wrapped in a
        # noop.
        formatter = UTCFormatter(fmt=fmt)
        logging.handlers.RotatingFileHandler.setLevel(self, level)
        logging.handlers.RotatingFileHandler.setFormatter(self, formatter)

    def setLevel(self, level):
        """Noop to avoid setLevel being triggered."""
        self._logger.warning(
            "setLevel is not supported on %s. Please consider "
            "changing the code here.",
            type(self).__name__,
        )

    def setFormatter(self, fmt):
        """Noop to avoid setFormatter being triggered."""
        self._logger.warning(
            "setFormatter is not supported on %s. Please consider "
            "changing the code here.",
            type(self).__name__,
        )

    def _getLinkpath(self):
        """Helper to create symbolic link name."""
        return os.path.join(self.logdir, self.linkname)

    def updateConvenienceLink(self):
        """Generate a symbolic link to the latest file."""
        linkfile = self._getLinkpath()
        tmplink = f"{linkfile}.{uuid.uuid4().hex}.tmp"
        try:
            os.symlink(os.path.basename(self.baseFilename), tmplink)
            os.replace(tmplink, linkfile)
        finally:
            if os.path.lexists(tmplink):
                os.remove(tmplink)

    def _buildFilename(self, ts):
        """Helper to build the active log file's filename.

        Args:
          ts: timestamp string

        Returns:
          Full path of the logfile for the given timestamp.
        """
        return os.path.join(
            self.logdir, "%s.%s.%s" % (LOG_FILE_PREFIX, ts, self.levelsuffix)
        )

    @staticmethod
    def getCompressedPathname(path):
        """Helper to encapsulate compressed filename logic.

        If |path| does not have a number at its end, it means that it's the first,
        unrotated log to be compressed. In that case, append a 0, so that sorting
        will show it above all others.

        Args:
          path: str, pathname to analyze

        Returns:
          compressed pathname, str, of how |path| should be called post compression
        """
        malleable_path = path
        if not path[-1].isdigit():
            # This means the normal active file is being compressed. At the danger
            # of there being other files, to ensure sorting, append a 0.
            malleable_path = "%s.0" % path
        return "%s.%s" % (malleable_path, COMPRESSION_SUFFIX)

    @staticmethod
    def compressFn(path):
        """Compress file at |path|.

        Args:
          path: path to file to compress.
        """
        if COMPRESSION_SUFFIX not in path:
            # Do not unnecessarily recompress files.
            compressed_path = ServodRotatingFileHandler.getCompressedPathname(path)
            with tarfile.open(compressed_path, "w:bz2") as tar:
                tar.add(path, recursive=False)
            # This file has been compressed and can be safely deleted now.
            os.remove(path)

    def pruneOldLogsAcrossInstances(self):
        """Helper to enforce |self.levelBackupCount| across instances."""
        # Servod backup counts are meant across invocations on the same port.
        # Therefore, this needs to find all logs in the logdir for the level and
        # make sure that the backup count does not grow too large.
        loglevel_logs = []
        for logfile in os.listdir(self.logdir):
            logpath = os.path.join(self.logdir, logfile)
            if not os.path.islink(logpath) and self.levelsuffix in logpath:
                # Exclude the linkname from search and sort.
                loglevel_logs.append(logpath)
        sorted_logs = _sortLogs(loglevel_logs, self.levelsuffix)
        # The +1 here is needed as the idea is to keep |backupCount| backups
        # around in addition to the active logfile.
        remove_logs = sorted_logs[self.levelBackupCount + 1 :]
        for fp in remove_logs:
            os.remove(fp)

    def doRollover(self):
        """Extend stock doRollover to prune old logs.

        In addition to regular filename rotation this also ensures that the backup
        count does not grow beyond the backup count across the |logdir| and not just
        the baseFilename.
        """
        logging.handlers.RotatingFileHandler.doRollover(self)
        self.updateConvenienceLink()
        self.pruneOldLogsAcrossInstances()


class FuncNameAligner(logging.Filter):
    """
    Class to align the function names without having to alter the log format
    """

    def __init__(self, padding):
        """Instance initializer

        Args:
          padding: number of spaces to reserve for function name
        """
        super().__init__()
        self.padding = padding

    def filter(self, record):
        """Modify the record, then allow it to be logged by returning True"""
        record.funcName = record.funcName.ljust(self.padding)
        return True

    def __eq__(self, other):
        """Equality check to prevent duplicates

        Args:
          other: Another object which may or may not be an instance of our class

        Returns:
          True when the objects have the same parameters
        """
        if isinstance(other, self.__class__):
            return self.padding == other.padding
        return False

    def __ne__(self, other):
        """Inequality check

        Args:
          other: Another object which may or may not be an instance of our class

        Returns:
          The negation of the equality operator
        """
        return not self.__eq__(other)


class _ControlWrapper:
    """
    When running tests, it's nice to be able to see all the servod calls the test
    is making, without having to open the DEBUG log full of console output and
    implementation details.

    Some set() and get() calls result in additional calls, so now they are logged
    with indentation.

    The child classes define the actual text for the log messages.
    """

    # Number of characters to log before switching to just logging the count
    # servo_micro_uart_stream = '2020-02-19 14:11:37 chan save\r\n2020-02-19 ...
    MAX_VALUE_LEN = 80

    # The history of recursive set/get/set calls
    # This is a class attribute so indentation can be shared between instances.
    call_stack = []

    def __init__(self, name, known_exceptions=(AttributeError,)):
        """Instance initializer

        Args:
          name: the name of the control being invoked
          known_exceptions: a tuple of exception classes to count as "ordinary"
                            in _log_exception
        """
        self.logger = logging.getLogger("Controls")
        self.logger.addFilter(FuncNameAligner(len("_log_success")))
        self.depth = len(self.__class__.call_stack)
        self.indent = "  " * self.depth
        self.name = name
        self._known_exceptions = tuple(known_exceptions)

    def __str__(self):
        """String representation of this wrapper object."""
        return "<%s %s>" % (self.__class__.__name__, self.name)

    def _truncate_string(self, val):
        """If string is very long, truncate it and note how long it was.

        Args:
          val (str): The original value

        Returns:
          A reformatted representation of the original value
        """
        if isinstance(val, str) and len(val) > self.MAX_VALUE_LEN:
            # The output should already be there, via LogConsoleOutput.
            # Abbreviate the output: ec_uart_stream   = (962 characters) '2020-...
            return "(%d characters) %s..." % (len(val), val[: self.MAX_VALUE_LEN])
        return val

    def __enter__(self):
        """Upon entering the context, log that the call is starting."""
        self._log_start()

        # Record self in the stack, so inner calls are indented.
        self.__class__.call_stack.append(str(self))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Report any exception that occurred inside the context manager.

        Args:
          exc_type (type): The class of the captured exception, if any
          exc_value (Exception): The exception object
          exc_tb: The traceback object
        """

        # Remove one level from the call stack, since this call is done.
        if self.__class__.call_stack:
            self.__class__.call_stack.pop(-1)

        if exc_val is None:
            self._log_success()
            return

        self._log_exception(exc_type, exc_val, exc_tb)

    def _log_start(self):
        """Log the start of a call.  (Must be overridden.)"""
        raise NotImplementedError()

    def _log_success(self):
        """Log a successful finish: exception not raised.  (Must be overridden.)"""
        raise NotImplementedError()

    def _log_exception(self, exc_type, exc_val, exc_tb):
        """Log any exception caused by the call.  (Must be overridden.)

        Args:
          exc_type (type): The class of the captured exception, if any
          exc_value (Exception): The exception object
          exc_tb: The traceback object
        """
        raise NotImplementedError()


class WrapSetCall(_ControlWrapper):
    """
    This class is a context manager for use around "set" calls.

    It logs the before and after, and logs the exception that exited the context,
    if one happened.

    Format:
      Controls - DEBUG - (SET) fw_wp_state         force_off
      Controls - DEBUG -   (SET) fw_wp_vref          pp3300
      Controls - DEBUG -   (set) fw_wp_vref        : pp3300
      Controls - DEBUG -   (SET) fw_wp_en            on
      Controls - DEBUG -   (set) fw_wp_en          : on
      Controls - DEBUG -   (SET) fw_wp               off
      Controls - DEBUG -   (set) fw_wp             : off
      Controls - DEBUG - (set) fw_wp_state      : force_off
    """

    def __init__(self, name, value, known_exceptions=(AttributeError,)):
        """Instance initializer

        Args:
          name:  the name of the control
          value: the value to be set
          known_exceptions: a tuple of exception classes to count as "ordinary"
                            in _log_exception
        Example:
          with WrapSetCall(name, value):
            ...

        """
        super().__init__(name, known_exceptions)
        self.value = value

    def _log_start(self):
        """Log the start of a set() operation, indicating the value to be set."""
        self.logger.debug("%s(SET) %-16s   %s", self.indent, self.name, self.value)

    def _log_success(self):
        """Log the success of a set() operation, showing that the value was set."""
        self.logger.debug("%s(set) %-16s : %s", self.indent, self.name, self.value)

    def _log_exception(self, exc_type, exc_val, exc_tb):
        """Log any exception coming from the driver's actual set() operation.

        Args:
          exc_type (type): The class of the captured exception, if any
          exc_value (Exception): The exception object
          exc_tb: The traceback object
        """

        if isinstance(exc_val, self._known_exceptions):
            # Ordinary exceptions: ERROR shows only first line; DEBUG shows traceback.
            first_line = str(exc_val).split("\n", 1)[0]
            self.logger.error(
                "(%s) Failed setting %s -> %s: %s",
                exc_type.__name__,
                self.name,
                self.value,
                first_line,
            )
        else:
            # Inform the user of errors that shouldn't happen and need investigation.
            self.logger.error(
                "(%s) Unknown issue setting %s -> %s. "
                "Please take a look in the DEBUG logs.",
                exc_type.__name__,
                self.name,
                self.value,
            )
        self.logger.debug(
            "(%s) Details:", exc_type.__name__, exc_info=(exc_type, exc_val, exc_tb)
        )


class WrapGetCall(_ControlWrapper):
    """
    This class is a context manager for use around "get" calls.

    It logs the before and after, and logs the exception that exited the context,
    if one happened.

    Format:
      Controls - DEBUG - (GET) fw_wp_state      ?
      Controls - DEBUG -   (GET) fw_wp_en         ?
      Controls - DEBUG -   (get) fw_wp_en         = off
      Controls - DEBUG -   (GET) fw_wp            ?
      Controls - DEBUG -   (get) fw_wp            = on
      Controls - DEBUG - (get) fw_wp_state      = on

    If a value is very long (>MAX_VALUE_LEN characters), it is truncated, and a
    note is added stating how long it was originally:
      Controls - INFO - (get) ec_uart_stream   = (962 characters) '2020-02-...

    """

    def __init__(self, name, known_exceptions=(AttributeError,)):
        """Instance initializer

        Args:
          name: the name of the control being requested
          known_exceptions: a tuple of exception classes to count as "ordinary"
                            in _log_exception

        Examples:
          with WrapGetCall(name) as wrapper:
            ...
            result = ...
            wrapper.got_result(result)
        """
        super().__init__(name, known_exceptions)
        self.result = None
        self._result_reported = False

    def got_result(self, value):
        """Store the return value of the call, to be logged during __exit__."""
        self.result = value
        self._result_reported = True

    def _log_start(self):
        """Log the start of a get() operation, with value not known."""
        self.logger.debug("%s(GET) %-16s ?", self.indent, self.name)

    def _log_success(self):
        """Log the success of a get() operation, showing the retrieved value."""
        if self._result_reported:
            result_str = self._truncate_string(self.result)
        else:
            result_str = "[result not reported]"
        self.logger.debug("%s(get) %-16s = %s", self.indent, self.name, result_str)

    def _log_exception(self, exc_type, exc_val, exc_tb):
        """Log any exception coming from the driver's actual get() method."""

        if isinstance(exc_val, self._known_exceptions):
            # Ordinary exceptions: ERROR shows only first line; DEBUG shows traceback.
            first_line = str(exc_val).split("\n", 1)[0]
            self.logger.error(
                "(%s) Failed getting %s: %s", exc_type.__name__, self.name, first_line
            )

        else:
            # Inform the user of errors that shouldn't happen and need investigation.
            self.logger.error(
                "(%s) Unknown issue getting %s. "
                "Please take a look in the DEBUG logs.",
                exc_type.__name__,
                self.name,
            )

        self.logger.debug(
            "(%s) Details:", exc_type.__name__, exc_info=(exc_type, exc_val, exc_tb)
        )
