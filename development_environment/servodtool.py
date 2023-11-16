#!/usr/bin/env python3
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import run_command


class ServodtoolCommand(run_command.RunCommandBase):
    def __init__(self):
        super().__init__()
        self.message = """
servodtool

    [-n CONTAINER_NAME]
        If you are running multiple servod containers use this to address a
        specific instance.

    --
        Everything after the -- is passed to the servodtool command in
        the container.

Example:   servodtool -- instance
servo_type:ccd_cr50

Note the exit code for the wrapper script is set to be the exit code of the dut-control command.

Run servodtool -- -h to get the specific help for servodtool
"""

    def execute_command(self, container, passthrough):
        return container.exec_run("servodtool " + (" ".join(passthrough)))


if __name__ == "__main__":
    command = ServodtoolCommand()
    command.run_command_in_container()
