# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

config_type = 'sweetberry'

inas = [
    ('ina231', (1,3),   'ppvar_vccin_aux',      1.1, 0.002, 'j2', True),
    ('ina231', (2,4),   'pp1800_soc_s5',        1.8, 0.010, 'j2', True),
    ('ina231', (6,8),   'pp3300_soc_s5',        3.3, 0.010, 'j2', True),
    ('ina231', (7,9),   'pp3300_rtc_z2',        3.3, 0.010, 'j2', True),
    ('ina231', (11,13), 'pp1800_dram',          1.8, 0.010, 'j2', True),
    ('ina231', (12,14), 'pp1100_dram',          1.1, 0.002, 'j2', True),
    ('ina231', (16,18), 'pp0600_vddq',          0.6, 0.005, 'j2', True),
    ('ina231', (17,19), 'pp3300_ssd_x',         3.3, 0.010, 'j2', True),
    ('ina231', (21,23), 'pp3300_wlan_x',        3.3, 0.010, 'j2', True),
    ('ina231', (22,24), 'ppvar_wwan_x',         5.0, 0.010, 'j2', True),
    ('ina231', (26,28), 'pp1800_sensor_s5',     1.8, 0.100, 'j2', True),
    ('ina231', (27,29), 'pp5000_hdmi_x',        5.0, 0.010, 'j2', True),
    ('ina231', (31,33), 'pp3300_hdmi_x',        3.3, 0.020, 'j2', True),
    ('ina231', (32,34), 'pp3300_ec_z1',         3.3, 2.200, 'j2', True),
    ('ina231', (36,38), 'pp3300_ec_z2',         3.3, 0.010, 'j2', True),
    ('ina231', (37,39), 'pp1800_ec_z1',         1.8, 2.200, 'j2', True),
    ('ina231', (1,3),   'ppvar_ec_vref_peci',   5.0, 0.010, 'j3', True),
    ('ina231', (2,4),   'ppvar_b',              5.0, 0.100, 'j3', True),
    ('ina231', (6,8),   'pp3300_edp_x' ,        3.3, 0.020, 'j3', True),
    ('ina231', (7,9),   'pp3300_sensor_s5' ,    3.3, 0.100, 'j3', True),
    ('ina231', (11,13), 'pp3300_tchscr_x' ,     3.3, 0.020, 'j3', True),
    ('ina231', (12,14), 'pp5000_tchpad_x' ,     5.0, 0.010, 'j3', True),
    ('ina231', (16,18), 'pp3300_tchpad_x' ,     3.3, 0.020, 'j3', True),
    ('ina231', (17,19), 'ppvar_kb_bl' ,         5.0, 0.100, 'j3', True),
    ('ina231', (21,23), 'pp5000_fan_x' ,        5.0, 0.100, 'j3', True),
    ('ina231', (22,24), 'pp1800_s5',            1.8, 0.005, 'j3', True),
    ('ina231', (26,28), 'pp3300_s5',            3.3, 0.005, 'j3', True),
    ('ina231', (27,29), 'pp5000_z1',            5.0, 0.010, 'j3', True),
    ('ina231', (31,33), 'ppvar_sys',            5.0, 0.010, 'j3', True),
    ('ina231', (32,34), 'pp3300_fp_x',          3.3, 0.500, 'j3', True),
    ('ina231', (36,38), 'pp3300_gsc_z2',        3.3, 0.010, 'j3', True),
]
