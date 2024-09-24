# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# generates vell_rev0
# checked against dvt board file

revs = [0]
config_type='servod'

inas = [
    ('ina3221', '0x42:0', 'PP3300_EDP',     3.3,    0.020, 'rem', True),  # R657
    ('ina3221', '0x42:1', 'PP1065_DRAM',    1.065,  0.002, 'rem', True),  # R672
    ('ina3221', '0x42:2', 'PP1800_S5',      1.8,    0.005, 'rem', True),  # R467

    ('ina3221', '0x41:0', 'PP3300_FP',      3.3,    0.500, 'rem', True),  # R632
    ('ina3221', '0x41:1', 'PP1800_FP',      1.8,    0.500, 'rem', True),  # R999
    ('ina3221', '0x41:2', 'PP3300_WWAN',    3.3,    0.005, 'rem', True),  # R294

    ('ina3221', '0x40:0', 'PP5000_Z1',      5.0,    0.002, 'rem', True),  # R468
    ('ina3221', '0x40:1', 'PP3300_S5',      3.3,    0.005, 'rem', True),  # R473
    ('ina3221', '0x40:2', 'PPVAR_VCCIN_AUX',9.0,    0.002, 'rem', True),  # R494

#    ('ina3221', '0x43:0', 'NOCONNECT_0',     3.3,    0.010, 'rem', False),  # TP
#    ('ina3221', '0x43:1', 'PP3300_Z1',      3.3,    0.200, 'rem', False),  # R656
#    ('ina3221', '0x43:2', 'NOCONNECT_2',    3.3,    0.010, 'rem', False),  # TP
]
