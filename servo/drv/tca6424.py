# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for board config controls tca6424 tri port (24bit) ioexpander."""
from servo.drv import tca6416


class tca6424(tca6416.tca6416):
    """Object to access drv=tca6424 controls."""

    # base indexes of the input, output, polarity and direction registers
    # respectively.  Base is for port 0, +1 for port 1, and +2 for port 2.
    REG_INP = 0
    REG_OUT = 4
    REG_POL = 8
    REG_DIR = 12
    # Note(coconutruben): according to datasheet, we skip registers 3, 7, 11

    PORT_VALID_MASK = 0x11
    PORT_VALID_ERR_STR = "0 | 1 | 2"
