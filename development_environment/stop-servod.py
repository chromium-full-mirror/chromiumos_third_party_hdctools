#!/usr/bin/env python3
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import run_command


class StopCommand(run_command.RunCommandBase):
    def __init__(self):
        super().__init__()
        self.allow_no_args = True
        self.message = """
stop-servod

    [-n CONTAINER_NAME]
        If you are running multiple servod containers use this to address a
        specific instance.
"""

    def execute_command(self, container, passthrough):
        container.kill()
        return (0, None)


if __name__ == "__main__":
    command = StopCommand()
    command.run_command_in_container()
