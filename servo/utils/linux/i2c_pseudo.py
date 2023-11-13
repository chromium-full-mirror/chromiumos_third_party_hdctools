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

from servo.utils.linux.i2c import i2c_msg


I2CP_CONTROLLER_PATH = b"/dev/i2c-pseudo"

# ioctl commands from include/uapi/linux/i2c-pseudo.h
I2CP_IOCTL_START = 0x0701
I2CP_IOCTL_XFER_REQ = 0x0702
I2CP_IOCTL_XFER_REPLY = 0x0703
I2CP_IOCTL_GET_COUNTERS = 0x0704
I2CP_IOCTL_SHUTDOWN = 0x0705


class i2cp_ioctl_start_output(ctypes.Structure):
    _fields_ = (
        ("adapter_num", ctypes.c_uint64),
        ("name_len", ctypes.c_uint32),
    )


class i2cp_ioctl_start_arg(ctypes.Structure):
    _fields_ = (
        ("output", i2cp_ioctl_start_output),
        ("functionality", ctypes.c_uint32),
        ("timeout_ms", ctypes.c_uint32),
        ("name", ctypes.c_char_p),
    )


class i2cp_ioctl_xfer_counters(ctypes.Structure):
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


class i2cp_ioctl_xfer_req_output(ctypes.Structure):
    _fields_ = (
        ("xfer_id", ctypes.c_uint64),
        ("num_msgs", ctypes.c_uint32),
    )


class i2cp_ioctl_xfer_req_arg(ctypes.Structure):
    _fields_ = (
        ("output", i2cp_ioctl_xfer_req_output),
        ("msgs", ctypes.POINTER(i2c_msg)),
        ("data_buf", ctypes.POINTER(ctypes.c_uint8)),
        ("msgs_len", ctypes.c_uint32),
        ("data_buf_len", ctypes.c_uint32),
    )


class i2cp_ioctl_xfer_reply_arg(ctypes.Structure):
    _fields_ = (
        ("msgs", ctypes.POINTER(i2c_msg)),
        ("xfer_id", ctypes.c_uint64),
        ("num_msgs", ctypes.c_uint32),
        ("error", ctypes.c_uint32),
    )


__all__ = [n for n in dir() if n.startswith("I2CP_") or n.startswith("i2cp_")]
