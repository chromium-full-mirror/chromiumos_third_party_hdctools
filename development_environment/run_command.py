#!/usr/bin/env python3
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import sys

import docker


class RunCommandBase:
    def parse_args(self):
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument(
            "-n",
            "--container_name",
            type=str,
            help="The IP or hostname of the DUT connected to servo.",
        )
        parser.add_argument(
            "passthrough", nargs=argparse.REMAINDER, help="Arguments for subcommand"
        )
        return parser.parse_args()

    def run_command_in_container(self):
        args = self.parse_args()
        client = docker.from_env()

        name_search = "docker_servod"
        if args.container_name:
            name_search = "%s-%s" % (args.container_name, name_search)

        containers = client.containers.list(filters={"name": name_search})
        if not containers:
            print("Can not find a container that matches name %s" % name_search)
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
                % name_search
            )

    def execute_command(self, container, passthrough):
        raise NotImplementedError
