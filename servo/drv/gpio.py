# Copyright 2011 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for board config controls of type=gpio."""
import logging

from servo.drv import hw_driver


class gpioError(hw_driver.HwDriverError):
    """Error class for gpio class."""


class gpio(hw_driver.HwDriver):
    """Object to access type=gpio controls.

    Required params:
      offset: integer, shift amount (left) to align GPIO bit correctly

    Optional params:
      chip: Beaglebone gpio chip id.
      width: integer, number of contiguous bits in GPIO control
    """

    def _drv_init(self):
        """Driver specific initializer."""
        super()._drv_init()
        # TODO (sbasi/tbroch) crbug.com/241507 - Deprecate chip & muxfile params.
        self._chip = self._params.get("chip", None)
        self._muxfile = self._params.get("muxfile", None)

    def _get(self):
        """Get value for gpio driver

        Returns:
          integer value from gpio

        Raises:
          gpioError: if no offset in param dict
        """

        (offset, width) = self._get_common_params()

        if hasattr(self._interface, "gpio_wr_rd"):
            return self._interface.gpio_wr_rd(offset, width)
        else:
            return self._interface.wr_rd(
                offset, width, chip=self._chip, muxfile=self._muxfile
            )

    def _set(self, value):
        """Set value for gpio driver

        Args:
          value: integer value to write to gpio

        Raises:
          gpioError: if no offset in param dict
        """

        (offset, width) = self._get_common_params()

        is_output = 1
        if self._io_type == "PU":
            if value == 1:
                is_output = 0

        if hasattr(self._interface, "gpio_wr_rd"):
            self._interface.gpio_wr_rd(offset, width, is_output, value)
        else:
            self._interface.wr_rd(
                offset, width, is_output, value, chip=self._chip, muxfile=self._muxfile
            )

    def _get_common_params(self):
        """Get common parameters for gpio control

        Returns:
          tuple (offset, width) where
            offset: integer, left shift amount for location of gpio
            width: integer, bit width of gpio

        Raises:
          gpioError: if integer conversion of offset or width fail
        """

        if "offset" not in self._params:
            raise gpioError("No offset in params for gpio")
        try:
            offset = int(self._params["offset"])
        except ValueError as error:
            raise gpioError(error)

        width_str = self._params.get("width", "1")
        try:
            width = int(width_str)
        except ValueError as error:
            raise gpioError(error)
        return (offset, width)
