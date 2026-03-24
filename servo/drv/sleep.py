# Copyright 2014 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for sleep delay pseudo-control."""
import time

from servo.drv import hw_driver


class sleep(hw_driver.HwDriver):
    """Simple HwDriver wrapper around time.sleep()."""

    def _drv_init(self):
        """Driver specific initializer."""
        super()._drv_init()

    def _set(self, seconds):
        """Sleep for the given number of seconds."""
        time.sleep(seconds)
