#!/usr/bin/env python3
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import sys

import run_command
from run_instead import RunInsteadBase


DUT_CONTROL_HELP_BASE = (
    run_command.HELP_MESSAGE_BASE
    + "\n"
    + """
[-p|--port PORT]
    Connect to the servod running on this port, either a local servod instance
    or a remote servod, via an ssh-forwarded port.
""".strip()
)


EXAMPLE_MSG = """
dut-control -- servo_type
    servo_type:ccd_cr50
""".strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "-p",
        "--port",
        type=str,
        help="Connect to the servod running on this port.",
        default=None,
    )
    return parser.parse_known_args()


class DutControlCommand(run_command.RunCommandBase):
    def __init__(self):
        super().__init__("dut-control", EXAMPLE_MSG, DUT_CONTROL_HELP_BASE)


class DutControlRunInsteadCommand(RunInsteadBase):
    """Runs dut-control in a standalone ephemeral container.

    Enables host networking so users can pass -p/--port to connect to servod
    on a remote host (for example via an SSH-forwarded port on localhost) or
    reach remote hosts directly using the host machine's network stack.
    """

    def __init__(self):
        super().__init__("dut-control")
        self.network_mode = "host"

    def add_custom_args(self, parser):
        parser.add_argument(
            "-p",
            "--port",
            type=str,
            help="Connect to the servod running on this port.",
            default=None,
        )

    def override_args(self, args, passthrough_args):
        if args.port is not None:
            passthrough_args.extend(["-p", str(args.port)])


if __name__ == "__main__":
    # When -p or --port is provided, the user may be connecting to servod on
    # a remote host (e.g. via an SSH-forwarded port on localhost or a remote
    # hostname). Use RunInsteadBase to launch a standalone container on demand
    # rather than requiring a local pre-existing 'docker_servod' container.
    main_args, _ = parse_args()
    if main_args.port is not None:
        command = DutControlRunInsteadCommand()
        sys.exit(command.run())
    else:
        command = DutControlCommand()
        command.run_command_in_container()
