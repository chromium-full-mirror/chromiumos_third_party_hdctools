#!/usr/bin/env python3
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import run_command


class StopCommand(run_command.RunCommandBase):
    def execute_command(self, container, _):
        container.kill()


if __name__ == "__main__":
    command = StopCommand()
    command.run_command_in_container()
