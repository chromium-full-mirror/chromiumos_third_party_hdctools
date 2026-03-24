# Copyright 2014 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""EEPROM driver for ST M24C02.

The driver provides functions to read data from or write data to
one of 8 ST M24C02 EEPROMs, which child addresses are 0x50 - 0x57.
"""

# servo libs
from servo.drv import hw_driver


# Devices shared among driver objects:
#   (interface instance, child) => M24C02Device instance
m24c02_devices = {}


class EepromError(hw_driver.HwDriverError):
    """Error occurred accessing M24C02."""

    pass


class M24C02Device:
    """Defines a M24C02 device shared among many M24C02 drivers."""

    def __init__(self, offset, read_count):
        self._offset = offset
        self._read_count = read_count

    def _set(self, offset, read_count):
        """Set offset and read count.

        Args:
          offset: Start address for reading/writing.
          read_count: Size of reading bytes.

        Raises:
          ValueError: If offset or count doesn't make sense.
        """
        if (offset < 0) or (offset > (m24c02._EEPROM_SIZE - 1)):
            raise ValueError("Offset(%d) error." % offset)
        if (offset + read_count) > m24c02._EEPROM_SIZE:
            raise ValueError("Boundary(%d) error." % (offset + read_count))

        self._offset = offset
        self._read_count = read_count

    def _get(self):
        """Get the operating parameters.

        Returns:
          Get offset and read count.
        """
        return (self._offset, self._read_count)


class m24c02(hw_driver.HwDriver):
    """Provides drv=m24c02 control."""

    # Supported M24C02 child addresses.
    SUPPORTED_ADDRESS = (80, 81, 82, 83, 84, 85, 86, 87)

    _EEPROM_SIZE = 256
    HELP_TEXT = """
    # Step 1. Prepare parameters for operating EEPROM.
      dut-control plankton_rom_[1-8]_parameter
      dut-control plankton_rom_[1-8]_parameter:"[offset];[read count]"

    # Step 2. Read/write data from/to EEPROM.
      dut-control plankton_rom_[1-8]_data
      dut-control plankton_rom_[1-8]_data:"[text]"

    # Example
      dut-control plankton_rom_1_parameter
      dut-control plankton_rom_1_parameter:"10;20"
      dut-control plankton_rom_1_data               # read 20 bytes from offset 10
      dut-control plankton_rom_1_data:"Hello"  # write "Hello" to  offset 10
    """

    def _get_child(self):
        """Checks and return needed params to call driver.

        Returns:
          child: 7-bit i2c address.

        Raises:
          EepromError: If the 'child' doesn't exist.
        """
        if "child" not in self._params:
            raise EepromError('Missing child address "child"')
        child = int(self._params["child"], 0)
        return child

    def _drv_init(self):
        """Driver specific initializer."""
        super()._drv_init()

        child = self._get_child()
        if child not in m24c02.SUPPORTED_ADDRESS:
            raise ValueError("Child address(%d) error." % child)

        offset = 0
        read_count = m24c02._EEPROM_SIZE
        device_key = (self._interface, child)
        if device_key not in m24c02_devices:
            m24c02_devices[device_key] = M24C02Device(offset, read_count)

        self._device = m24c02_devices[device_key]

    def _read_byte(self, offset, auto_release=True):
        """Reads one byte from EEPROM.

        Args:
          offset: Start address for reading.
          auto_release: if true, release the USB device after this operation

        Returns:
          Read back one byte.
        """
        buffer = self._interface.wr_rd(
            self._get_child(), [offset], 1, auto_release=auto_release
        )
        return buffer[0]

    def _read_bytes(self, offset, count, auto_release=True):
        """Reads one or more bytes from EEPROM.

        Args:
          offset: Start address for reading.
          count: Size of reading bytes.
          auto_release: if true, release the USB device after this operation

        Returns:
          A list of bytes.
        """
        # TODO(Aaron) To replace this with bulk read command.
        try:
            return [
                self._read_byte(addr, auto_release=False)
                for addr in range(offset, offset + count)
            ]
        finally:
            if auto_release:
                self._interface.release()

    def _write_byte(self, offset, value, auto_release=True):
        """Writes one byte to EEPROM.

        Args:
          offset: Start address for writing.
          value: One byte written to EEPROM.
          auto_release: if true, release the USB device after this operation
        """
        self._interface.wr_rd(
            self._get_child(), [offset, value], 0, auto_release=auto_release
        )

    def _write_bytes(self, offset, text, auto_release=True):
        """Writes one or more bytes to EEPROM.

        Args:
          offset: Start address for writing.
          text: One or more bytes written to EEPROM.
          auto_release: if true, release the USB device after this operation

        Raises:
          ValueError: If text exceeds EEPROM size.
        """
        try:
            if (offset + len(text)) > m24c02._EEPROM_SIZE:
                raise ValueError("Boundary(%d) error." % (offset + len(text)))

            for c in text:
                self._write_byte(offset, ord(c), auto_release=False)
                offset = offset + 1
        finally:
            if auto_release:
                self._interface.release()

    def _Get_rom_params(self):
        """Gets operating parameters.

        Returns:
          Show child address, offset, and read count.
        """
        return (self._get_child(),) + self._device.get()

    def _Set_rom_params(self, params):
        """Sets offset and read count.

        Args:
          params: Format is "[offset];[read count]"

        Raises:
          EepromError: If offset or count doesn't make sense.
        """
        try:
            offset, read_count = map(int, params.split(";", 1))
            self._device.set(offset, read_count)
        except (ValueError, IndexError) as e:
            raise EepromError(str(e) + m24c02.HELP_TEXT)

    def _Get_data(self):
        """Reads bytes from one of 8 EEPROMs.

        Returns:
          Read one or more bytes.
        """
        offset, read_count = self._device.get()
        return self._read_bytes(offset, read_count)

    def _Set_data(self, text):
        """Writes bytes to one of 8 EEPROMs.

        Args:
          text: data will be written to EEPROM.

        Raises:
          EepromError: If text exceeds EEPROM size.
        """
        try:
            offset, empty = self._device.get()
            self._write_bytes(offset, text)
        except ValueError as e:
            raise EepromError(str(e) + m24c02.HELP_TEXT)
