#!/usr/bin/env python3
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import run_command


class DutControlCommand(run_command.RunCommandBase):
    def execute_command(self, container, unknown_args):
        (exit_code, output) = container.exec_run(
            "dut-control " + (" ".join(unknown_args))
        )
        print("dut-control exited with code %d\n\nOutput:\n" % exit_code)
        print(output.decode("utf-8"))


if __name__ == "__main__":
    command = DutControlCommand()
    command.run_command_in_container()
