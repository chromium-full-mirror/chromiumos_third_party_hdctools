# Copyright 2011 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Common functions for tools and libraries related to FTDI devices."""

import argparse
import ctypes
import ctypes.util
import logging
import sys

from servo.common.interface import common as c
from servo.common.interface import ftdi_common


def get_interface_and_pid(index, pid):
    """Helper to retrieve the 'real' ftdi pid and interface given the index.

    Args:
      index: int, index in the interface list
      pid: product id of ftdi device

    Returns:
      tuple(index, pid) - the effective index and pid after conversion
    """
    # servos with multiple FTDI are guaranteed to have contiguous USB PIDs
    # The interface argument in ftdi initialization is the interface number.
    idx = ((index - 1) % ftdi_common.MAX_FTDI_INTERFACES_PER_DEVICE) + 1
    # pid has to be an int. ensure the increment is also an int.
    product_increment = int((index - 1) / ftdi_common.MAX_FTDI_INTERFACES_PER_DEVICE)
    pid = pid + product_increment
    if product_increment:
        c.build_logger.info("Use the next FTDI part @ pid = 0x%04x", pid)
    return (idx, pid)


def load_libs(*args):
    """Load libraries and return dll objects.

    Calls sys.exit if unable to locate the library

    Args:
      args : list of strings names of libraries to load

    Returns:
      List of PyDLL objects

    Raises:
      SystemExit on failure
    """
    dll_list = []

    # Mapping of library names to known aliases
    lib_aliases = {
        "ftdi": ["ftdi", "ftdi1"],
    }

    for lib_name in args:
        lib_path = None

        aliases = lib_aliases.get(lib_name)
        if aliases:
            for name in aliases:
                lib_path = ctypes.util.find_library(name)
                if lib_path:
                    break
        else:
            lib_path = ctypes.util.find_library(lib_name)

        if lib_path is None:
            print("-E- Unable to find library path %s" % (lib_name))
            sys.exit(1)

        logging.debug("lib_path for %s is %s\n", lib_name, lib_path)

        try:
            dll_list.append(ctypes.cdll.LoadLibrary(lib_path))
        except OSError as e:
            print("-E- Unable to find library %s : %s" % (lib_name, e))
            sys.exit(1)
    return dll_list


def parse_common_args(
    vendor=ftdi_common.DEFAULT_VID,
    product=ftdi_common.DEFAULT_PID,
    interface=1,
    serialname=None,
):
    """Parse common arguments for tools related to FTDI devices.

    Args:
      vendor    : integer value of USB vendor id of FTDI device
      product   : integer value of USB vendor id of FTDI device
      interface : integer ( 1 - 4 ) of interface on FTDI device
      serialname: string of device serialname/number as defined in FTDI eeprom.

    Returns:
      (values, args) where 'values' is a optparse.Values instance and 'args' is
      the list of arguments left over after parsing options.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d",
        "--debug",
        help="enable debug messages",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-v", "--vendor", help="vendor id of ftdi device", default=vendor, type=int
    )
    parser.add_argument(
        "-p", "--product", help="product id of ftdi device", default=product, type=int
    )
    parser.add_argument(
        "-i", "--interface", help="ftdi interface to use", type=int, default=interface
    )
    parser.add_argument(
        "-s",
        "--serialname",
        default=serialname,
        type=str,
        help="device serialname stored in eeprom",
    )
    return parser.parse_args()
