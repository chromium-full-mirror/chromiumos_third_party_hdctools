# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Common code for servo parsing support."""

import argparse
import logging
import os
import textwrap


DEFAULT_PORT = 9999


class ServodParserHelpFormatter(
    argparse.RawDescriptionHelpFormatter, argparse.ArgumentDefaultsHelpFormatter
):
    """Servod help formatter.

    Combines ability for raw description printing (needed to have control over
    how to print examples) and default argument printing, printing the default
    which each argument.
    """


class _BaseServodParser(argparse.ArgumentParser):
    """Extension to ArgumentParser that allows for examples in the description.

    _BaseServodParser allows for a list of example tuples, where
      element[0]: is the cmdline invocation
      element[1]: is a comment to explain what the invocation does.

    For example (loosely based on servod.)
    ('-b board', 'Start servod with the configuration for board |board|')
    would print the following help message:
    ...

    Examples:
      > servod -b board
          Start servod with the configuration for board |board|

    Optional Arguments...

    see servod, or dut_control for more examples.
    """

    def __init__(self, description="", examples=None, **kwargs):
        """Initialize _BaseServodParser by setting description and formatter.

        Args:
          description: description of the program
          examples: list of tuples where the first element is the cmdline example,
                    and the second element is a comment explaining the example.
                    %(prog)s will be prepended to each example if it does not
                    start with %(prog)s.
          **kwargs: keyword arguments forwarded to ArgumentParser
        """
        # Logging is setup in servod.py ServodStarter:__init__
        self._logger = logging.getLogger(type(self).__name__)
        # Generate description.
        description_lines = textwrap.wrap(description)
        # Setting it into the kwargs here ensures that we overwrite an potentially
        # passed in and undesired formatter class.
        kwargs["formatter_class"] = ServodParserHelpFormatter
        if examples:
            # Extra newline to separate description from examples.
            description_lines.append("\n")
            description_lines.append("Examples:")
            for example, comment in examples:
                if not example.startswith("%(prog)s"):
                    example = "%%(prog)s " + example
                example_lines = ["  > " + example]
                example_lines.extend(textwrap.wrap(comment))
                description_lines.append("\n\t".join(example_lines))
        description = "\n".join(description_lines)
        kwargs["description"] = description
        super().__init__(**kwargs)


class BaseServodParser(_BaseServodParser):
    """BaseServodParser handling common arguments in the servod cmdline tools."""

    def __init__(self, add_port=True, **kwargs):
        """Initialize by adding common arguments.

        Adds:
        - host/port arguments to find/initialize a servod instance
        - debug argument to toggle debug message printing

        Args:
          add_port: bool, whether to add --port to the parser. A caller might want
                    to add port themselves either to rename it (servod-port),
                    or to create mutual exclusion with serialname and name (clients)
          **kwargs: keyword arguments forwarded to _BaseServodParser
        """
        super().__init__(**kwargs)
        self.add_argument(
            "-d",
            "--debug",
            action="store_true",
            default=False,
            help="enable debug messages",
        )
        self.add_argument(
            "--host",
            default="localhost",
            type=str,
            help="hostname of the servod server.",
        )
        if add_port:
            BaseServodParser.add_rc_enabled_port_arg(self)

    @staticmethod
    def add_rc_enabled_port_arg(parser, port_flags=None):
        """Add the port to the argparser.

        Set the default to environment variable ENV_PORT_NAME if defined

        Note: while this helper does allow for arbitrary flags for the port
        variable, the destination is still set to 'port'. It's on the caller to
        ensure that there is no conflict.

        Args:
          parser: parser or group to add argument to
          port_flags: optional, list, if the flags for the port should be different
                      than the default ones.
        """
        if port_flags is None:
            port_flags = ["-p", "--port"]
        default = os.environ.get("SERVOD_PORT", DEFAULT_PORT)
        parser.add_argument(
            *port_flags,
            default=default,
            type=int,
            dest="port",
            help="port of the servod server. Can also be supplied "
            "through environment variable SERVOD_PORT",
        )


class ServodClientParser(BaseServodParser):
    """Parser to use for servod client cmdline tools."""

    def __init__(self, **kwargs):
        """Create a BaseServodParser that has the BaseServodParser args."""
        super().__init__(**kwargs)
