#!/usr/bin/env python3
# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import run_command


EXAMPLE_MSG = """
dut-power -- -s example
    dut-power: error: No servod instance running for device with serialname: 'example'
""".strip()


class DutPowerCommand(run_command.RunCommandBase):
    def __init__(self):
        super().__init__("dut-power", EXAMPLE_MSG)


if __name__ == "__main__":
    command = DutPowerCommand()
    command.run_command_in_container()
