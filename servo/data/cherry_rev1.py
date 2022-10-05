# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

inas = [
    ('ina231', '0x40', 'ppvar_vbus_in',   20.0, 0.020, 'rem', True), # RS1
    ('ina231', '0x41', 'ppvar_batt',      7.7,  0.010, 'rem', True), # RS15
    ('ina231', '0x42', 'pp4200_z2',       4.2,  0.010, 'rem', True), # RS16
    ('ina231', '0x43', 'ppvar_bl',        7.7,  0.010, 'rem', True), # RS10
    ('ina231', '0x44', 'pp3300_z2',       3.3,  0.010, 'rem', True), # RS6
    ('ina231', '0x45', 'pp5000_s5',       5.0,  0.010, 'rem', True), # RS7
    ('ina231', '0x46', 'pp4200_gpu_vin',  4.2,  0.010, 'rem', True), # R207
    ('ina231', '0x47', 'ppvar_sys',       7.7,  0.010, 'rem', True), # RS4
    ('ina231', '0x48', 'pp1800_vio18_s3', 1.8,  0.020, 'rem', True), # RS9
    ('ina231', '0x49', 'pp4200_core_vin', 4.2,  0.010, 'rem', True), # R125
    ('ina231', '0x4a', 'pp4200_bc_vin',   4.2,  0.010, 'rem', True), # R227
    ('ina231', '0x4b', 'pp4200_lc_vin',   4.2,  0.010, 'rem', True), # R880
    ('ina231', '0x4c', 'pp3300_wlan_x',   3.3,  0.020, 'rem', True), # RS14
    ('ina231', '0x4d', 'pp3300_s3',       3.3,  0.020, 'rem', True), # RS8
    ('ina231', '0x4e', 'pp3300_ec_z2',    3.3,  0.020, 'rem', True), # RS18
    ('ina231', '0x4f', 'pp3300_lcm_x',    3.3,  0.020, 'rem', True), # RS5
]
# _x suffixed rails can be independently controlled out of power states.
