#!/usr/bin/env python3
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

servo_devices = [
    {
        'TYPE': 'miniservo_v1',
        'VID': 0x18d1,
        'PID': 0x5000,
        'LOTIDS': ['001', '540052'],
        'DEFAULT_CONFIG': 'miniservo.xml'
    },
    {
        'TYPE': 'servo_v1',
        'VID': 0x18d1,
        'PID': 0x5001,
        'LOTIDS': ['483881', '498432'],
        'DEFAULT_CONFIG': 'servo.xml'
    },
    {
        'TYPE': 'servo_v2_r0',
        'VID': 0x18d1,
        'PID': 0x5002,
        'LOTIDS': ['609600', '629871'],
        'DEFAULT_CONFIG': 'servo_v2_r0.xml',
        'HUB_SERVO': True,
        'DUT_CONTROLLER': True
    },
    {
        'TYPE': 'servo_v2',
        'VID': 0x18d1,
        'PID': 0x5002,
        'LOTIDS': ['641200', '686203', '730422', '780735', '868534', '875286', 'force-v2-lotid'],
        'DEFAULT_CONFIG': 'servo_v2_r1.xml',
        'HUB_SERVO': True,
        'DUT_CONTROLLER': True
    },
    {
        'TYPE': 'servo_v4',
        'VID': 0x18d1,
        'PID': 0x501b,
        'DEFAULT_CONFIG': 'servo_v4.xml',
        'HUB_SERVO': True
    },
    {
        'TYPE': 'servo_v4p1',
        'VID': 0x18d1,
        'PID': 0x520d,
        'DEFAULT_CONFIG': 'servo_v4p1.xml',
        'HUB_SERVO': True
    },
    {
        'TYPE': 'servo_micro',
        'VID': 0x18d1,
        'PID': 0x501a,
        'DEFAULT_CONFIG': 'servo_micro.xml',
        'DUT_CONTROLLER': True
    },
    {
        'TYPE': 'ccd_cr50',
        'VID': 0x18d1,
        'PID': 0x5014,
        'DEFAULT_CONFIG': 'ccd_cr50.xml',
        'DUT_CONTROLLER': True
    },
    {
        'TYPE': 'ccd_gsc',
        'VID': 0x18d1,
        'PID': 0x504a,
        'DEFAULT_CONFIG': 'ccd_ti50.xml',
        'DUT_CONTROLLER': True
    },
    {
        'TYPE': 'ccd_gsc_nt',
        'VID': 0x18d1,
        'PID': 0x5066,
        'DEFAULT_CONFIG': 'ccd_ti50.xml',
        'DUT_CONTROLLER': True
    },
    {
        'TYPE': 'sweetberry',
        'VID': 0x18d1,
        'PID': 0x5020,
        'DEFAULT_CONFIG': 'sweetberry.xml'
    },
    {
        'TYPE': 'c2d2',
        'VID': 0x18d1,
        'PID': 0x5041,
        'DEFAULT_CONFIG': 'c2d2.xml',
        'DUT_CONTROLLER': True
    },
    {
        'TYPE': 'fluffy',
        'VID': 0x18d1,
        'PID': 0x503b,
        'DEFAULT_CONFIG': 'fluffy.xml'
    },
    {
        'TYPE': 'pacman',
        'VID': 0x18d1,
        'PID': 0x5211,
        'DEFAULT_CONFIG': 'pacman_v1.xml'
    },
    {
        'TYPE': 'ft4232h_generic',
        'VID': 0x0403,
        'PID': 0x6011,
        'DEFAULT_CONFIG': 'single_pac.xml'
    },
    {
        'TYPE': 'maui_v1',
        'VID': 0x18d1,
        'PID': 0x5085,
        'DEFAULT_CONFIG': 'maui_v1.xml',
        'HUB_SERVO': True
    },
    {
        'TYPE': 'maui_v1_proto',
        'VID': 0x0403,
        'PID': 0x6002,
        'DEFAULT_CONFIG': 'maui_v1.xml',
        'HUB_SERVO': True
    }
]


def get_default_config_by_vid_pid(vid, pid):
    """
    Get the DEFAULT_CONFIG value based on the given VID (Vendor ID) and PID (Product ID).

    Args:
        vid (int): Vendor ID of the device.
        pid (int): Product ID of the device.

    Returns:
        str or None: DEFAULT_CONFIG value if a match is found, None otherwise.
    """
    for device in servo_devices:
        if device['VID'] == vid and device['PID'] == pid:
            return device['DEFAULT_CONFIG']
    return ""
