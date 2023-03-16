# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

config_type='sweetberry'

inas = [
    ('ina231', (7,13),    'pp1800_alc5682',         1.8, 0.010, 'android', True), # R357, audio DAC
    ('ina231', (9,15),    'pp3300_audio',           3.3, 0.050, 'android', True), # R343, audio DAC
    ('ina231', (4,10),    'pp1200_pd_s5',           1.2, 0.100, 'android', True), # R296, USB C0 C1 TCPC
    ('ina231', (11,17),   'pp1800_prox',            1.8, 0.010, 'android', True), # R27, sar sensor
    ('ina231', (6,12),    'pp3300_fps',             3.3, 0.500, 'android', True), # R34, FP sensor
    ('ina231', (19,25),   'pp3300_codec',           3.3, 0.100, 'android', True), # R345, audio DAC
    ('ina231', (20,26),   'pp3300_fp_mcu',          3.3, 0.500, 'android', True), # R164, FP MCU + sensor
    ('ina231', (21,27),   'pp1200_wf_cam',          1.2, 0.010, 'android', True), # R419, WF cam
    ('ina231', (22,28),   'pp1200_tcpc_c0',         1.2, 0.010, 'android', True), # R171, USB C0 TCPC
    ('ina231', (23,29),   'pp3300_tp',              3.3, 0.500, 'android', True), # R61, TP
    ('ina231', (24,30),   'pp3300_ssd',             3.3, 0.005, 'android', True), # R77, SSD, original 0.010mohm
    ('ina231', (32,38),   'pp2850_wf_cam',          2.85, 0.01, 'android', True), # R405, WF cam
    ('ina231', (39,45),   'pp1800_wf_cam',          1.8, 1.000, 'android', True), # R423, WF cam (rework Left #7)
    ('ina231', (34,40),   'pp3300_hub',             3.3, 0.100, 'android', True), # R102, USB hub + boot flash
    ('ina231', (41,47),   'pp5000_s5',              5.0, 0.100, 'android', True), # R170, speaker amps + kbd bl + USB A0 C0 C1, original 0.005mohm
    ('ina231', (36,42),   'pp3300_pd_s5_rb',        3.3, 0.500, 'android', True), # R88, USB C1
    ('ina231', (49,55),   'ppvar_sys_pp3300_z1_in', 8.8, 0.050, 'android', True), # R484, before voltage change
    ('ina231', (51,57),   'pp2850_wf_vcm',          2.85, 0.01, 'android', True), # R413, WF cam
    ('ina231', (53,59),   'pp3300_ec_r_s5',         3.3, 2.200, 'android', True), # R94, EC
    ('ina231', (67,73),   'src_vph_pwr',            3.9, 0.100, 'android', True), # R375, MB + UF cam
    ('ina231', (62,68),   'pp3300_tcpc_c0',         3.3, 0.500, 'android', True), # R482, USB C0
    ('ina231', (64,70),   'pp1800_sensors_s5',      1.8, 5.100, 'android', True), # R135, lid accel + ALS + gyro
    ('ina231', (71,77),   'pp3300_mipi',            3.3, 0.100, 'android', True), # R391, MIPI display
    ('ina231', (66,72),   'pp1800_ec',              1.8, 2.200, 'android', True), # R109, EC
    ('ina231', (79,85),   'pp1800_mipi',            1.8, 0.100, 'android', True), # R378, MIPI display
    ('ina231', (81,87),   'pp1800_gsc_z1',          1.8, 0.200, 'android', True), # R147, security
    ('ina231', (83,89),   'pp3300_ec_s5',           3.3, 0.100, 'android', True), # R134, EC + EEPROM
    ('ina231', (97,103),  'pp3300_ec_stby_z1',      3.3, 2.000, 'android', True), # R204, RTC + EC + USB C1
    ('ina231', (92,98),   'pp3300_gsc_z1',          3.3, 0.500, 'android', True), # R191, security + spi flash analog mux, original 0.010ohm
    ('ina231', (99,105),  'pp3300_pd_s5',           3.3, 0.050, 'android', True), # R189, USB C0 C1
    ('ina231', (109,115), 'ppvar_batt_r_sb',        8.8, 0.010, 'android', True), # R284 (stuff R277 R290 with 0 ohm)
    ('ina231', (110,116), 'pp3300_rtc_stby',        3.3, 10.00, 'android', True), # R280, RTC
    ('ina231', (111,117), 'pp1800_main_bd',         1.8, 0.010, 'android', True), # R291
    ('ina231', (112,118), 'ppvar_sys_bl',           8.8, 0.010, 'android', True), # R368, screen backlight
    ('ina231', (114,120), 'pp1800_fp',              1.8, 0.500, 'android', True), # R33, FP sensor
]
