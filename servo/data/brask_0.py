# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# generates brask_rev0
revs = [0]

inas = [
    ('ina3221', '0x40:0', 'pp1800_s5',      1.8, 0.005,  'rem', True),  # R467
    ('ina3221', '0x40:1', 'pp1200_dram',    1.2, 0.002,  'rem', True),  # R672
    ('ina3221', '0x40:2', 'pp2500_dram',    2.5, 0.010,  'rem', True),  # R11782
    ('ina3221', '0x41:0', 'ppvar_sys_qi',  20.0, 0.010,  'rem', True),  # R11990
    ('ina3221', '0x41:1', 'pp3300_ssd_x',   3.3, 0.005,  'rem', True),  # R221
    ('ina3221', '0x42:0', 'pp5000_s5',      5.0, 0.002,  'rem', True),  # R2002
    ('ina3221', '0x42:1', 'pp5000_z1',      5.0, 0.002,  'rem', True),  # R468
    ('ina3221', '0x42:2', 'pp3300_s5',      3.3, 0.005,  'rem', True),  # R473
    ('ina3221', '0x43:0', 'ppvar_vccin_aux',1.0, 0.0001, 'rem', True),  # R494 is a short
    ('ina3221', '0x43:1', 'pp3300_z1',      3.3, 0.010,  'rem', True),  # R1085
    ('ina3221', '0x43:2', 'pp3300_wlan_x',  3.3, 0.005,  'rem', True),  # R294
]
