# Copyright 2012 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Access to NXP's PCA9500.

8-bit I2C-bus and SMBus I/O port with 2-kbit EEPROM.

Accessed via controls with params of,
  1. type=pca9500 subtype=gpio offset='<num>'
  2. type=pca9500 subtype=eeprom

GPIO:
- Functions as an open-drain style GPIO's
  - Writing a '1' to the control register effectively makes the device an input
    with a pull-up.
  - Writing a '0' to the control register makes it a true output.
  - Reading the control register returns the current value of the pin.

EEPROM:
  writes:
   - page write: child wr + byte addr byte + 1-4 bytes to write
  reads:
   - byte N read: child wr + byte addr byte to set addr
                  child rd + read N bytes

  Note, EEPROM has an active low write control (WC#) which must be
  asserted to write the device.
"""
import logging

from servo.drv import hw_driver


REG_CTRL_LEN = 1
EEPROM_BYTES = 256
PAGE_BYTES = 4


class pca9500Error(hw_driver.HwDriverError):
    """Error class for pca9500 class."""


class pca9500(hw_driver.HwDriver):
    """Object to access type=pca9500 controls."""

    _byte_addr = 0

    def _drv_init(self):
        """Driver specific initializer.

        Required params:
          child: integer, 7-bit i2c child address

        Optional params:
          offset: integer, left shift amount for location of gpio
          width: integer, bit width of gpio

        Attributes:
          _child: integer value of the 7-bit i2c child address.
        """
        super()._drv_init()
        if "child" not in self._params:
            raise pca9500Error("getting child address")
        self._child = int(self._params["child"], 0)

    def _Set_gpio(self, value):
        """Set pca9500 GPIO to value.

        The pca9500 GPIO expander has a single control register (not typical
        direction and value register).  The driver must take care to maintain
        previous state of all bits.

        Args:
          value: integer value to write to gpio
        """
        try:
            self._logger.debug("value = %d", value)
            (_, mask) = self._get_offset_mask()
            cur_value = self._read_control_reg(auto_release=False)
            if value:
                hw_value = cur_value | mask
            else:
                hw_value = cur_value & ~mask
            self._logger.debug(
                "new(0x%02x) cur(0x%02x) mask(0x%02x)", hw_value, cur_value, mask
            )
            self._interface.wr_rd(self._child, [hw_value], 0, auto_release=False)
        finally:
            self._interface.release()

    def _Get_gpio(self):
        """Get pca9500 GPIO value and return.

        Returns:
          integer value from gpio
        """

        return self._create_logical_value(self._read_control_reg())

    def _read_control_reg(self, auto_release=True):
        """Read the pca9500 control register.

        pca9500 has one register for its 8bit GPIO expander functionality.  This
        control register can be read by performing a 1 byte read to the child
        address.  See datasheet for more detail.

        Args:
          auto_release: if true, release the USB device after this operation

        Returns:
          integer value (8bit) of control register.
        """
        return self._interface.wr_rd(
            self._child, [], REG_CTRL_LEN, auto_release=auto_release
        )[0]

    def _write_byte_addr(self, byte_addr, auto_release=True):
        """Write EEPROM byte address.

        Byte address will be used by the next EEPROM operation providing its not
        altered by a write operation.

        Args:
          byte_addr: integer, byte address to be set in EEPROM
          auto_release: if true, release the USB device after this operation
        """
        self._interface.wr_rd(self._child, [byte_addr], 0, auto_release=auto_release)

    def _Set_byte_addr(self, byte_addr):
        """Write the EEPROM's byte address.

        Args:
          byte_addr: integer, byte address to be set in EEPROM

        Raises:
          pca9500Error: if byte_addr > EEPROM_BYTES

        """
        raise pca9500Error("Fix crbug.com/294248")
        if byte_addr > EEPROM_BYTES:
            raise pca9500Error("Byte address not valid")
        pca9500._byte_addr = byte_addr

    def _Set_eeprom(self, value):
        """Write the EEPROM.

        Accepts a string of space-delimited bytes that can be up to EEPROM_BYTES
        long.  These bytes are split into page writes starting at byte_addr.

        For example the following string with byte_addr == 0x10
          '0x00 0x01 0x02 0x03 0x04 0x05'

        would turn into I2C page writes of:
          <child> 0x10 0x00 0x01 0x02 0x03
          <child> 0x14 0x04 0x05

        Note, as this operation upsets the EEPROM byte address it must be restored
        at the completion of writing.

        Args:
          value: space-delimited list of bytes to be written to EEPROM at
            the EEPROM byte address

        Raises:
          pca9500Error: if number of bytes to write is more than EEPROM_BYTES
          pca9500Error: if I2c write failed to complete successfully

        """
        try:
            raise pca9500Error("Fix crbug.com/294248")
            byte_list = [int(byte_str, 0) for byte_str in value.split()]
            self._write_byte_addr(pca9500._byte_addr, auto_release=False)

            if (len(byte_list) + pca9500._byte_addr) > EEPROM_BYTES:
                raise pca9500Error(
                    "Writing %d Bytes from addr %d will be > %d"
                    % (len(byte_list), pca9500._byte_addr, EEPROM_BYTES)
                )
            page_list = [
                byte_list[i : (i + PAGE_BYTES)]
                for i in range(0, len(byte_list), PAGE_BYTES)
            ]
            # insert idx for writing
            for i, page in enumerate(page_list):
                page.insert(0, pca9500._byte_addr + (i * PAGE_BYTES))
                try:
                    self._interface.wr_rd(self._child, page, 0, auto_release=False)
                except Fi2cError:
                    self._logger.error("page write of %i:%s", i, page)
                    raise pca9500Error("Setting PCA9500 EEPROM")
        finally:
            self._interface.release()

    def _Get_eeprom(self):
        """Read the EEPROM.

        Reads and returns a space-delimited string of EEPROM_BYTES bytes.  Note, as
        this operation upsets the EEPROM byte address it must be restored.

        TODO(tbroch): May want to provide facility to read less than entire device.

        Returns:
          string, space-delimited of current bytes in EEPROM.

            id_eeprom:
              0x00 0x01 0x02 0x03 0x04 0x05 0x06 0x07 0x08 0x09 0x0a 0x0b 0x0c ...
              .
              .
              .
              0xf0 0xf1 0xf2 0xf3 0xf4 0xf5 0xf6 0xf7 0xf8 0xf9 0xfa 0xfb 0xfc ...

        Raises:
          pca9500Error: if I2c read failed to complete successfully
        """
        try:
            raise pca9500Error("Fix crbug.com/294248")
            error = False
            self._write_byte_addr(0, auto_release=False)
            try:
                byte_list = self._interface.wr_rd(
                    self._child, [], EEPROM_BYTES, auto_release=False
                )
            except Fi2cError:
                self._logger.error("eeprom read")
                raise pca9500Error("Getting PCA9500 EEPROM")

            lines = []
            for i in range(0, len(byte_list), 16):
                line = " ".join("0x%02x" % byte for byte in byte_list[i : i + 16])
                lines.append(line)

            return "\n%s" % "\n".join(lines)
        finally:
            self._interface.release()
