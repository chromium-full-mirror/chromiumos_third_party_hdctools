#!/usr/bin/env python3
# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import sys

from run_instead import RunInsteadBase


class ServoUpdaterCommand(RunInsteadBase):
    def __init__(self):
        super().__init__("servo_updater")


if __name__ == "__main__":
    servo_updater = ServoUpdaterCommand()
    sys.exit(servo_updater.run())
