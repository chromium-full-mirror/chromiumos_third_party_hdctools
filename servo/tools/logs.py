# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# pylint: disable=logging-not-lazy

"""Logs tool to process the servod logs."""

import os
import re
import shutil
import tarfile

from servo.tools import tool


# default name of servod log directory
SERVOD_LOG_DIR = "/var/log/servod_%s"

# location of the output of log extraction
OUTPUT_DIR = "/tmp/servodlog/"
# naming pattern of the subdirectory is <servod log dir>.<servod instance timestamp>
OUTPUT_SUBDIR = OUTPUT_DIR + "%s.%s"

# naming pattern of the output of log extraction
OUTPUT_JOINT_LOG = "log.%s.txt"
OUTPUT_JOINT_DEBUG_LOG = OUTPUT_JOINT_LOG % "DEBUG"
OUTPUT_TAR = OUTPUT_DIR + "servodlog.tbz2"

# Levels used to generate logs in servod
LOG_LEVELS = ["DEBUG", "WARNING", "INFO"]

# Regex group to extract timestamp from logfile name.
TS_GROUP = "ts"
# This regex is used to extract the timestamp from servod logs.
# Files always start with log.
TS_RE = (
    r"log."
    # The timestamp is of format %Y-%m-%d--%H-%M-%S.MS
    r"(?P<%s>\d{4}(\-\d{2}){2}\-(-\d{2}){3}.\d{3})"
    # The loglevel is optional depending on labstation version.
    r"(.(INFO|DEBUG|WARNING))?"
    % TS_GROUP
)
TS_EXTRACTOR = re.compile(TS_RE)

# Regex group to extract MCU name from logline in servod logs.
MCU_GROUP = "mcu"
# Regex group to extract logline from MCU logline in servod logs.
LINE_GROUP = "line"
# This regex is used to extract the mcu and the line content from an
# MCU logline in servod logs. e.g. EC or servo_v4 console logs.
# Here is an example log-line:
#
# 2020-01-23 13:15:12,223 - servo_v4 - EC3PO.Console - DEBUG -
# console.py:219:LogConsoleOutput - /dev/pts/9 - cc polarity: cc1
#
# Here is conceptually how they are formatted:
#
#  <time> - <MCU> - EC3PO.Console - <LVL> - <file:line:func> - <pts> -
#  <output>
#
# The log format starts with a timestamp
MCU_RE = (
    r"[\d\-]+ [\d:,]+ "
    # The mcu that is logging this is next.
    r"- (?P<%s>\w+) - "
    # Next, we have more log outputs before the actual line.
    # Information about the file line, logging function etc.
    # Anchor on EC3PO Console, LogConsoleOutput and dev/pts.
    # NOTE: if the log format changes, this regex needs to be
    # adjusted.
    r"EC3PO\.Console[\s\-\w\d:.]+LogConsoleOutput - /dev/pts/\d+ - "
    # Lastly, we get the MCU's console line.
    r"(?P<%s>.+$)"
    % (MCU_GROUP, LINE_GROUP)
)
MCU_EXTRACTOR = re.compile(MCU_RE)


class LogsError(Exception):
    """Logs tool error class."""


class Logs(tool.Tool):
    """Class to implement various subtools to process servod logs."""

    @property
    def help(self):
        """Tool help message for parsing."""
        return "Process servod logs."

    def extract(self, args):
        """Extract MCU logs from servod logs to a tar file and print its location.

        Args:
          args.port: port(s) where the servod instance is listening
          args.directory: directory(s) that contains servod logs
          args.previous: if true, extract logs of latest and previous deployments of
                         servod. otherwise, only extract logs of the latest deployment
        """
        log_dirs = set()
        if args.port is not None:
            log_dirs = [SERVOD_LOG_DIR % str(port) for port in args.port]
        else:
            log_dirs = args.directory
        # dedup
        log_dirs = set(log_dirs)
        # verify all log directories exist before extracting
        for log_dir in log_dirs:
            if not os.path.exists(log_dir):
                self.error("Servod log directory %s not exist." % log_dir)
        # clean up all old extracted log files by deleting and recreating OUTPUT_DIR
        _cleanup_output_dir()
        combine_log_subdirs = []
        for log_dir in log_dirs:
            combine_log_subdirs += self._extract_one_dir(log_dir, args.previous)
        if combine_log_subdirs:
            _make_tarfile(OUTPUT_TAR, combine_log_subdirs)
            self._logger.info("\nExtracted MCU log for:\n%s\n" % "\n".join(log_dirs))
            self._logger.info("MCU logs extracted to\n%s\n" % OUTPUT_DIR)
            self._logger.info("MCU logs compressed to\n%s" % OUTPUT_TAR)

    def _extract_one_dir(self, log_dir, include_previous):
        """Helper to extract MCU logs from 1 directory of servod logs.

        Args:
          log_dir: one directory that contains servod logs
          include_previous: whether to extract logs of previous deployments of servod

        Return a list of directories that contain extracted MCU logs.
        """
        log_groups = self._group_logs(log_dir, include_previous)
        combine_log_subdirs = self._combine_logs(log_dir, log_groups)
        for log_subdir in combine_log_subdirs:
            self._extract_mcu_logs(log_subdir)
        return combine_log_subdirs

    def _group_logs(self, log_dir, include_previous):
        """Group logs in the log_dir.

        Args:
          log_dir: one directory that contains servod logs
          include_previous: whether to extract logs of previous deployments of servod

        Return a dictionary whose key is the timestamp of the servod instance and
        value is a list of logs.
        """
        res = {}
        for logfile in os.listdir(log_dir):
            ts_match = TS_EXTRACTOR.match(logfile)
            if ts_match:
                timestamp = ts_match.group(TS_GROUP)
                if timestamp not in res:
                    res[timestamp] = []
                res[timestamp] += [logfile]
        if not res:
            self._logger.info("No log files found in directory %s" % log_dir)
            return res
        if not include_previous:
            latest_ts = sorted(res.keys())[-1]
            res = {latest_ts: res[latest_ts]}
        return res

    def _combine_logs(self, log_dir, log_groups):
        """Stick together rotated logs for each log level of a servod instance.

        Args:
          log_dir: one directory that contains servod logs
          log_groups: a dictionary whose key is the timestamp of the servod instance and
                      value is a list of logs

        Return a list of directories that contain combined logs.
        """
        res = []
        for timestamp, log_group in log_groups.items():
            output_subdir = OUTPUT_SUBDIR % (os.path.basename(log_dir), timestamp)
            os.makedirs(output_subdir)
            for log_level in LOG_LEVELS:
                logs = [log for log in log_group if log_level in log]
                if not logs:
                    continue

                # Need to sort. As they all share the same timestamp, and
                # loglevel, the index itself is sufficient. The highest index
                # is the oldest file, therefore we need a descending sort.
                def sortkey(log, level=log_level):
                    """Custom sortkey to sort based on rotation number int."""
                    return 0 if log.endswith(level) else int(log.split(".")[-1])

                logs.sort(reverse=True, key=sortkey)
                joint_log = os.path.join(output_subdir, OUTPUT_JOINT_LOG % log_level)
                with open(joint_log, "a+", encoding="utf-8") as joint_f:
                    for log in logs:
                        with open(
                            os.path.join(log_dir, log), "r", encoding="utf-8"
                        ) as log_f:
                            for line in log_f:
                                joint_f.write(line)
            res += [output_subdir]
        return res

    def _extract_mcu_logs(self, log_subdir):
        """Extract MCU (EC, Cr50, etc) console output from servod debug logs.

        Using the MCU_EXTRACTOR regex to extract and split out MCU console
        lines from the logs to generate individual console logs e.g. after
        this method, you can find an ec.txt and servo_v4.txt in |log_dir| if
        those MCUs had any console input/output.

        Args:
          log_subdir: directory with log.DEBUG.txt main servod debug logs.
        """
        # Extract the MCU for each one. The MCU logs are only in the .DEBUG files
        mcu_lines_file = os.path.join(log_subdir, OUTPUT_JOINT_DEBUG_LOG)
        if not os.path.exists(mcu_lines_file):
            self._logger.info(
                "No DEBUG logs in %s to extract MCU logs from." % log_subdir
            )
            return
        mcu_files = {}
        mcu_file_template = "%s.txt"
        with open(mcu_lines_file, "r", encoding="utf-8") as mcu_f:
            for line in mcu_f:
                match = MCU_EXTRACTOR.match(line)
                if match:
                    mcu = match.group(MCU_GROUP).lower()
                    line = match.group(LINE_GROUP)
                    if mcu not in mcu_files:
                        mcu_file = os.path.join(log_subdir, mcu_file_template % mcu)
                        mcu_files[mcu] = open(mcu_file, "a", encoding="utf-8")
                    file = mcu_files[mcu]
                    file.write(line + "\n")
        for file in mcu_files:
            mcu_files[file].close()

    def add_args(self, tool_parser):
        """Add the arguments needed for this tool."""
        subcommands = tool_parser.add_subparsers(dest="command")
        extract = subcommands.add_parser(
            "extract",
            help="Extract MCU logs from servod logs,"
            "bundle it to a tar file and return its location."
            "By default only extract the logs of the latest "
            "servod deployment",
        )
        extract_target = extract.add_mutually_exclusive_group(required=True)
        extract_target.add_argument(
            "-p",
            "--port",
            dest="port",
            type=int,
            nargs="+",
            help="port(s) where the servod instance is listening.",
        )
        extract_target.add_argument(
            "-d",
            "--directory",
            dest="directory",
            nargs="+",
            help="directory(s) that contains servod logs",
        )
        extract.add_argument(
            "--previous",
            action="store_true",
            help="extract logs of latest and previous deployments of servod",
        )


def _cleanup_output_dir():
    """Helper to clean up all old extracted log files."""
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)


def _make_tarfile(output, sources):
    """Helper that compresses all files in a directory into a tarfile."""
    with tarfile.open(output, "w:bz2") as tar:
        for source in sources:
            tar.add(source, arcname=os.path.basename(source))
