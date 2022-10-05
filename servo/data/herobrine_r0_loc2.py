# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

config_type='sweetberry'

# Optimized for measurement in S5 / G3 and lower power states.
inas = [
    ('ina231', (7,13),    'pp1800_main_bd',         1.8, 0.010, 'android', True), # R513
    ('ina231', (9,15),    'pp3300_ec_rtc',          3.3, 10.00, 'android', True), # R164
    ('ina231', (11,17),   'pp3300_mcu',             3.3, 0.050, 'android', True), # R1
    ('ina231', (6,12),    'pp3300_pd_s5_c0',        3.3, 0.500, 'android', True), # R138, 0.010ohm originally
    ('ina231', (19,25),   'pp3300_hub',             3.3, 0.010, 'android', True), # R376
    ('ina231', (20,26),   'pp1200_pd_s5',           1.2, 0.500, 'android', True), # R372, 0.010ohm originally
    ('ina231', (22,28),   'pp1200_tcpc_c0',         1.2, 0.500, 'android', True), # R268, 0.010ohm originally
    ('ina231', (23,29),   'pp3300_codec',           3.3, 0.010, 'android', True), # R526_40
    ('ina231', (24,30),   'src_vph_pwr',            3.9, 0.002, 'android', True), # R321
    ('ina231', (32,38),   'pp3300_audio',           3.3, 0.200, 'android', True), # R42, 0.050ohm originally
    ('ina231', (41,47),   'ppvar_batt_r_sb',        8.8, 0.010, 'android', True), # R172_33
    ('ina231', (36,42),   'pp3300_pd_s5_rb',        3.3, 0.100, 'android', True), # R182, 0.002ohm originally
    ('ina231', (49,55),   'pp3300_ec_stby',         3.3, 0.100, 'android', True), # R297_FF, 0.010ohm originally
    ('ina231', (51,57),   'pp3300_pd_s5',           3.3, 0.200, 'android', True), # R397_FF, 0.010ohm originally
    ('ina231', (53,59),   'pp3300_gsc',             3.3, 0.200, 'android', True), # R296_FF, 0.010ohm originally
    ('ina231', (67,73),   'pp1800_gsc',             1.8, 0.200, 'android', True), # R314, 0.010ohm originally
    ('ina231', (62,68),   'ppvar_sys_pp3300_z1_in', 8.8, 0.100, 'android', True), # R175, 0.002ohm originally
    ('ina231', (71,77),   'pp3300_ec_main',         3.3, 0.100, 'android', True), # R398_FF, 0.010ohm originally
    ('ina231', (81,87),   'pp1800_ec',              1.8, 2.200, 'android', True), # R7
    ('ina231', (83,89),   'pp3300_ec',              3.3, 2.200, 'android', True), # R24
    ('ina231', (97,103),  'pp3300_pen',             3.3, 0.050, 'android', True), # R561_45
    ('ina231', (92,98),   'pp1800_sensors',         1.8, 0.500, 'android', True), # R393_FF, 0.010ohm originally
    ('ina231', (99,105),  'pp1800_pen',             1.8, 0.050, 'android', True), # R546_45
    ('ina231', (109,115), 'pp3300_tp',              3.3, 0.500, 'android', True), # R371
    ('ina231', (110,116), 'pp1800_alc5682',         1.8, 0.010, 'android', True), # R508_40
    ('ina231', (111,117), 'pp5000_s3',              5.0, 0.100, 'android', True), # R4689, 0.002ohm originally
    ('ina231', (112,118), 'pp3300_fps',             3.3, 0.500, 'android', True), # R248
    ('ina231', (114,120), 'pp1800_fp',              1.8, 0.500, 'android', True), # R249
]
