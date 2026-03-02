# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


from servo.utils.linux import i2c_pseudo


def test_i2c_pseudo_constants():
    assert i2c_pseudo.I2CP_CONTROLLER_PATH == b"/dev/i2c-pseudo"
    assert i2c_pseudo.I2CP_IOCTL_CODE == 0x2C


def test_i2c_pseudo_structs():
    # Just basic instantiation to make sure definitions are valid
    out = i2c_pseudo.I2cpIoctlStartOutput()
    assert out.adapter_num == 0

    arg = i2c_pseudo.I2cpIoctlStartArg()
    assert arg.functionality == 0

    counters = i2c_pseudo.I2cpIoctlXferCounters()
    assert counters.controller_replied == 0

    req_out = i2c_pseudo.I2cpIoctlXferReqOutput()
    assert req_out.xfer_id == 0

    req_arg = i2c_pseudo.I2cpIoctlXferReqArg()
    assert req_arg.msgs_len == 0

    reply_arg = i2c_pseudo.I2cpIoctlXferReplyArg()
    assert reply_arg.xfer_id == 0


def test_i2c_pseudo_ioctls():
    assert i2c_pseudo.I2CP_IOCTL_START > 0
    assert i2c_pseudo.I2CP_IOCTL_XFER_REQ > 0
    assert i2c_pseudo.I2CP_IOCTL_XFER_REPLY > 0
    assert i2c_pseudo.I2CP_IOCTL_GET_COUNTERS > 0
    assert i2c_pseudo.I2CP_IOCTL_SHUTDOWN > 0


def test_all_exports():
    """Ensure all exported names start with I2CP_ or i2cp_."""
    for name in i2c_pseudo.__all__:
        assert name.startswith("I2CP_") or name.startswith("i2cp_")
