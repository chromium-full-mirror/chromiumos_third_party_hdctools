# Copyright 2019 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

config_type='sweetberry'

revs = [6]

inas = [
    ('ina231', '0x40:3', 'pp975_io',        7.7, 0.100, 'j2', True), # R111
    ('ina231', '0x40:1', 'pp850_prim_core', 7.7, 0.100, 'j2', True), # R164
    ('ina231', '0x40:2', 'pp3300_dsw',      3.3, 0.010, 'j2', True), # R513
    ('ina231', '0x40:0', 'pp3300_a',        7.7, 0.010, 'j2', True), # R144
    ('ina231', '0x41:3', 'pp1800_a',        7.7, 0.100, 'j2', True), # R141
    ('ina231', '0x41:1', 'pp1800_u',        7.7, 0.100, 'j2', True), # R161
    ('ina231', '0x41:2', 'pp1200_vddq',     7.7, 0.100, 'j2', True), # R162
    ('ina231', '0x41:0', 'pp1000_a',        7.7, 0.100, 'j2', True), # R163
    ('ina231', '0x42:3', 'pp3300_dx_wlan',  3.3, 0.010, 'j2', True), # R645
    ('ina231', '0x42:1', 'pp3300_dx_edp',   3.3, 0.010, 'j2', True), # F1
    ('ina231', '0x42:2', 'vbat',            7.7, 0.010, 'j2', True), # R226
    ('ina231', '0x42:0', 'ppvar_vcc',       1.0, 0.003, 'j2', True), # L13
    ('ina231', '0x43:3', 'ppvar_sa',        1.0, 0.005, 'j2', True), # L12
    ('ina231', '0x43:1', 'ppvar_gt',        1.0, 0.003, 'j2', True), # L31
    ('ina231', '0x43:2', 'ppvar_bl',        7.7, 0.050, 'j2', True), # U89
    ('ina231', '0x43:0', 'ppvar_vbus_in',  15.0, 0.020, 'j2', True), # R213
]
