# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
This provides types and constants for working with the Linux I2C userspace API
from include/uapi/linux/i2c.h .

This module is designed to be friendly for 'import *' by making these promises:
* All names thus imported will begin with either "I2C_" or "i2c_" .
* No other modules will be passed through in this manner.
"""

import ctypes


# struct I2cMsg flags from include/uapi/linux/i2c.h
I2C_M_RD = 0x0001
I2C_M_TEN = 0x0010
I2C_M_DMA_SAFE = 0x0200
I2C_M_RECV_LEN = 0x0400
I2C_M_NO_RD_ACK = 0x0800
I2C_M_IGNORE_NAK = 0x1000
I2C_M_REV_DIR_ADDR = 0x2000
I2C_M_NOSTART = 0x4000
I2C_M_STOP = 0x8000

# i2c adapter functionality flags from include/uapi/linux/i2c.h
I2C_FUNC_I2C = 0x00000001
I2C_FUNC_10BIT_ADDR = 0x00000002
I2C_FUNC_PROTOCOL_MANGLING = 0x00000004
I2C_FUNC_SMBUS_PEC = 0x00000008
I2C_FUNC_NOSTART = 0x00000010
I2C_FUNC_SLAVE = 0x00000020  # nocheck
I2C_FUNC_SMBUS_BLOCK_PROC_CALL = 0x00008000
I2C_FUNC_SMBUS_QUICK = 0x00010000
I2C_FUNC_SMBUS_READ_BYTE = 0x00020000
I2C_FUNC_SMBUS_WRITE_BYTE = 0x00040000
I2C_FUNC_SMBUS_READ_BYTE_DATA = 0x00080000
I2C_FUNC_SMBUS_WRITE_BYTE_DATA = 0x00100000
I2C_FUNC_SMBUS_READ_WORD_DATA = 0x00200000
I2C_FUNC_SMBUS_WRITE_WORD_DATA = 0x00400000
I2C_FUNC_SMBUS_PROC_CALL = 0x00800000
I2C_FUNC_SMBUS_READ_BLOCK_DATA = 0x01000000
I2C_FUNC_SMBUS_WRITE_BLOCK_DATA = 0x02000000
I2C_FUNC_SMBUS_READ_I2C_BLOCK = 0x04000000
I2C_FUNC_SMBUS_WRITE_I2C_BLOCK = 0x08000000
I2C_FUNC_SMBUS_HOST_NOTIFY = 0x10000000
I2C_FUNC_SMBUS_BYTE = I2C_FUNC_SMBUS_READ_BYTE | I2C_FUNC_SMBUS_WRITE_BYTE
I2C_FUNC_SMBUS_BYTE_DATA = (
    I2C_FUNC_SMBUS_READ_BYTE_DATA | I2C_FUNC_SMBUS_WRITE_BYTE_DATA
)
I2C_FUNC_SMBUS_WORD_DATA = (
    I2C_FUNC_SMBUS_READ_WORD_DATA | I2C_FUNC_SMBUS_WRITE_WORD_DATA
)
I2C_FUNC_SMBUS_BLOCK_DATA = (
    I2C_FUNC_SMBUS_READ_BLOCK_DATA | I2C_FUNC_SMBUS_WRITE_BLOCK_DATA
)
I2C_FUNC_SMBUS_I2C_BLOCK = (
    I2C_FUNC_SMBUS_READ_I2C_BLOCK | I2C_FUNC_SMBUS_WRITE_I2C_BLOCK
)
I2C_FUNC_SMBUS_EMUL = (
    I2C_FUNC_SMBUS_QUICK
    | I2C_FUNC_SMBUS_BYTE
    | I2C_FUNC_SMBUS_BYTE_DATA
    | I2C_FUNC_SMBUS_WORD_DATA
    | I2C_FUNC_SMBUS_PROC_CALL
    | I2C_FUNC_SMBUS_WRITE_BLOCK_DATA
    | I2C_FUNC_SMBUS_I2C_BLOCK
    | I2C_FUNC_SMBUS_PEC
)


class I2cMsg(ctypes.Structure):
    _fields_ = (
        ("addr", ctypes.c_uint16),
        ("flags", ctypes.c_uint16),
        ("len", ctypes.c_uint16),
        ("buf", ctypes.POINTER(ctypes.c_uint8)),
    )


__all__ = [n for n in dir() if n.startswith("I2C_") or n.startswith("i2c_")]
