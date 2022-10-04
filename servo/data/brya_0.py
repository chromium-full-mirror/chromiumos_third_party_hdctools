# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# generates brya_rev0
revs = [0]

inas = [
    ('ina3221', '0x40:0', 'pp3300_edp_dx',  3.3, 0.020, 'rem', True),  # R657
    ('ina3221', '0x40:1', 'pp1100_dram',    1.1, 0.002, 'rem', True),  # R672
    ('ina3221', '0x40:2', 'pp1800_s5',      1.8, 0.005, 'rem', True),  # R467
    ('ina3221', '0x41:0', 'pp3300_fp_x',    3.3, 0.500, 'rem', True),  # R999
    ('ina3221', '0x41:1', 'pp1800_fp_sens', 1.8, 0.500, 'rem', True),  # R632
    ('ina3221', '0x42:0', 'pp5000_z1',      5.0, 0.002, 'rem', True),  # R468
    ('ina3221', '0x42:1', 'pp3300_s5',      3.3, 0.005, 'rem', True),  # R473
    ('ina3221', '0x42:2', 'ppvar_vccin_aux',1.0, 0.002, 'rem', True),  # R494
    ('ina3221', '0x43:1', 'pp3300_z1',      3.3, 0.500, 'rem', True),  # R656
    ('ina3221', '0x43:2', 'pp3300_wlan_x',  3.3, 0.005, 'rem', True),  # R294
]
