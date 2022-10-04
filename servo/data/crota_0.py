# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# generates crota_rev0
revs = [0]
config_type='servod'

inas = [
    ('ina3221', '0x40:0', 'PP3300_EDP',     3.3,    0.020, 'rem', True),  # R5519
    ('ina3221', '0x40:1', 'PP1065_DRAM',    1.065,  0.005, 'rem', True),  # PR5112
    ('ina3221', '0x40:2', 'PP1800_S5',      1.8,    0.005, 'rem', True),  # PR5302

    ('ina3221', '0x41:0', 'PP3300_FP',      3.3,    0.020, 'rem', True),  # R3909
    ('ina3221', '0x41:1', 'PP1800_FP',      1.8,    0.020, 'rem', True),  # R3908
    ('ina3221', '0x41:2', 'PP3300_WWAN',    3.3,    0.005, 'rem', True),  # R6211

    ('ina3221', '0x42:0', 'PP5000_Z1',      5.0,    0.002, 'rem', True),  # PR4501
    ('ina3221', '0x42:1', 'PP3300_S5',      3.3,    0.005, 'rem', True),  # PR4502
    ('ina3221', '0x42:2', 'PPVAR_VCCIN_AUX',9.0,    0.002, 'rem', True),  # PR5011

    ('ina3221', '0x43:0', 'PP3300_SSD',     3.3,    0.010, 'rem', True),  # R6303
    ('ina3221', '0x43:1', 'PP3300_Z1',      3.3,    0.200, 'rem', True),  # R3902
    ('ina3221', '0x43:2', 'PP3300_WLAN',    3.3,    0.010, 'rem', True),  # R6108
]
