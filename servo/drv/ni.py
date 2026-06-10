# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""'Not Implemented' driver for controls that must be overridden by boards."""

from servo.drv import hw_driver


class ni(hw_driver.HwDriver):
    """Class to signal that a control is purposely not implemented.

    This is used as a safety default for controls that have dangerous default
    behaviors, forcing board overlays to explicitly define their own working
    implementation.
    """

    def __init__(self, core_addr, data_addr, interface, params):
        """Constructor.

        Args:
          core_addr: gRPC core address.
          data_addr: gRPC data address.
          interface: driver interface object.
          params: dictionary of params.
        """
        super().__init__(core_addr, data_addr, interface, params)
        self._message = self._params.get(
            "message",
            "Control %r is purposely not implemented." % self._params["control_name"],
        )

    def set(self, val):
        """Set method. Always raises an error."""
        raise hw_driver.HwDriverError(self._message)

    def get(self):
        """Get method. Always raises an error."""
        raise hw_driver.HwDriverError(self._message)
