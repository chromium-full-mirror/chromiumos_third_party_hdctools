# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Created using go/sense-point-template

config_type='servod'

inas = [
    ('pac1934', '0x10:0', 'pp0600_vddq',       0.6 , 0.005, 'rem', True), # R673
#   ('pac1934', '0x10:1', 'unused',            0.0 , 0.0  , 'rem', True), #
    ('pac1934', '0x10:2', 'pp1800_soc_s5',     1.8 , 0.005, 'rem', True), # R108
    ('pac1934', '0x10:3', 'pp3300_soc_s5',     3.3 , 0.1  , 'rem', True), # R109
    ('pac1934', '0x11:0', 'ppvar_sys_in_aux', 15.4 , 0.01 , 'rem', True), # R461
    ('pac1934', '0x11:1', 'ppvar_sys_edp',    15.4 , 0.3  , 'rem', True), # R313
    ('pac1934', '0x11:2', 'pp3300_edp_x',      3.3 , 0.005, 'rem', True), # R670
    ('pac1934', '0x11:3', 'pp0950_gpu_x',      0.95, 0.005, 'rem', True), # R2300
#  Address 0x12-0x15 is skipped
    ('pac1934', '0x16:0', 'pp5000_fan2_x',     5.0 , 0.1  , 'rem', True), # R4001
    ('pac1934', '0x16:1', 'pp5000_z1',         5.0 , 0.005, 'rem', True), # R436
    ('pac1934', '0x16:2', 'pp3300_gpu_x',      3.3 , 0.003, 'rem', True), # R421
    ('pac1934', '0x16:3', 'pp1200_s5',         1.2 , 0.01 , 'rem', True), # R746
    ('pac1934', '0x17:0', 'pp5000_fan1_x',     5.0 , 0.1  , 'rem', True), # R4000
    ('pac1934', '0x17:1', 'pp3300_wlan_x',     3.3 , 0.01 , 'rem', True), # R327
    ('pac1934', '0x17:2', 'pp3300_ec_z2',      3.3 , 32.4 , 'rem', True), # R330
    ('pac1934', '0x17:3', 'pp1800_gpu_x',      1.8 , 0.005, 'rem', True), # R2301
    ('pac1934', '0x18:0', 'pp3300_gsc_z2',     3.3 , 1.0  , 'rem', True), # R1008
    ('pac1934', '0x18:1', 'pp1100_dram',       1.1 , 0.001, 'rem', True), # R672
#   ('pac1934', '0x18:2', 'unused',            0.0 , 0.0  , 'rem', True), #
    ('pac1934', '0x18:3', 'ppvar_sys_sd',     15.4 , 0.03 , 'rem', True), # R799
    ('pac1934', '0x19:0', 'pp3300_z1',         3.3 , 0.3  , 'rem', True), # R656
    ('pac1934', '0x19:1', 'pp3300_usb_z1',     3.3 , 0.3  , 'rem', True), # R668
    ('pac1934', '0x19:2', 'pp1800_dram',       1.8 , 0.01 , 'rem', True), # R685
    ('pac1934', '0x19:3', 'pp3300_ssd_x',      3.3 , 0.01 , 'rem', True), # R289
]
