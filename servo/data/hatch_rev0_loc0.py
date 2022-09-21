# Copyright 2019 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

config_type='sweetberry'

inas = [
    ('ina231', (1,3),   'pp3300_g',       3.3, 0.005, 'j3', True), # PR17
    ('ina231', (2,4),   'pp3300_h1',      3.3, 0.500, 'j3', True), # R423
    ('ina231', (6,8),   'pp3300_ec',      3.3, 0.500, 'j3', True), # R415
    ('ina231', (7,9),   'pp3300_tcpc',    3.3, 0.010, 'j3', True), # R416
    ('ina231', (11,13), 'pp3300_hp_vbat', 3.3, 0.010, 'j3', True), # RA7, connect to pp3300_g
    ('ina231', (12,14), 'pp3300_a',       3.3, 0.020, 'j3', True), # R203
    ('ina231', (16,18), 'pp3300_a_soc',   3.3, 0.100, 'j3', True), # R410
    ('ina231', (17,19), 'pp3300_a_wlan',  3.3, 0.020, 'j3', True), # R409
    ('ina231', (21,23), 'pp3300_a_ssd',   3.3, 0.020, 'j3', True), # R411
    ('ina231', (22,24), 'ppvar_bat',      7.6, 0.010, 'j3', True), # PRB11
    ('ina231', (26,28), 'pp3300_g_in',    7.6, 0.020, 'j3', True), # PR10
]
