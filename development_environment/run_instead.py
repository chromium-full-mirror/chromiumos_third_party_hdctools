#!/usr/bin/env python3
# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
from datetime import datetime
import os
import sys

import docker


DEFAULT_IMAGE = "servod:dev"
ARTIFACT_URL_TEMPLATE = "us-docker.pkg.dev/chromeos-hw-tools/servod/servod:%s"

HELP_DESCRIPTION = """  --
    Everything after the -- is passed to the %(prog)s command in the container.

    Note the exit code for the wrapper script is set to be the exit code of the %(prog)s command.

    Run %(prog)s -- -h to get the specific help for %(prog)s"""


class RunInsteadBase:
    def __init__(self, command):
        self.client = docker.from_env()
        self.command = command

        now = datetime.now().strftime("%s")
        self.name = "{}-docker_{}".format(now, os.path.basename(command))

        self.volumes = ["/dev:/dev"]
        # This variable is set by bootstrap script. If bootstrap is no more,
        # revert commit done for b:400921593
        _servodrc = os.environ["SERVODRC"] if "SERVODRC" in os.environ else ""
        if len(_servodrc) > 0:
            self.volumes.append(f"{_servodrc}:/root/.servodrc:ro")

    def get_image(self, channel):
        if channel != "local":
            image = ARTIFACT_URL_TEMPLATE % channel
            try:
                self.client.images.pull(image)
            except (docker.errors.APIError, docker.errors.DockerException) as e:
                if self.client.images.list(filters={"reference": image}):
                    print("Warning: Failed to pull newest image, using local version.")
                    return image

                if isinstance(e, docker.errors.APIError) and (
                    e.is_server_error()
                    and e.response is not None
                    and str(e.response.content).find("unauthorized") > 0
                ):
                    print(
                        "!!!\nUnexpected authentication failure. Please try running: \n"
                        "\ngcloud auth login\n\n"
                        "Refresh the credentials and try again.\n"
                        "More reading: https://chromium.googlesource.com/chromiumos/"
                        "third_party/hdctools/+/main/docs/servod_outside_chroot.md#"
                        "start_servod"
                        "-sent-me-here-after-authenticating-with-the-registry-failed"
                    )
                    sys.exit(1)
                raise
            return image
        return DEFAULT_IMAGE

    def parse_args(self):
        parser = argparse.ArgumentParser(
            add_help=True,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=HELP_DESCRIPTION,
        )

        parser.add_argument(
            "-c",
            "--updater_channel",
            type=str,
            choices=["local", "latest", "beta", "release"],
            default="release",
            dest="channel",
            help="Select docker image to use.",
        )

        parser.add_argument(
            "-n",
            "--name",
            help="Name of existing container if command should attach to it",
            default=None,
        )

        if hasattr(self, "add_custom_args"):
            self.add_custom_args(parser)

        return parser.parse_known_args()

    def execute(self, image, passthrough_args, container_name):
        entrypoint = [self.command] + passthrough_args
        exit_code = 0

        if container_name is not None:
            containers = self.client.containers.list(filters={"name": container_name})
            if not containers or len(containers) > 1:
                print(
                    "Can not find a container that matches name %s" % container_name,
                    file=sys.stderr,
                )
                sys.exit(1)
            cont = containers[0]
            exit_code, output = cont.exec_run(entrypoint, stream=True, tty=True)
        else:
            cont = self.client.containers.run(
                image,
                privileged=True,
                stderr=True,
                tty=True,
                name=self.name,
                hostname=self.name,
                detach=True,
                volumes=self.volumes,
                entrypoint=entrypoint,
            )
            output = cont.attach(stdout=True, stderr=True, stream=True, logs=True)

        # Setting the tty parameter to True causes the output to
        # contain CRLF line endings instead of LF. This can cause
        # problems when using output of this command in shell
        # scripts or as input to other commands. Stripping lines
        # caused empty lines to be printed periodically, so the
        # replace *SHOULD* work correctly. We have no guarantee that
        # the CR and LF won't be split between different calls.
        for line in output:
            print(line.decode("utf-8").replace("\r\n", "\n"), end="")

        if container_name is None:
            result = cont.wait()
            ec = result["StatusCode"]
            cont.remove()
            return ec
        return exit_code

    def run(self):
        args, passthrough_args = self.parse_args()

        if passthrough_args and passthrough_args[0] != "--":
            print(
                (
                    "Error - unknown arguments '%s' - if you want to pass through"
                    " arguments use the -- separator"
                )
                % " ".join(passthrough_args),
                file=sys.stderr,
            )
            sys.exit(3)

        # Remove --
        if passthrough_args:
            passthrough_args.pop(0)
        if hasattr(self, "override_args"):
            self.override_args(args, passthrough_args)

        print("Getting docker image...")
        image = self.get_image(args.channel)
        print("Starting docker container...")
        res = self.execute(
            image=image, passthrough_args=passthrough_args, container_name=args.name
        )

        return res
