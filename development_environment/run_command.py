#!/usr/bin/env python3
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import sys
import threading
import time
import types

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


def output_logs(output):
    if output:
        # We need to check for both types due to a change in the API
        # at version 6.1.0 of the python docker API.
        # Remove the extra check for GeneratorType when we are sure
        # that no-one is using older versions and we put a min version
        # check in.
        if isinstance(
            output, (docker.types.daemon.CancellableStream, types.GeneratorType)
        ):
            # Setting the tty parameter to True causes the output to
            # contain CRLF line endings instead of LF. This can cause
            # problems when using output of this command in shell
            # scripts or as input to other commands. Stripping lines
            # caused empty lines to be printed periodically, so the
            # replace *SHOULD* work correctly. We have no guarantee that
            # the CR and LF won't be split between different calls.
            for line in output:
                print(line.decode("utf-8").replace("\r\n", "\n"), flush=True, end="")
                time.sleep(0.1)
        else:
            print(output.decode("utf-8"), flush=True, end="")


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
            sys.exit(5)
        elif len(containers) == 1:
            output_thread = None
            try:
                unused_exit, output = self.execute_base_command(
                    containers[0],
                    args.passthrough[1:],
                )
                output_thread = threading.Thread(target=output_logs, args=(output,))
                output_thread.daemon = True
                output_thread.start()
                process_running = 1
                while process_running > 0 and self.command:
                    unused_exit, output = self.execute_command(
                        containers[0],
                        [
                            "bash",
                            "-c",
                            f"ps aux | grep -v grep | grep {self.command} | wc -l",
                        ],
                    )
                    time.sleep(0.1)
                    process_running = int(list(output)[0])

            except (KeyboardInterrupt, SystemExit):
                print("Interrupt", flush=True)

                unused_exit, output = self.execute_command(
                    containers[0],
                    [
                        "bash",
                        "-c",
                        (
                            f"kill -s SIGINT "
                            f"$(ps aux | grep {self.command} | grep -v grep | "
                            f"awk -F ' ' '{{print $2}}')"
                        ),
                    ],
                )
            finally:
                time.sleep(0.1)
                if output_thread:
                    output_thread.join(timeout=1)
                output_thread = None

        else:
            print(
                (
                    "More than one container matches %s, "
                    "please re-run with --container_name"
                )
                % name_search,
                file=sys.stderr,
            )

    def execute_base_command(self, container, passthrough, detach=False):
        cmd = [self.command] + passthrough
        return self.execute_command(container, cmd, detach)

    def execute_command(self, container, command, detach=False):
        return container.exec_run(command, stream=True, detach=detach, tty=True)
