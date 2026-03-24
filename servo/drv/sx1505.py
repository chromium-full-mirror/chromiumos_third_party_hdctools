# Copyright 2016 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for sx1505 8bit ioexpander."""
from servo.drv import hw_driver
from servo.drv import i2c_reg


class Sx1505Error(hw_driver.HwDriverError):
    """Error occurred accessing Sx1505."""


# We need a shared register cache between all the bits,
# as there is no readable state register.
# Indexing is: reg_cache[((interface, i2c addr), reg addr)] = value
reg_cache = {}


class sx1505(hw_driver.HwDriver):
    """Object to access drv=sx1505 controls."""

    # base indexes of the data, direction, pullup and pulldown registers
    # respectively.
    REG_DATA = 0
    REG_DIR = 1
    REG_PU = 2
    REG_PD = 3

    def _drv_init(self):
        """Driver specific initializer.

        Required params:
          child: integer, 7-bit i2c child address
          offset: integer, gpio's bit position from lsb
        """
        super()._drv_init()
        child = self._get_child()
        self._i2c_obj = i2c_reg.I2cReg.get_device(
            self._interface,
            child,
            addr_len=1,
            reg_len=1,
            msb_first=True,
            no_read=False,
            use_reg_cache=False,
        )
        try:
            # Remember what GPIOs we have set.
            global reg_cache
            self._reg_cache = reg_cache
            self._cacheindex = (self._interface, child)
            # Cache REG_DATA
            outputs = self._reg_cache.get((self._cacheindex, self.REG_DATA), 0xFF)
            self._reg_cache[(self._cacheindex, self.REG_DATA)] = outputs
            # Cache REG_DIR
            dir = self._reg_cache.get(
                (self._cacheindex, self.REG_DIR),
                self._i2c_obj._read_reg(self.REG_DIR, auto_release=False),
            )
            self._reg_cache[(self._cacheindex, self.REG_DIR)] = dir

            # Initialize pullup
            if self._io_type == "PU":
                (_, mask) = self._get_offset_mask()
                pu_reg = self._i2c_obj._read_reg(self.REG_PU, auto_release=False)
                pu_reg = pu_reg | mask
                self._i2c_obj._write_reg(self.REG_PU, pu_reg, auto_release=False)
        finally:
            self._i2c_obj.release()

    def _get(self):
        """Get gpio value.

        sx1505 has a data register REG_DATA. GPIO's current value
        can be read there.

        Returns:
          integer in formatted representation
        """
        value = self._i2c_obj._read_reg(self.REG_DATA)
        return self._create_logical_value(value)

    def _set(self, fmt_value):
        """Set value on ioexpander.

        1. Read cached value
        2. Mask accordingly
        3. Write value to Output register
        4. Read Direction reg cache (Note 0 == output, 1 == input)
           a. if input, Write Direction register
        5. Read Input register for returning

        Args:
          fmt_value: Integer value to write to hardware.  If None or empty string
            defaults to 0.

        Raises:
          Sx1505Error: If width of open drain driver is != 1 or open drain type is
            not recognized.
        """
        try:
            self._logger.debug("sx1505 set %s" % fmt_value)
            (_, mask) = self._get_offset_mask()
            if mask is None:
                raise Sx1505Error("Unable to determine mask.  Is offset declared?")

            change_to_input = False
            if self._io_type == "PU" and fmt_value == 1:
                self._logger.debug("Set to input because its io type is PU")
                change_to_input = True

            # output register handling
            if not change_to_input:
                hw_value = 0
                if fmt_value:
                    hw_value = self._create_hw_value(fmt_value)

                current_out_reg = self._reg_cache[(self._cacheindex, self.REG_DATA)]
                new_out_reg = hw_value | (current_out_reg & ~mask)
                if new_out_reg != current_out_reg:
                    self._reg_cache[(self._cacheindex, self.REG_DATA)] = new_out_reg
                    self._i2c_obj._write_reg(
                        self.REG_DATA, new_out_reg, auto_release=True
                    )

            current_dir_reg = self._reg_cache[(self._cacheindex, self.REG_DIR)]
            if change_to_input:
                new_dir_reg = current_dir_reg | mask
            else:
                new_dir_reg = current_dir_reg & ~mask

            if new_dir_reg != current_dir_reg:
                self._reg_cache[(self._cacheindex, self.REG_DIR)] = new_dir_reg
                self._i2c_obj._write_reg(self.REG_DIR, new_dir_reg, auto_release=True)
        finally:
            self._i2c_obj.release()

    def _get_child(self):
        """Check and return needed params to call driver.

        Returns:
          child: 7-bit i2c address
        """
        if "child" not in self._params:
            raise Sx1505Error("getting child address")
        child = int(self._params["child"], 0)
        return child
