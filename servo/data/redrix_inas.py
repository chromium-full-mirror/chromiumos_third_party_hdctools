# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""redrix on-board adc map"""

revs = [ 2 ]

inas = [
#    drvname,   child,      name,             nom,  sense, mux,   is_calib
    ('ina3221', '0x40:0', 'pp5000_z1',        5.00, 0.002, 'rem', True),  # R468
    ('ina3221', '0x40:1', 'pp1100_dram',      1.10, 0.002, 'rem', True),  # R672
    ('ina3221', '0x40:2', 'pp1800_s5',        1.80, 0.005, 'rem', True),  # R467
    ('ina3221', '0x41:0', 'pp3300_fp_x',      3.30, 0.500, 'rem', True),  # R999
    ('ina3221', '0x41:1', 'pp1800_fp_sens',   1.80, 0.500, 'rem', True),  # R632
    ('ina3221', '0x41:2', 'pp3300_wlan_x',    3.30, 0.005, 'rem', True),  # R294
    ('ina3221', '0x42:0', 'pp3300_edp_x',     3.30, 0.020, 'rem', True),  # R657
    ('ina3221', '0x42:1', 'pp3300_s5',        3.30, 0.005, 'rem', True),  # R473
    ('ina3221', '0x42:2', 'ppvar_vccin_aux',  9.00, 0.002, 'rem', True),  # R494
    ('ina3221', '0x43:1', 'pp3300_z1',        3.30, 0.000, 'rem', False), # R656
]
