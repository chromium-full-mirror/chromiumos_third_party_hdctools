#!/usr/bin/env python3
# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import run_command


class DutPowerCommand(run_command.RunCommandBase):
    def __init__(self):
        super().__init__()
        self.message = """
    dut-power

    [-n CONTAINER_NAME]
        If you are running multiple servod containers use this to address a
        specific instance.

    --

        Everything after the -- is passed to the dut-power command in
        the container.

        Example:   dut-power -- servo_type
        servo_type:ccd_cr50

        Note the exit code for the wrapper script is set to be the exit code of the dut-power command.

        Run dut-power -- -h to get the specific help for dut-power
"""

    def execute_command(self, container, passthrough):
        return container.exec_run("dut-power " + (" ".join(passthrough)))


if __name__ == "__main__":
    command = DutPowerCommand()
    command.run_command_in_container()
