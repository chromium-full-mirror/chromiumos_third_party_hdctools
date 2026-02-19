# Copyright 2011 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Defines common structures for use with c libraries related to FTDI devices."""
import ctypes

from servo.common import servo_dev_templates


MAX_FTDI_INTERFACES_PER_DEVICE = 4

DEFAULT_VID = servo_dev_templates.get_vid("servo_v4")
DEFAULT_PID = servo_dev_templates.get_pid("servo_v4")

INTERFACE_TYPE_ANY = ctypes.c_int(0)
INTERFACE_TYPE_GPIO = ctypes.c_int(1)
INTERFACE_TYPE_I2C = ctypes.c_int(2)
INTERFACE_TYPE_JTAG = ctypes.c_int(3)
INTERFACE_TYPE_SPI = ctypes.c_int(4)
INTERFACE_TYPE_UART = ctypes.c_int(5)


class FtdiContext(ctypes.Structure):
    """Defines primary context structure for libftdi.

    Declared in ftdi.h with name ftdi_context.
    """

    _fields_ = [
        # USB specific
        ("usb_dev", ctypes.POINTER(ctypes.c_int)),
        ("usb_read_timeout", ctypes.c_int),
        ("usb_write_timeout", ctypes.c_int),
        # FTDI specific
        ("type", ctypes.c_int),
        ("baudrate", ctypes.c_int),
        ("bitbang_enabled", ctypes.c_ubyte),
        ("readbuffer", ctypes.POINTER(ctypes.c_ubyte)),
        ("readbuffer_offset", ctypes.c_uint),
        ("readbuffer_remaining", ctypes.c_uint),
        ("readbuffer_chunksize", ctypes.c_uint),
        ("writebuffer_chunksize", ctypes.c_uint),
        ("max_packet_size", ctypes.c_uint),
        # for FTx232 chips
        ("interface", ctypes.c_int),
        ("index", ctypes.c_int),
        # Endpoints
        ("in_ep", ctypes.c_int),
        ("out_ep", ctypes.c_int),
        ("bitbang_mode", ctypes.c_ubyte),
        ("eeprom_size", ctypes.c_int),
        ("error_str", ctypes.POINTER(ctypes.c_char)),
        ("asynctypes.c_usb_buffer", ctypes.POINTER(ctypes.c_char)),
        ("asynctypes.c_usb_buffer_size", ctypes.c_uint),
        ("module_detach_mode", ctypes.c_int),
    ]


class FtdiCommonArgs(ctypes.Structure):
    """Defines structure of common arguments for FTDI related devices.

    Declared in ftdi_common.h with name ftdi_common_args.
                ("serialname", ctypes.POINTER(ctypes.c_char)),
    """

    _fields_ = [
        ("vendor_id", ctypes.c_uint),
        ("product_id", ctypes.c_uint),
        ("dev_id", ctypes.c_uint),
        ("interface", ctypes.c_int),
        ("serialname", ctypes.c_char_p),
        ("speed", ctypes.c_uint),
        ("bits", ctypes.c_int),
        ("parity", ctypes.c_int),
        ("sbits", ctypes.c_int),
        ("direction,", ctypes.c_ubyte),
        ("value", ctypes.c_ubyte),
    ]


class Gpio(ctypes.Structure):
    """Defines structure for managing typical 8-bit GPIO used in FTDI devices.

    Declared in ftdi_common.h with name gpio_s
    """

    _fields_ = [
        ("value", ctypes.c_ubyte),
        ("direction", ctypes.c_ubyte),
        ("mask", ctypes.c_ubyte),
    ]
