# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""i2c register module drv to read/write register directly."""
import errno
import time

from servo.common.interface.stm32i2c import Si2cError
from servo.drv import hw_driver
from servo.drv import i2c_reg
from servo.drv import undefined


TIMEOUT_RETRIES = 10


class i2cRegDrv(hw_driver.HwDriver):
    """Provides methods for devices with registered indexing over i2c."""

    # len: the length of the register in bytes
    # addr: the i2c child address
    # offset: the i2c offset of the register to read
    REQUIRED_GET_PARAMS = ["reg_len", "addr", "offset"]
    REQUIRED_SET_PARAMS = REQUIRED_GET_PARAMS

    def _drv_init(self):
        """Driver specific initializer.

        Required params:
            See REQUIRED_GET_PARAMS and REQUIRED_SET_PARAMS above.

        Optional params:
            msb_last: if this param is present, we assume that most
                      significant byte comes last. Default is False
            no_read: if this param is present, we will not read after
                     writing to the register. Default is False
            read_only: when a register cannot be written to. This will then
                       cause an error to be thrown when a write is attempted.
                       Default is False
            write_only: when a register cannot be read from. This will then
                        cause an error to be thrown when a read is attempted.
                        Default is False
        """
        super()._drv_init()
        msb_first = "msb_last" not in self._params
        self._no_read = "no_read" in self._params
        self._read_only = "read_only" in self._params
        self._write_only = "write_only" in self._params
        self._offset = int(self._params["offset"])
        self._reg_len = int(self._params["reg_len"])
        self._dev = i2c_reg.I2cReg.get_device(
            self._interface,
            addr_len=1,
            child=int(self._params["addr"], 0),
            reg_len=self._reg_len,
            msb_first=msb_first,
            no_read=self._no_read,
            use_reg_cache=False,
        )

    def _set(self, value):
        """Write |value| to |self._offset| on |self._dev|.

        Args:
          value: int, value to write to register

        Raises:
          HwDriverError: if |self._read_only| is True
        """
        if self._read_only:
            undefined.undefined.set(self, None)
        # Set potential overwrites from default.
        # pylint: disable=protected-access
        # _dev object is used to share object across multiple registers
        self._dev._write_reg(
            self._offset, value, reg_len=self._reg_len, no_read=self._no_read
        )

    def _get(self):
        """ "Read out the value from |self._offset| register on |self._dev|.

        Returns:
          output of read_reg of the i2c object

        Raises:
          HwDriverError: if |self._write_only| is True
        """
        if self._write_only:
            undefined.undefined.get(self)
        last_exception = None
        for i in range(0, TIMEOUT_RETRIES):
            if i > 0:
                sleep_ms = i**2
                self._logger.warning("Read timed out, trying again in %d ms", sleep_ms)
                time.sleep(sleep_ms / 1000.0)

            try:
                # pylint: disable=protected-access
                # _dev object is used to share object across multiple registers
                return self._dev._read_reg(self._offset, reg_len=self._reg_len)
            except IOError as e:
                if e.errno == errno.ETIMEDOUT:
                    last_exception = e
                else:
                    raise
            except Si2cError as e:
                last_exception = e

        if last_exception:
            raise last_exception
