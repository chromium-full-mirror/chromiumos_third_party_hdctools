# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

inas = [
#    drvname,    slv,     name,                     nom,   sense, mux,   is_calib
    ('ina3221', '0x41:0', 'PPVAR_PCORE_IN',         0.000, 0.005, 'rem', True), #RS2
    ('ina3221', '0x41:1', 'PPVAR_PCORE_SOC',        0.000, 0.01,  'rem', True), #RS1
    ('ina3221', '0x41:2', 'PP0750_VDDP_S0',         0.750, 0.005, 'rem', True), #R913
    ('ina3221', '0x40:0', 'PP3300_S5_VDD_33_S5',    3.300, 0.200, 'rem', True), #R188
    ('ina3221', '0x40:1', 'PP1100_SOC_MEM_S3',      1.100, 0.005, 'rem', True), #R182
    ('ina3221', '0x40:2', 'PP1100_MEM_S3',          1.100, 0.002, 'rem', True), #RS3
    ('ina3221', '0x42:0', 'PP0750_VDDP_S5',         0.750, 0.010, 'rem', True), #R884
    ('ina3221', '0x42:1', 'PP1800_Z1',              1.800, 0.001, 'rem', True), #R853
    ('ina3221', '0x42:2', 'PPVAR_SYS',              0.000, 0.001, 'rem', True), #R748
    ('ina3221', '0x43:0', 'PP3300_Z1',              3.300, 0.002, 'rem', True), #RS4
    ('ina3221', '0x43:1', 'PP5000_S5',              5.000, 0.002, 'rem', True), #RS5
    ('ina3221', '0x43:2', 'PP3300_WLAN_X',          3.300, 0.030, 'rem', True), #R599
    ('ina231', '0x49', 'PP0600_MEM_S3',             0.600, 0.010, 'rem', True), #R833
    ('ina231', '0x4B', 'PP3300_DISP_X',             3.300, 0.020, 'rem', True), #R571
    ('ina231', '0x47', 'PPVAR_BL_PWR',              0.000, 0.100, 'rem', True), #R579
    ('ina231', '0x46', 'PP1800_S0',                 1.800, 0.000, 'rem', False), #R907=0ohm
    ('ina231', '0x4A', 'PP3300_S5',                 3.300, 0.100, 'rem', True), #R887
    ('ina231', '0x4C', 'PP1800_S5',                 1.800, 0.005, 'rem', True), #R886
    ('ina231', '0x45', 'PP3300_SSD_S0',             3.300, 0.020, 'rem', True), #R367
    ('ina231', '0x4E', 'PPVAR_BAT_Q',               0.000, 0.005, 'rem', True), #R745
    ('ina231', '0x48', 'PPVAR_VBUS_IN',             0.000, 0.001, 'rem', True), #R729
    ('ina231', '0x4D', 'PP3300_S0_VDD_33',          3.300, 0.100, 'rem', True), #R185
    ('ina231', '0x4F', 'PP1800_S5_VDD_18_S5',       1.800, 0.010, 'rem', True), #R187
    ('ina231', '0x44', 'PP1800_S0_VDD_18',          1.800, 0.000, 'rem', False), #R186=0ohm
]
