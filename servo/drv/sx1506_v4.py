# Copyright 2016 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for sx1506 16bit ioexpander, with power on defaults for for servo v4"""
from servo.drv import sx1506


class sx1506V4(sx1506.sx1506):
    """Object to access drv=sx1506_v4 controls.

    This class implements hardcoded defaults for servo v4's sx1506 io expander.
    Since sx1506 doesn't export its internal state, and the GPIOs must be
    preserved on init to keep servo_micro up, we need to hardcode here.
    """

    INIT_DATA = 0x0282
    INIT_DIR = 0x0000
