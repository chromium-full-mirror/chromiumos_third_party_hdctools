#!/usr/bin/env python3
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import sys

import docker


HELP_MESSAGE_BASE = """
{0}

[-n|--container_name CONTAINER_NAME]
    If you are running multiple servod containers use this to address a
    specific instance.
""".strip()

HELP_MESSAGE_ADV = """
--

Everything after the -- is passed to the {0} command in
the container.

Example: {1}

Note the exit code for the wrapper script is set to be the exit code of the {0} command.

Run {0} -- -h to get the specific help for {0}
""".strip()


class CustomArgHelpParser(argparse.ArgumentParser):
    def __init__(self, message):
        super().__init__(add_help=False)
        self.message = message

        self.add_argument(
            "-h",
            "--help",
            action=argparse.BooleanOptionalAction,
        )

    def print_usage(self, file=None):
        print(self.message, file=file)


class RunCommandBase:
    def __init__(self, command, example_msg=None):
        self.command = command
        self.message = HELP_MESSAGE_BASE.format(command)
        if example_msg is not None:
            self.message = self.message + HELP_MESSAGE_ADV.format(command, example_msg)

    def parse_args(self):
        self.parser = CustomArgHelpParser(self.message)
        self.parser.add_argument(
            "-n",
            "--container_name",
            type=str,
        )
        self.parser.add_argument(
            "passthrough",
            nargs=argparse.REMAINDER,
        )
        args = self.parser.parse_args()
        if args.help:
            self.parser.print_usage()
            sys.exit(4)
        if args.passthrough and args.passthrough[0] != "--":
            print(
                (
                    "Error - unknown arguments '%s' - if you want to pass through"
                    " arguments use the -- separator"
                )
                % " ".join(args.passthrough),
                file=sys.stderr,
            )
            sys.exit(3)
        return args

    def run_command_in_container(self):
        args = self.parse_args()
        client = docker.from_env()

        name_search = "docker_servod"
        if args.container_name:
            name_search = "%s-%s" % (args.container_name, name_search)

        containers = client.containers.list(filters={"name": name_search})
        if not containers:
            print(
                "Can not find a container that matches name %s" % name_search,
                file=sys.stderr,
            )
        elif len(containers) == 1:
            exit_code, output = self.execute_command(
                containers[0], args.passthrough[1:]
            )
            if output:
                print(output.decode("utf-8"), end="")
            sys.exit(exit_code)
        else:
            print(
                (
                    "More than one container matches %s, "
                    "please re-run with --container_name"
                )
                % name_search,
                file=sys.stderr,
            )

    def execute_command(self, container, passthrough):
        cmd = [self.command] + passthrough
        return container.exec_run(cmd)
