# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

SERVO_DEVICE_DATA = {
    "servo_v2_r0": (
        (0x18D1, 0x5002),
        ("609600", "629871"),
        "servo_v2_r0.xml",
    ),
    "servo_v2": (
        (0x18D1, 0x5002),
        ("641200", "686203", "730422", "780735", "868534", "875286", "force-v2-lotid"),
        "servo_v2_r1.xml",
    ),
    "servo_v4": (
        (0x18D1, 0x501B),
        (),
        "servo_v4.xml",
    ),
    "servo_v4p1": (
        (0x18D1, 0x520D),
        (),
        "servo_v4p1.xml",
    ),
    "servo_micro": (
        (0x18D1, 0x501A),
        (),
        "servo_micro.xml",
    ),
    "ccd_cr50": (
        (0x18D1, 0x5014),
        (),
        "ccd_cr50.xml",
    ),
    "ccd_gsc": (
        (0x18D1, 0x504A),
        (),
        "ccd_ti50.xml",
    ),
    "ccd_gsc_nt": (
        (0x18D1, 0x5066),
        (),
        "ccd_ti50.xml",
    ),
    "sweetberry": (
        (0x18D1, 0x5020),
        (),
        "sweetberry.xml",
    ),
    "c2d2": (
        (0x18D1, 0x5041),
        (),
        "c2d2.xml",
    ),
    "fluffy": (
        (0x18D1, 0x503B),
        (),
        "fluffy.xml",
    ),
}
