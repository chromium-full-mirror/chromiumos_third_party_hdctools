#!/usr/bin/env python3
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import run_command


EXAMPLE_MSG = """
dut-control -- servo_type
    servo_type:ccd_cr50
""".strip()


class DutControlCommand(run_command.RunCommandBase):
    def __init__(self):
        super().__init__("dut-control", EXAMPLE_MSG)


if __name__ == "__main__":
    command = DutControlCommand()
    command.run_command_in_container()
