# Copyright 2016 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# pylint: disable=abstract-method, implicit-str-concat
"""Allows creation of gpio interface via stm32 usb."""

import struct

from servo.common.interface import common as c
from servo.common.interface import gpio_interface
from servo.common.interface import stm32usb


class SgpioError(c.InterfaceError):
    """Class for exceptions of Sgpio."""

    def __init__(self, msg, value=0):
        """SgpioError constructor.

        Args:
          msg: string, message describing error in detail
          value: integer, value of error when non-zero status returned.  Default=0
        """
        super().__init__(msg, value)
        self.msg = msg
        self.value = value


class Sgpio(gpio_interface.GpioInterface):
    """Provide interface to stm32 gpio USB endpoint.

    Instance Variables:
    _logger: Sgpio tagged log output
    _susb: stm32 usb object
    """

    def __init__(self, vendor=0x18D1, product=0x500F, interface=1, serialname=None):
        """Sgpio constructor.

        Loads libraries for libusb.  Creates instance objects
        and Gpio to interact with the library and initializes them.

        Args:
          vendor    : usb vendor id of stm32 device
          product   : usb product id of stm32 device
          interface : interface number ( 1 - 4 ) of stm32 device to use
          serialname: string of device serialname/number TODO: is this a thing?

        Raises:
          SgpioError: An error accessing Sgpio object
        """
        gpio_interface.GpioInterface.__init__(self)

        self._susb = stm32usb.Susb(
            vendor=vendor,
            product=product,
            interface_id=interface,
            serialname=serialname,
            logger=self._logger,
        )

        self._logger.debug("Set up stm32 gpio")

    @staticmethod
    def build(vid, pid, sid, interface_data, **_kwargs):
        """Factory method to implement the interface."""
        c.build_logger.info("Sgpio: interface: %s", interface_data)
        return Sgpio(
            vendor=vid,
            product=pid,
            interface=interface_data["interface"],
            serialname=sid,
        )

    @staticmethod
    def name():
        """Name to request interface by in interface config maps."""
        return "stm32_gpio"

    def __del__(self):
        """Sgpio destructor."""
        self._logger.debug("Close")

    def wr_rd(
        self, offset, width=1, dir_val=None, wr_val=None, _chip=None, _muxfile=None
    ):
        """Write and/or read GPIO bit.

        Args:
          offset  : bit offset of the gpio to read or write
          width   : integer, number of contiguous bits in gpio to read or write
          dir_val : Not used. defaulted to None.
          wr_val  : value to write to the GPIO. If unset, skips the write.
          chip    : Not used. defaulted to None.
          muxfile : Not used. defaulted to None.

        Returns:
          integer value from reading the gpio value ( masked & aligned )
        """
        self._logger.debug(
            "Sgpio.wr_rd(offset=%s, width=%s, dir_val=%s, wr_val=%s)",
            offset,
            width,
            dir_val,
            wr_val,
        )
        # Read preexisting values for debug output.
        ret = self._susb.read_ep(4, self._susb.TIMEOUT_MS)
        read_mask = struct.unpack("<I", ret)[0]
        self._logger.debug("Read mask: 0x%08x", read_mask)

        width_mask = (1 << width) - 1
        set_mask = 0
        clear_mask = 0

        if wr_val is not None:
            set_mask = (wr_val & width_mask) << offset
            clear_mask = (~wr_val & width_mask) << offset

        byte_str = struct.pack("<II", set_mask, clear_mask)
        ret = self._susb.write_ep(byte_str, self._susb.TIMEOUT_MS)
        if ret != len(byte_str):
            raise SgpioError("Wrote %d bytes, expected %d" % (ret, len(byte_str)))

        # GPIO cached values update on read,
        ret = self._susb.read_ep(4, self._susb.TIMEOUT_MS)
        ret = self._susb.read_ep(4, self._susb.TIMEOUT_MS)
        if len(ret) != 4:
            raise SgpioError(
                "Read error: expected 4 bytes, got %d [%s]" % (len(ret), ret)
            )

        read_mask = struct.unpack("<I", ret)[0]
        self._logger.debug("Read mask: 0x%08x", read_mask)

        readvalue = (read_mask >> offset) & width_mask
        self._logger.debug("Read value: 0x%x", readvalue)
        return readvalue

    def reinitialize(self):
        """Reinitialize the usb endpoint"""
        self._susb.reset_usb()

    def get_device_info(self):
        """The usb device information."""
        return self._susb.get_device_info()

    def close(self):
        """Stm32gpio wind down logic.

        Note: because we run this in a thread, an exception gets thrown at the very
        end unless we explicitly predelete this instance.
        """
        del self._susb
