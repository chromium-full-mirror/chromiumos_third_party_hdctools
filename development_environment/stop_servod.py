#!/usr/bin/env python3
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import run_command


class StopCommand(run_command.RunCommandBase):
    def __init__(self):
        super().__init__(None)

    def execute_command(self, container, command, detach=False):
        container.kill()
        return (0, None)


if __name__ == "__main__":
    stop_command = StopCommand()
    stop_command.run_command_in_container()
