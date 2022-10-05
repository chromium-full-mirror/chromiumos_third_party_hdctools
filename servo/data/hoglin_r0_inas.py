# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# generates hoglin_rev0
revs = [0]

inas = [
    ('ina3221', '0x40:2', 'pp3300_hub',  3.3, 0.010, 'rem', True),  # R2037

    ('ina3221', '0x41:0', 'pp3300_edp',  3.3, 0.010, 'rem', True),  # R3303
    ('ina3221', '0x41:2', 'vreg_edp_bl', 8.5, 0.010, 'rem', True),  # R3509

    ('ina3221', '0x42:0', 'pp1800_h1',   1.8, 0.010, 'rem', True),  # R1624, QSPI FLASH + H1 1.8v
    ('ina3221', '0x42:1', 'pp3300_a',    3.3, 0.010, 'rem', True),  # R1622, eDP + Touch screen + USB HUB 3.3V
    ('ina3221', '0x42:2', 'pp3300_h1',   3.3, 0.010, 'rem', True),  # R1615

    ('ina3221', '0x43:0', 'vph_pwr',     3.3, 0.005, 'rem', True),  # R1410
    ('ina3221', '0x43:1', 'pp1800_ec',   1.8, 0.010, 'rem', True),  # R1619
    ('ina3221', '0x43:2', 'pp3300_ec',   3.3, 0.010, 'rem', True),  # R1623
]
