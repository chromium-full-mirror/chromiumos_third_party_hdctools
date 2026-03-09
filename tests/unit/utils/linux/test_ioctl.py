# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import ctypes

from servo.utils.linux import ioctl


def test_ioc_macros():
    """Test basic ioctl macro functionality."""
    # Testing _ioc
    res = ioctl._ioc(1, 2, 3, 4)
    expected = (
        (1 << ioctl._IOC_DIRSHIFT)
        | (2 << ioctl._IOC_TYPESHIFT)
        | (3 << ioctl._IOC_NRSHIFT)
        | (4 << ioctl._IOC_SIZESHIFT)
    )
    assert res == expected

    # Testing typecheck
    assert ioctl._ioc_typecheck(ctypes.c_uint32) == 4

    # Testing _io, _ior, _iow, _iowr
    class MockStruct(ctypes.Structure):
        _fields_ = [("val", ctypes.c_uint32)]

    io_res = ioctl._io(2, 3)
    assert io_res == ioctl._ioc(ioctl._IOC_NONE, 2, 3, 0)

    ior_res = ioctl._ior(2, 3, MockStruct)
    assert ior_res == ioctl._ioc(ioctl._IOC_READ, 2, 3, 4)

    iow_res = ioctl._iow(2, 3, MockStruct)
    assert iow_res == ioctl._ioc(ioctl._IOC_WRITE, 2, 3, 4)

    iowr_res = ioctl._iowr(2, 3, MockStruct)
    assert iowr_res == ioctl._ioc(ioctl._IOC_READ | ioctl._IOC_WRITE, 2, 3, 4)


def test_ioc_bad_macros():
    class MockStruct(ctypes.Structure):
        _fields_ = [("val", ctypes.c_uint32)]

    # testing _ior_bad, _iow_bad, _iowr_bad
    # Since we are passing the class, ctypes.sizeof(size) would normally fail
    # but let's pass an instance or integer if sizeof accepts it.
    mock_inst = MockStruct()
    assert ioctl._ior_bad(2, 3, mock_inst) == ioctl._ioc(ioctl._IOC_READ, 2, 3, 4)
    assert ioctl._iow_bad(2, 3, mock_inst) == ioctl._ioc(ioctl._IOC_WRITE, 2, 3, 4)
    assert ioctl._iowr_bad(2, 3, mock_inst) == ioctl._ioc(
        ioctl._IOC_READ | ioctl._IOC_WRITE, 2, 3, 4
    )


def test_ioc_extract_macros():
    """Test extracting dir, type, nr, size from ioctl code."""
    code = ioctl._ioc(ioctl._IOC_READ | ioctl._IOC_WRITE, 0xAB, 0xCD, 128)

    assert ioctl._ioc_dir(code) == (ioctl._IOC_READ | ioctl._IOC_WRITE)
    assert ioctl._ioc_type(code) == 0xAB
    assert ioctl._ioc_nr(code) == 0xCD
    assert ioctl._ioc_size(code) == 128


def test_all_exports():
    """Ensure all exported names start with IO or _io."""
    for name in ioctl.__all__:
        assert name.startswith("IO") or name.startswith("_io")
