# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import ctypes

from servo.utils.linux import i2c


def test_i2c_constants():
    """Test that all expected constants are defined and have correct type."""
    assert i2c.I2C_M_RD == 0x0001
    assert i2c.I2C_M_STOP == 0x8000
    assert i2c.I2C_FUNC_I2C == 0x00000001
    assert i2c.I2C_FUNC_SMBUS_EMUL > 0


def test_i2c_msg_struct():
    """Test the I2cMsg struct."""
    msg = i2c.I2cMsg()
    assert msg.addr == 0
    assert msg.flags == 0
    assert msg.len == 0
    # test buffer assignment
    buf_array = (ctypes.c_uint8 * 5)()
    msg.buf = ctypes.cast(buf_array, ctypes.POINTER(ctypes.c_uint8))
    msg.len = 5
    msg.flags = i2c.I2C_M_RD
    assert msg.flags == 0x0001


def test_all_exports():
    """Ensure all exported names start with I2C_ or i2c_."""
    for name in i2c.__all__:
        assert name.startswith("I2C_") or name.startswith("i2c_")
