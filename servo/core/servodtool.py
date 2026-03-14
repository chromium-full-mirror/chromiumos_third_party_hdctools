# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Servodtool manager."""

import argparse
import logging
import sys

from servo import tools


class ServodToolError(Exception):
    """Servodtool error class."""


def setup_logging(debug=False):
    """Setup logging for the command line tool."""
    root_logger = logging.getLogger()
    stdout_handler = logging.StreamHandler(sys.stdout)
    level = logging.DEBUG if debug else logging.INFO
    stdout_handler.setLevel(level)
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(stdout_handler)


# TODO(coconutruben): phase this out. For now, users are still expecting this
# tool, and some autotest code might still rely on this. Once all the
# dependencies are eliminated for servodtool, then remove this.
def servodutil(cmdline=sys.argv[1:]):
    """Legacy, to keep the old command-line tool in place."""
    setup_logging()
    parser = argparse.ArgumentParser()
    instance_tool = tools.instance.Instance()
    instance_tool.add_args(parser)
    args = parser.parse_args(cmdline)
    instance_tool.run(args)


# pylint: disable=dangerous-default-value
def main(cmdline=sys.argv[1:]):
    """Entry function for cmdline servodtool utility."""
    if len(cmdline) > 0 and cmdline[0] == "--":
        cmdline = cmdline[1:]
    # pylint: disable=protected-access
    parser = argparse.ArgumentParser()
    # Add double-dashes in help message to unify docker and standalone versions
    parser.prog = parser.prog + " --"

    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        default=False,
        help="enable debug messages",
    )
    subparsers = parser.add_subparsers(dest="tool")
    # Make a dictionary of tool names and the actual tool.
    tool_dict = {}
    for tool_cls in tools.REGISTERED_TOOLS:
        t = tool_cls()
        tool_dict[t.name] = t
    for tname in tool_dict:
        t = tool_dict[tname]
        tparser = subparsers.add_parser(tname, help=t.help)
        tool_dict[tname].add_args(tparser)
    try:
        args = parser.parse_args(cmdline)
        setup_logging(args.debug)
        tool_dict[args.tool].run(args)
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        if args.debug:
            raise
        print("Error: %s" % e)
        sys.exit(1)


if __name__ == "__main__":
    main()
