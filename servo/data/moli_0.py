# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# generates moli_rev0
revs = [0]

inas = [
    ('ina3221', '0x40:0', 'pp1800_s5',      1.8, 0.005,  'rem', True),  # PR5303
    ('ina3221', '0x40:1', 'pp1200_dram',    1.2, 0.002,  'rem', True),  # PR5114
    ('ina3221', '0x40:2', 'pp2500_dram',    2.5, 0.010,  'rem', True),  # PR5110
    ('ina3221', '0x41:1', 'pp3300_ssd_x',   3.3, 0.005,  'rem', True),  # R4032
    ('ina3221', '0x42:0', 'pp5000_s5',      5.0, 0.002,  'rem', True),  # PR4506
    ('ina3221', '0x42:1', 'pp5000_z1',      5.0, 0.002,  'rem', True),  # PR4519
    ('ina3221', '0x42:2', 'pp3300_s5',      3.3, 0.005,  'rem', True),  # PR4543
    ('ina3221', '0x43:0', 'ppvar_vccin_aux',1.0, 0.002,  'rem', True),  # PR5007
    ('ina3221', '0x43:1', 'pp3300_z1',      3.3, 0.010,  'rem', True),  # PR4528
    ('ina3221', '0x43:2', 'pp3300_wlan_x',  3.3, 0.005,  'rem', True),  # R4021
]
