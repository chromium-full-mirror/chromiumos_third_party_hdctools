#!/usr/bin/env python3
# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
from datetime import datetime
import os

import docker


DEFAULT_IMAGE = "servod:dev"
ARTIFACT_URL_TEMPLATE = "us-docker.pkg.dev/chromeos-hw-tools/servod/servod:%s"


class RunInsteadBase:
    def __init__(self, command):
        self.client = docker.from_env()
        self.command = command

        now = datetime.now().strftime("%s")
        self.name = "{}-docker_{}".format(now, os.path.basename(command))

        self.volumes = ["/dev:/dev"]
        _servodrc = os.path.join(os.path.expanduser("~"), ".servodrc")
        if os.path.isfile(_servodrc):
            self.volumes.append(f"{_servodrc}:/root/.servodrc:ro")

    def get_image(self, channel):
        if channel != "local":
            image = ARTIFACT_URL_TEMPLATE % channel
            self.client.images.pull(image)
            return image
        return DEFAULT_IMAGE

    def parse_args(self):
        parser = argparse.ArgumentParser(add_help=True)
        parser.add_argument(
            "-c",
            type=str,
            choices=["local", "latest", "beta", "release"],
            default="release",
            dest="channel",
            help="Select docker image to use.",
        )

        if hasattr(self, "add_custom_args"):
            self.add_custom_args(parser)

        return parser.parse_known_args()

    def execute(self, image, passthrough_args):
        entrypoint = [self.command] + passthrough_args

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
        for line in output:
            print(line.decode("utf-8"), end="")
        result = cont.wait()
        ec = result["StatusCode"]
        cont.remove()
        return ec

    def run(self):
        args, passthrough_args = self.parse_args()

        if hasattr(self, "override_args"):
            self.override_args(args, passthrough_args)

        print("Getting docker image...")
        image = self.get_image(args.channel)
        print("Starting docker container...")
        res = self.execute(
            image=image,
            passthrough_args=passthrough_args,
        )

        return res
