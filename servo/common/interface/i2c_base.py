# Copyright 2018 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Provides a base class for I2C bus implementations."""

import logging
import threading

from servo.common.interface import interface


def _format_write_list(write_list):
    """Format a BaseI2CBus.wr_rd() write_list arg for logging.

    Args:
      write_list: list of output byte values [0~255], or None for no write

    Returns:
      str
    """
    if write_list is None:
        return str(None)
    return "[%s]" % (", ".join("0x%02X" % (value,) for value in write_list),)


class BaseI2CBus(interface.Interface):
    """Base class for all I2c bus classes.

    Thread safety:
      All public methods are safe to invoke concurrently from multiple threads.

    Usage:
      class MyI2CBus(BaseI2CBus):
        def _raw_wr_rd(self, child_address, write_list, read_count):
          # Implement hdctools wr_rd() interface here.
    """

    def __init__(self):
        """Initializer."""
        interface.Interface.__init__(self)
        self.__logger = logging.getLogger("i2c_base")
        self.__lock = threading.Lock()

    def multi_wr_rd(self, transactions, auto_release=True):
        """Allows for multiple write/read/write+read I2C transactions.

        This guarantees that no other I2C messages/transactions are sent by this
        object in the middle of the transactions passed to this function.

        This does NOT combine the transactions passed to this function into one I2C
        transaction.

        Args:
          transactions: iterable of (child_address, write_list, read_count) tuples
            child_address: 7 bit I2C child address.
            write_list: list of output byte values [0~255], or None for no write
            read_count: number of byte values to read from device, or None for no
                read
          auto_release: if true, release the USB device after this operation

        Returns:
          [None or [int]] - A list of .wr_rd() return values, one for each
              transaction.

              Each item is a list of the bytes read from one transaction.  If no
              bytes were read, the item may be an empty list, or may be None instead
              of a list.

              Instead of int, another type that represents and acts as an integer
              may be used, such as ctypes.c_ubyte.
        """
        with self.__lock:
            try:
                return [
                    self._raw_wr_rd(*args, auto_release=False) for args in transactions
                ]
            finally:
                if auto_release:
                    self.release()

    def wr_rd(self, child_address, write_list, read_count, auto_release=True):
        """Implements hdctools wr_rd() interface.

        This function writes byte values list to I2C device (if given), then reads
        byte values from the same device (if requested).

        For a given I2C bus object, overlapping calls to this method will be
        serialized by means of a mutex or equivalent, thus while one call is
        executing, the rest will block.

        Args:
          child_address: 7 bit I2C child address.
          write_list: list of output byte values [0~255], or None for no write
          read_count: number of byte values to read from device, or None for no read
          auto_release: if true, release the USB device after this operation

        Returns:
          None or [int] - A list of the bytes read.  If no bytes were read, either
              None or an empty list may be returned.  Instead of int, another type
              that represents and acts as an integer may be used, such as
              ctypes.c_ubyte.
        """
        with self.__lock:
            self.__logger.debug(
                "i2c_base.BaseI2CBus.wr_rd(0x%02X, %s, %s) called",
                child_address,
                _format_write_list(write_list),
                read_count,
            )
            retval = self._raw_wr_rd(
                child_address, write_list, read_count, auto_release=auto_release
            )
            self.__logger.debug(
                "i2c_base.BaseI2CBus.wr_rd(0x%02X, %r, %s) returning %s",
                child_address,
                _format_write_list(write_list),
                read_count,
                retval,
            )
        return retval

    def _raw_wr_rd(self, child_address, write_list, read_count, auto_release=True):
        """Implements hdctools wr_rd() interface.

        This function writes byte values list to I2C device (if given), then reads
        byte values from the same device (if requested).

        For a given I2C bus object, there should never be overlapping calls to this
        method.  Implementations should therefore make no special effort to handle
        calls from multiple threads.

        Args:
          child_address: 7 bit I2C child address.
          write_list: list of output byte values [0~255], or None for no write
          read_count: number of byte values to read from device, or None for no read
          auto_release: if true, release the USB device after this operation

        Returns:
          None or [int] - A list of the bytes read.  If no bytes were read, either
              None or an empty list may be returned.  Instead of int, another type
              that represents and acts as an integer may be used, such as
              ctypes.c_ubyte.
        """
        raise NotImplementedError

    def release(self):
        """For usb devices only, release device so that external tools can use it."""
