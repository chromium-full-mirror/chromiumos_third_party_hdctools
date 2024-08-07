#!/usr/bin/env python3
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import sys

from run_instead import RunInsteadBase


class ServodtoolCommand(RunInsteadBase):
    def __init__(self):
        super().__init__("servodtool")


if __name__ == "__main__":
    servodtool = ServodtoolCommand()
    sys.exit(servodtool.run())
