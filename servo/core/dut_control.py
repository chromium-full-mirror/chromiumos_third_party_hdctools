#!/usr/bin/env python3
# Copyright 2011 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Client to control DUT hardware connected to servo debug board."""

import collections
import logging
from socket import error as SocketError
import statistics
import sys
import time

from servo.common import servo_parsing
from servo.core import client


class ControlError(Exception):
    pass


# used to aid sorting of dict keys
KEY_PREFIX = "__"
STATS_PREFIX = "@@"
GNUPLOT_PREFIX = "##"
# dict key for tracking sampling time
TIME_KEY = KEY_PREFIX + "sample_msecs"


def _build_parser():
    """Build command line parser for dut_control.

    Returns:
      ServodClientParser with dut_control arguments
    """
    description = (
        "dut-control allows users to set and get various controls on a DUT system "
        "via the servo debug & control board. This client communicates to the "
        "board via a socket connection to the servo server."
    )
    examples = [
        ("--get-all", "gets value for all controls"),
        ("--verbose", "gets value for all controls verbosely"),
        (
            "i2c_mux",
            "gets value for i2c_mux control. If the exact control"
            " name is not found, a list of similar controls is printed",
        ),
        ("-r 100 i2c_mux", "gets value for i2c_mux control 100 times"),
        ("-t 2 loc_0x40_mv", "gets value for loc_0x40_mv control for 2 seconds"),
        (
            "-y -t 2 loc_0x40_mv",
            "gets value for loc_0x40_mv control for 2"
            " seconds and prepends time in seconds to results",
        ),
        (
            "-g -y -t 2 loc_0x40_mv loc_0x41_mv",
            "gets value for "
            "loc_0x4[0|1]_mv control for 2 seconds with gnuplot style",
        ),
        (
            "-z 100 -t 2 loc_0x40_mv",
            "gets value for loc_0x40_mv control for 2 seconds sampling every 100ms",
        ),
        ("--verbose i2c_mux", "gets value for i2c_mux control verbosely"),
        ("i2c_mux:remote_adcs", "sets i2c_mux to value remote_adcs"),
    ]
    parser = servo_parsing.ServodClientParser(
        description=description, examples=examples
    )
    # Add double-dashes in help message to unify docker and standalone versions
    parser.prog = parser.prog + " --"

    info_g = parser.add_mutually_exclusive_group()
    info_g.add_argument(
        "-i",
        "--info",
        help="show info about controls",
        action="store_true",
        default=False,
    )
    info_g.add_argument(
        "--hwinit",
        help="Initialize controls to their POR/safe state",
        action="store_true",
        default=False,
    )
    info_g.add_argument(
        "-o",
        "--value_only",
        help="show the value only",
        action="store_true",
        default=False,
    )

    info_g.add_argument(
        "--get-all",
        action="store_true",
        default=False,
        help="get all servod 'get' controls. Runs before any "
        "passed in args. WARNING: super slow, and alters state.",
    )

    print_g = parser.add_mutually_exclusive_group()
    print_g.add_argument(
        "-g",
        "--gnuplot",
        help="gnuplot style to stdout. Implies print_time",
        action="store_true",
        default=False,
    )
    print_g.add_argument(
        "--verbose",
        help="show verbose info about controls",
        action="store_true",
        default=False,
    )

    parser.add_argument(
        "-r",
        "--repeat",
        type=int,
        help="repeat requested command multiple times",
        default=1,
    )
    parser.add_argument(
        "-t",
        "--time_in_secs",
        help="repeat requested command for this many seconds",
        type=float,
        default=0.0,
    )
    parser.add_argument(
        "-y",
        "--print_time",
        help="print time in seconds with queries to stdout",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-z",
        "--sleep_msecs",
        type=float,
        default=0.0,
        help="sleep for this many milliseconds between queries",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="timeout in seconds for XML-RPC requests (default: 60.0)",
    )

    return parser


def display_table(table, prefix):
    """Display a two-dimensional array ( list-of-lists ) as a table.

    The table will be spaced out.
    >>> table = [['aaa', 'bbb'], ['1', '2222']]
    >>> display_table(table)
    @@   aaa   bbb
    @@     1  2222
    >>> display_table(table, prefix='%')
    %   aaa   bbb
    %     1  2222
    >>> table = [['a']]
    >>> display_table(table)
    @@   a
    >>> table = []
    >>> display_table(table)
    >>> table = [[]]
    >>> display_table(table)
    >>> table = [['a'], ['1', '2']]
    >>> display_table(table)
    Traceback (most recent call last):
    ...
    IndexError: list index out of range
    >>> table = [['a', 'b'], ['1']]
    >>> display_table(table)
    Traceback (most recent call last):
    ...
    IndexError: list index out of range
    >>> table = [['aaa', 'bbb', 'c'], ['1', '2222', '0']]
    >>> display_table(table)
    @@   aaa   bbb  c
    @@     1  2222  0

    Args:
      table: A two-dimensional array (list of lists) to show.
      prefix: All lines will be prefixed with this and a space.
    """
    if not table or not table[0]:
        return

    max_col_width = []
    for col_idx in range(len(table[0])):
        col_item_widths = [len(row[col_idx]) for row in table]
        max_col_width.append(max(col_item_widths))

    for row in table:
        out_str = ""
        for i in range(len(row)):
            out_str += row[i].rjust(max_col_width[i] + 2)
        print(prefix, out_str)


def display_stats(stats, prefix=STATS_PREFIX):
    """Display various statistics for data captured in a table.

    >>> stats = {}
    >>> stats[TIME_KEY] = [50.0, 25.0, 40.0, 10.0]
    >>> stats['frobnicate'] = [11.5, 9.0]
    >>> stats['foobar'] = [11111.0, 22222.0]
    >>> display_stats(stats)
    @@           NAME  COUNT   AVERAGE   STDDEV       MAX       MIN
    @@   sample_msecs      4     31.25    15.16     50.00     10.00
    @@         foobar      2  16666.50  5555.50  22222.00  11111.00
    @@     frobnicate      2     10.25     1.25     11.50      9.00

    Args:
      stats: A dictionary of stats to show.  Key is name of result and value is a
          list of floating point values to show stats for.  See doctest.
          Any key starting with '__' will be sorted first and have its prefix
          stripped.
      prefix: All lines will be prefixed with this and a space.
    """
    table = [["NAME", "COUNT", "AVERAGE", "STDDEV", "MAX", "MIN"]]
    for key in sorted(stats.keys()):
        if stats[key]:
            stats_list = stats[key]
            disp_key = key.lstrip(KEY_PREFIX)
            row = [disp_key, str(len(stats_list))]
            row.append("%.4f" % statistics.mean(stats_list))
            row.append("%.4f" % statistics.pstdev(stats_list))
            row.append("%.4f" % max(stats_list))
            row.append("%.4f" % min(stats_list))
            table.append(row)
    display_table(table, prefix)


def _print_gnuplot_header(control_args):
    """Prints gnuplot header.

    Args:
      control_args: list of controls to get or set

    Note, calls sys.exit()
    """
    hdr = []
    # Don't put setting of controls into gnuplot output
    hdr.extend(arg for arg in control_args if ":" not in arg)
    if not hdr:
        logging.critical(
            "Can't use --gnuplot without supplying controls to read on command line"
        )
        sys.exit(-1)
    print(GNUPLOT_PREFIX + " seconds " + " seconds ".join(hdr))


def _pretty_print_result(result):
    if isinstance(result, list):
        return ", ".join(result)
    if isinstance(result, dict):
        return "\n".join(["%s: %s" % (k, v) for k, v in result.items()])
    return result


def do_iteration(requests, options, sclient, stats):
    """Perform one iteration across the controls.

    Args:
      requests: list of strings to make requests to servo about
        Example = ['dev_mode', 'dev_mode:on', 'dev_mode']
      options: optparse object options
      sclient: ServoRequest object
      stats: dict of key=control name, value=control value for stats calcs

    Returns:
      out_str: results string from iteration based on formats in options
    """
    results = []
    out_list = []
    time_str = ""
    sample_start = time.time()

    if options.info:
        for request_str in requests:
            control = request_str
            if ":" in request_str:
                logging.warning(
                    "Ignoring %s, can't perform set with --info", request_str
                )
                continue
            results.append(sclient.doc(control))
    else:
        results = sclient.set_get_all(requests)

    if options.print_time:
        time_str = "%.4f " % (time.time() - _START_TIME)

    for i, result in enumerate(results):
        control = requests[i]
        if options.info:
            request_type = "doc"
        elif ":" in control:
            request_type = "set"
        else:
            request_type = "get"
            try:
                stats[control].append(float(result))
            except ValueError:
                pass
            except TypeError:
                pass

        result = _pretty_print_result(result)

        if options.verbose:
            out_list.append(
                "%s%s %s -> %s" % (time_str, request_type.upper(), control, result)
            )
        elif request_type != "set":
            if options.gnuplot:
                out_list.append("%s%s" % (time_str, result))
            else:
                if options.value_only:
                    out_list.append(str(result))
                else:
                    out_list.append("%s%s:%s" % (time_str, control, result))

    # format of gnuplot is <seconds_val1> <val1> <seconds_val2> <val2> ... such
    # that plotting can then be done with time on x-axis, value on y-axis.  For
    # example, this
    # command would plot two values across time
    #   plot   "file.out" using 1:2 with linespoint
    #   replot "file.out" using 3:4 with linespoint
    if options.gnuplot:
        out_str = " ".join(out_list)
    else:
        out_str = "\n".join(out_list)

    iter_time_msecs = (time.time() - sample_start) * 1000
    stats[TIME_KEY].append(iter_time_msecs)
    if options.sleep_msecs:
        if iter_time_msecs < options.sleep_msecs:
            time.sleep((options.sleep_msecs - iter_time_msecs) / 1000)
    return out_str


def iterate(controls, options, sclient):
    """Perform iterations on various controls.

    Args:
      controls: list of controls to iterate over
      options: optparse object options
      sclient: ServoRequest object
    """
    if options.gnuplot:
        options.print_time = True
        _print_gnuplot_header(controls)
    stats = collections.defaultdict(list)

    repeat = options.repeat
    time_in_secs = options.time_in_secs
    while (repeat >= 1) or (time_in_secs > 0):
        start_time = time.time()
        iter_output = do_iteration(controls, options, sclient, stats)
        if iter_output:  # Avoid printing empty lines
            print(iter_output)
        secs_so_far = time.time() - start_time
        repeat = repeat - 1
        time_in_secs = time_in_secs - secs_so_far

    if (options.repeat != 1) or (options.time_in_secs > 0):
        prefix = STATS_PREFIX
        if options.gnuplot:
            prefix = GNUPLOT_PREFIX
        display_stats(stats, prefix=prefix)


def real_main(cmdline):
    """actual main method logic."""
    parser = _build_parser()
    options, args = parser.parse_known_args(cmdline)
    loglevel = logging.INFO
    if options.debug:
        loglevel = logging.DEBUG
    logging.basicConfig(
        level=loglevel, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    sclient = client.ServoClient(
        host=options.host,
        port=options.port,
        verbose=options.verbose,
        timeout=options.timeout,
    )
    global _START_TIME
    _START_TIME = time.time()

    # Perform 1st in order to allow user to then override below
    if options.hwinit:
        sclient.hwinit()
    if options.get_all:
        print(sclient.get_all())

    if not args:
        if options.info:
            # print all the doc info for the controls
            print(sclient.doc_all())
        elif not (options.hwinit or options.get_all):
            # Just print the help message and exit. The condition checks for the
            # permissible options that can run without arguments, and where a help
            # message is not required.
            parser.print_help()
    else:
        iterate(args, options, sclient)


# Ability to pass an arbitrary or artificial cmdline for testing is desirable.
def main(cmdline=sys.argv[1:]):
    """main method exception wrapper."""
    try:
        if len(cmdline) > 0 and cmdline[0] == "--":
            cmdline = cmdline[1:]
        real_main(cmdline)
    except KeyboardInterrupt:
        sys.exit(0)
    except (client.ServoClientError, ControlError) as e:
        sys.stderr.write(str(e) + "\n")
        sys.exit(1)
    except SocketError as e:
        logging.debug("Caught SocketError: %r", e)
        err_msg = e.strerror if e.strerror is not None else str(e)
        sys.stderr.write(err_msg + "\n")
        sys.exit(1)


# global start time for script
_START_TIME = 0
if __name__ == "__main__":
    main()
