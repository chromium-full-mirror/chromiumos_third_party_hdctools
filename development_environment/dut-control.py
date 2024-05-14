#!/usr/bin/env python3
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import run_command


class DutControlCommand(run_command.RunCommandBase):
    def __init__(self):
        super().__init__()
        self.message = """
    dut-control

    [-n CONTAINER_NAME]
        If you are running multiple servod containers use this to address a
        specific instance.

    --

        Everything after the -- is passed to the dut-control command in
        the container.

        Example:   dut-control -- servo_type
        servo_type:ccd_cr50

        Note the exit code for the wrapper script is set to be the exit code of the dut-control command.

        Run dut-control -- -h to get the specific help for dut-control
"""

    def execute_command(self, container, passthrough):
        cmd = ["dut-control"] + passthrough
        return container.exec_run(cmd)


if __name__ == "__main__":
    command = DutControlCommand()
    command.run_command_in_container()
