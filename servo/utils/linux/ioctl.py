# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
This provides types and constants for working with the Linux I2C userspace API
from include/uapi/asm-generic/ioctl.h .

This module is designed to be friendly for 'import *' by making these promises:
* All names thus imported will be names provided by ioctl.h itself.
* No other modules will be passed through in this manner.
"""

import ctypes


_IOC_NRBITS = 8
_IOC_TYPEBITS = 8
_IOC_SIZEBITS = 14
_IOC_DIRBITS = 2

_IOC_NRMASK = (1 << _IOC_NRBITS) - 1
_IOC_TYPEMASK = (1 << _IOC_TYPEBITS) - 1
_IOC_SIZEMASK = (1 << _IOC_SIZEBITS) - 1
_IOC_DIRMASK = (1 << _IOC_DIRBITS) - 1

_IOC_NRSHIFT = 0
_IOC_TYPESHIFT = _IOC_NRSHIFT + _IOC_NRBITS
_IOC_SIZESHIFT = _IOC_TYPESHIFT + _IOC_TYPEBITS
_IOC_DIRSHIFT = _IOC_SIZESHIFT + _IOC_SIZEBITS

_IOC_NONE = 0
_IOC_WRITE = 1
_IOC_READ = 2


def _ioc(dir_, type_, nr, size):
    return (
        (dir_ << _IOC_DIRSHIFT)
        | (type_ << _IOC_TYPESHIFT)
        | (nr << _IOC_NRSHIFT)
        | (size << _IOC_SIZESHIFT)
    )


def _ioc_typecheck(t):
    return ctypes.sizeof(t)


def _io(type_, nr):
    return _ioc(_IOC_NONE, type_, nr, 0)


def _ior(type_, nr, size):
    return _ioc(_IOC_READ, type_, nr, (_ioc_typecheck(size)))


def _iow(type_, nr, size):
    return _ioc(_IOC_WRITE, type_, nr, (_ioc_typecheck(size)))


def _iowr(type_, nr, size):
    return _ioc(_IOC_READ | _IOC_WRITE, type_, nr, (_ioc_typecheck(size)))


def _ior_bad(type_, nr, size):
    return _ioc(_IOC_READ, type_, nr, ctypes.sizeof(size))


def _iow_bad(type_, nr, size):
    return _ioc(_IOC_WRITE, type_, nr, ctypes.sizeof(size))


def _iowr_bad(type_, nr, size):
    return _ioc(_IOC_READ | _IOC_WRITE, type_, nr, ctypes.sizeof(size))


def _ioc_dir(nr):
    return (nr >> _IOC_DIRSHIFT) & _IOC_DIRMASK


def _ioc_type(nr):
    return (nr >> _IOC_TYPESHIFT) & _IOC_TYPEMASK


def _ioc_nr(nr):
    return (nr >> _IOC_NRSHIFT) & _IOC_NRMASK


def _ioc_size(nr):
    return (nr >> _IOC_SIZESHIFT) & _IOC_SIZEMASK


IOC_IN = _IOC_WRITE << _IOC_DIRSHIFT
IOC_OUT = _IOC_READ << _IOC_DIRSHIFT
IOC_INOUT = (_IOC_WRITE | _IOC_READ) << _IOC_DIRSHIFT
IOCSIZE_MASK = _IOC_SIZEMASK << _IOC_SIZESHIFT
IOCSIZE_SHIFT = _IOC_SIZESHIFT


__all__ = [n for n in dir() if n.startswith("IO") or n.startswith("_io")]
