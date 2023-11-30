# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""A drv to raise an error whenever set/get are used & those are undefined."""

from servo.drv import hw_driver


class undefinedCtrl(hw_driver.HwDriverError):
    """Specific error class (to allow logic to selectively catch these)."""


# pylint: disable=invalid-name
# naming convention needed for servod driver query.
class undefined(hw_driver.HwDriver):
    """class to raise set or get errors."""

    def _get(self):
        """raise error that |get| is undefined."""
        raise undefinedCtrl("get undefined for %r." % self._params["control_name"])

    def _set(self, _unused):
        """raise error that |set| is undefined."""
        raise undefinedCtrl("set undefined for %r." % self._params["control_name"])
