#!/usr/bin/env python3
# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys

from run_instead import RunInsteadBase


class ServoUpdaterCommand(RunInsteadBase):
    def __init__(self):
        super().__init__("servo_updater")

    def add_custom_args(self, parser):
        parser.add_argument(
            "-f",
            "--file",
            type=str,
            help="Path to local firmware binary file on the host.",
            default=None,
        )

    def override_args(self, args, passthrough_args):
        if args.file:
            if not os.path.isabs(args.file) and "HOST_PWD" in os.environ:
                abs_file = os.path.abspath(
                    os.path.join(os.environ["HOST_PWD"], args.file)
                )
            else:
                abs_file = os.path.abspath(args.file)
            dir_path = os.path.dirname(abs_file)
            base_name = os.path.basename(abs_file)

            container_dir = "/tmp/servo_updater"
            container_file = os.path.join(container_dir, base_name)

            self.volumes.append(f"{dir_path}:{container_dir}:ro")
            passthrough_args.extend(["-f", container_file])


if __name__ == "__main__":
    servo_updater = ServoUpdaterCommand()
    sys.exit(servo_updater.run())
