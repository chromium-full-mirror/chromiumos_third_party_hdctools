#!/usr/bin/env python3
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys

from run_instead import RunInsteadBase


class RunServoUpdater(RunInsteadBase):
    def __init__(self):
        super().__init__("/usr/local/bin/servo_updater")

    def add_custom_args(self, parser):
        parser.add_argument(
            "-f",
            "--file",
            type=str,
            help="Update servo with specific file.",
        )

    def override_args(self, args, passthrough_args):
        if args.file:
            dir_path = os.path.dirname(args.file)
            # new_file_path = f"/tmp/{os.path.basename(args.file)}"
            new_file_path = f"/tmp/{os.path.basename(args.file)}"

            # mount directory from host containing FW binary to container
            self.volumes.append(f"{dir_path}:/tmp/")

            # append new file path to command inside docker
            passthrough_args.append("-f")
            passthrough_args.append(new_file_path)


if __name__ == "__main__":
    updater = RunServoUpdater()
    sys.exit(updater.run())
