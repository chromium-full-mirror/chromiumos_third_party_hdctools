# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Access to Microchip PAC1954 GPIO expander functionality."""

import re

from servo.drv import bit_util
from servo.drv import hw_driver
from servo.drv import pac1934


class Pac1954GpioError(pac1934.Pac1934Error):
    """Pac1954Gpio error class."""


# pylint: disable=invalid-name
# servod drv identification follows this naming convention.
class pac1954Gpio(pac1934.pac1934):
    """Object to access drv=pac1954Gpio controls."""

    # io_mode: one of 'input', 'output', 'slow'
    # base_name: symbolic name of ADC control on system to anchor control to
    #            e.g. 'pp3300_wlan_dx'. This is used to read/write registers.
    #            NOTE: base_name map to a pac1954, otherwise the required
    #                  registers won't be available.
    REQUIRED_GET_PARAMS = ["io_mode", "pin", "base_name"]
    REQUIRED_SET_PARAMS = REQUIRED_GET_PARAMS

    def _drv_init(self):
        """Setup the drv and i2c reg."""
        # Note: we only inherit from pac1934 for register read/write
        # functionality. Do not initialize pac1934 but rather just hw_driver
        # as this drv does not deal with power, or rsense values.
        #
        # This could, and should, be fixed by moving the common register
        # read/write functionality into a separate library or
        # intermediate class.
        hw_driver.HwDriver._drv_init(self)
        # Need to retrieve the mode: i/o and which GPIO is in use (1,2)
        self._io_mode = self._params["io_mode"]
        self._pin = int(self._params["pin"])
        self._base_name = self._params["base_name"]
        # Assert the values are valid
        if self._io_mode not in ["input", "output", "slow"]:
            raise Pac1954GpioError("Unknown mode %r" % self._io_mode)
        if self._pin not in [1, 2]:
            raise Pac1954GpioError("Unknown pin %r" % self._pin)
        # Lastly, these things can only ever be set to 0 or 1. Enforce this.
        self._choices = re.compile("^(0|1)$")
        # Bit 8 and 9 are used for pin 1 cfg, 10 and 11 for pin 2 cfg
        self._cfg_offset = 8
        if self._pin == 2:
            self._cfg_offset += 2
        # Bit 6 is used for I/O for pin 1, bit 7 for I/0 for pin 2
        self._data_offset = 6 if self._pin == 1 else 7

    def _set_mode(self, mode):
        """Set the GPIO to |mode|."""
        cv = self._read_reg("ctrl")
        if mode == "input":
            cfg = 0x1
        elif mode == "output":
            cfg = 0x2
        else:
            # slow
            cfg = 0x3
        # zero out cvrent config
        rv = bit_util.set_bitfield(cv, 0x3, self._cfg_offset, cfg)
        self._write_reg("ctrl", rv)

    def _read_mode(self):
        """Read the currently programmed mode for the GPIO."""
        cv = self._read_reg("ctrl_act")
        mode = bit_util.extract_bitfield(cv, 0x3, self._cfg_offset)
        if mode == 0x0:
            return "alert"
        elif mode == 0x1:
            return "input"
        elif mode == 0x2:
            return "output"
        elif mode == 0x3:
            return "slow"
        else:
            raise Pac1954GpioError("Unknown GPIO mode 0x%02x" % v)

    def _write(self, value):
        """write |value| to the GPIO."""
        cv = self._read_reg("smbus", refresh=None)
        rv = bit_util.set_bitfield(cv, 0x1, self._data_offset, value)
        self._write_reg("smbus", rv)

    def _read(self):
        """read the value from the GPIO."""
        cv = self._read_reg("smbus", refresh=None)
        # Double cast rather than shifting or multiple checks.
        return int(bool(bit_util.extract_bitfield(cv, 0x1, self._data_offset)))

    def _enable_mode(self, mode=None):
        """Ensure that the programmed mode corresponds to |self._io_mode|."""
        if mode is None:
            mode = self._io_mode
        cm = self._read_mode()
        if cm != mode:
            self._logger.debug("mode is %r - changing it to %r", cm, mode)
            self._set_mode(mode)
        cm = self._read_mode()
        if cm != mode:
            raise Pac1954GpioError("Failed to set GPIO to %r mode" % mode)

    def _Set_gpio(self, value):
        """Set the |self._pin| to |value| if |self._io_mode| is 'output'."""
        if self._io_mode == "input":
            raise Pac1954GpioError("GPIO is configured as input. Cannot set.")
        # This ensures that if something changed the mode from underneath us,
        # we can configure it back to the expected |self._io_mode|
        self._enable_mode()
        self._write(value)

    def _Get_gpio(self):
        """Read the value from |self._pin| if |self._io_mode| is 'input'."""
        # This ensures that if something changed the mode from underneath us,
        # we can configure it back to the expected |self._io_mode|
        self._enable_mode()
        return self._read()

    def _Set_slow(self, value):
        """Turning on/off 'slow' capability."""
        # |value| being high means we want slow mode enabled. Otherwise, we do not
        # want slow mode at all. Set the pin to 'input' to implicitly disable slow
        mode = "slow" if value else "input"
        self._enable_mode(mode)

    def _Get_slow(self):
        """Whether slow mode on the pin is possible."""
        return int(self._read_mode() == "slow")
