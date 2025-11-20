# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
This provides types and constants for working with the Linux i2c-pseudo
userspace API from include/uapi/linux/i2c-pseudo.h .

This module is designed to be friendly for 'import *' by making these promises:
* All names thus imported will begin with either "I2CP_" or "i2cp_" .
* No other modules will be passed through in this manner.
"""

import ctypes

from servo.utils.linux import i2c
from servo.utils.linux import ioctl


I2CP_CONTROLLER_PATH = b"/dev/i2c-pseudo"


class I2cpIoctlStartOutput(ctypes.Structure):
    _fields_ = (
        ("adapter_num", ctypes.c_uint64),
        ("name_len", ctypes.c_uint32),
    )


class I2cpIoctlStartArg(ctypes.Structure):
    _fields_ = (
        ("output", I2cpIoctlStartOutput),
        ("functionality", ctypes.c_uint32),
        ("timeout_ms", ctypes.c_uint32),
        ("name", ctypes.c_char_p),
    )


class I2cpIoctlXferCounters(ctypes.Structure):
    _fields_ = (
        ("controller_replied", ctypes.c_uint64),
        ("unknown_failure", ctypes.c_uint64),
        ("after_shutdown", ctypes.c_uint64),
        ("too_many_msgs", ctypes.c_uint64),
        ("too_much_data", ctypes.c_uint64),
        ("interrupted_before_req", ctypes.c_uint64),
        ("interrupted_before_reply", ctypes.c_uint64),
        ("timed_out_before_req", ctypes.c_uint64),
        ("timed_out_before_reply", ctypes.c_uint64),
    )


class I2cpIoctlXferReqOutput(ctypes.Structure):
    _fields_ = (
        ("xfer_id", ctypes.c_uint64),
        ("num_msgs", ctypes.c_uint32),
    )


class I2cpIoctlXferReqArg(ctypes.Structure):
    _fields_ = (
        ("output", I2cpIoctlXferReqOutput),
        ("msgs", ctypes.POINTER(i2c.i2c_msg)),
        ("data_buf", ctypes.POINTER(ctypes.c_uint8)),
        ("msgs_len", ctypes.c_uint32),
        ("data_buf_len", ctypes.c_uint32),
    )


class I2cpIoctlXferReplyArg(ctypes.Structure):
    _fields_ = (
        ("msgs", ctypes.POINTER(i2c.i2c_msg)),
        ("xfer_id", ctypes.c_uint64),
        ("num_msgs", ctypes.c_uint32),
        ("error", ctypes.c_uint32),
    )


I2CP_IOCTL_CODE = 0x2C

I2CP_IOCTL_START = ioctl._IOWR(I2CP_IOCTL_CODE, 0, I2cpIoctlStartArg)
I2CP_IOCTL_XFER_REQ = ioctl._IOWR(I2CP_IOCTL_CODE, 1, I2cpIoctlXferReqArg)
I2CP_IOCTL_XFER_REPLY = ioctl._IOW(I2CP_IOCTL_CODE, 2, I2cpIoctlXferReplyArg)
I2CP_IOCTL_GET_COUNTERS = ioctl._IOR(I2CP_IOCTL_CODE, 3, I2cpIoctlXferCounters)
I2CP_IOCTL_SHUTDOWN = ioctl._IO(I2CP_IOCTL_CODE, 4)


__all__ = [n for n in dir() if n.startswith("I2CP_") or n.startswith("i2cp_")]
