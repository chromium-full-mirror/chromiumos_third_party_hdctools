# Copyright 2018 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Provides a base class for I2C bus implementations."""

import logging
import os
import subprocess
import sys
import threading
import weakref

from servo.common.interface import i2c_pseudo_v1
from servo.common.interface import i2c_pseudo_v2
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
        self.__pseudo_adap = None
        self.__reinit()

    # This exists to reinitialize the I2C pseudo controller after FTDI I2C
    # reinitialization, which is a hack supported for iteflash using Servo v2.
    # Otherwise, __reinit() would just be part of __init__().
    def init(self):
        self.__reinit()

    def __try_i2cp(self, pseudo_adap):
        """Try initializing an i2c-pseudo adapter implementation.

        Args:
            pseudo_adap: i2c_pseudo_base.BaseI2cPseudoAdapter

        Returns:
            bool - True for success, False if the i2c-pseudo device was not found
        """
        pseudo_device_path = pseudo_adap.default_pseudo_device()
        if not os.path.exists(pseudo_device_path):
            return False
        # This circular reference is less than ideal.
        # The weakref avoids a reference count cycle.
        # Avoding the circular reference entirely would be preferable.
        self.__logger.info(
            "i2c-pseudo device path %r found, starting %s I2C pseudo adapter",
            pseudo_device_path,
            type(pseudo_adap).__name__,
        )
        pseudo_adap.init(
            servo_i2c_bus=weakref.proxy(self), pseudo_device_path=pseudo_device_path
        )
        pseudo_adap.start()
        self.__pseudo_adap = pseudo_adap
        return True

    def __reinit(self):
        """Initialize or re-initialize the I2C pseudo adapter for this I2C bus."""
        self.__modprobe("i2c-pseudo", True)
        with self.__lock:
            if self.__pseudo_adap is not None:
                self.__do_close()
            for create_i2cp in (
                i2c_pseudo_v2.I2cPseudoV2Adapter,
                i2c_pseudo_v1.I2cPseudoV1Adapter,
            ):
                if self.__try_i2cp(create_i2cp()):
                    break
            else:
                self.__logger.info(
                    "i2c-pseudo device not found, skipping I2C pseudo adapter"
                )
                return
        # The I2C pseudo adapter itself does not need or use i2c-dev.
        # However any userspace program wanting to use a
        # servod I2C pseudo adapter will need i2c-dev,
        # so we load it for them if available.
        self.__modprobe("i2c-dev", True)

    @property
    def pseudo_adap(self):
        """Get the I2C pseudo adapter object for this I2C bus.

        Returns:
          None or i2c_pseudo_base.BaseI2cPseudoAdapter
        """
        return self.__pseudo_adap

    def multi_wr_rd(self, transactions):
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
            return [self._raw_wr_rd(*args) for args in transactions]

    def wr_rd(self, child_address, write_list, read_count):
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
            retval = self._raw_wr_rd(child_address, write_list, read_count)
            self.__logger.debug(
                "i2c_base.BaseI2CBus.wr_rd(0x%02X, %r, %s) returning %s",
                child_address,
                _format_write_list(write_list),
                read_count,
                retval,
            )
        return retval

    def _raw_wr_rd(self, child_address, write_list, read_count):
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

        Returns:
          None or [int] - A list of the bytes read.  If no bytes were read, either
              None or an empty list may be returned.  Instead of int, another type
              that represents and acts as an integer may be used, such as
              ctypes.c_ubyte.
        """
        raise NotImplementedError

    def close(self):
        """Stop the I2C pseudo interface, if it was started."""
        with self.__lock:
            if self.__pseudo_adap is not None:
                self.__do_close()

    # self.__lock must be held and self.__pseudo_adap must not be None.
    def __do_close(self):
        self.__pseudo_adap.shutdown(2)
        # Break the circular reference.
        self.__pseudo_adap = None

    def __modprobe(self, module, quiet):
        """Run modprobe for a given module name.

        Args:
          module: str - The module name to attempt to load.
          quiet: bool - Whether or not to ask modprobe to suppress error output.
            Regardless of the value of this setting, modprobe stdout and stderr will
            be inherited from servod.

        The modprobe attempt and its exit status will be logged at INFO level
        regardless of the quiet setting.
        """
        # Only attempt to modprobe if the module isn't already loaded.
        sysfs_path = "/sys/module/%s/" % (module.replace("-", "_"),)
        if os.path.exists(sysfs_path):
            logging.info(
                "Skipping modprobe of %s: it is already loaded per existence of: %s",
                module,
                sysfs_path,
            )
            return 0
        args = []
        # Run using sudo so that this also works outside the chroot as non-root.
        if os.geteuid():
            args.append("sudo")
            # Only prompt for password if stdin is a terminal.
            if not sys.stdin.isatty():
                args.append("-n")
            args.append("--")
        args.append("modprobe")
        if quiet:
            args.append("--quiet")
        args.append("--")
        args.append(module)
        logging.info("Executing command: %r", args)
        ret = subprocess.call(args)
        logging.debug(
            "Exit status was %d (negative is killed by signal) for command: %r",
            ret,
            args,
        )
        return ret
