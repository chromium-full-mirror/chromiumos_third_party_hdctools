# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

config_type='sweetberry'

inas = [
    ('ina231', '0x40:3', 'ppvar_bat_r',    12.0 , 0.01 , 'j2', True), # Across battery
    ('ina231', '0x40:1', 'ppvar_bat',      12.0 , 0.01 , 'j2', True), # R172_33
    ('ina231', '0x40:2', 'pp3300_ec_stby',  3.3 , 0.1  , 'j2', True), # R297_FF
    ('ina231', '0x40:0', 'pp3300_ec',       3.3 , 0.1  , 'j2', True), # R398_FF
    ('ina231', '0x41:3', 'pp1800_ec',       1.8 , 0.1  , 'j2', True), # R330
    ('ina231', '0x41:1', 'pp3300_h1',       3.3 , 0.1  , 'j2', True), # R296_FF
    ('ina231', '0x41:2', 'pp1800_h1',       1.8 , 0.1  , 'j2', True), # R314
    ('ina231', '0x41:0', 'pp1800_sensors',  1.8 , 0.1  , 'j2', True), # R43
    ('ina231', '0x42:3', 'pp3300_pd_a',     3.3 , 0.1  , 'j2', True), # R397_FF
    ('ina231', '0x42:1', 'pp3300_a_r',      3.3 , 0.01 , 'j2', True), # R4699
    ('ina231', '0x42:2', 'src_vph_pwr_r',   3.3 , 0.01 , 'j2', True), # R321
    ('ina231', '0x42:0', 'pp5000_a',        5.0 , 0.01 , 'j2', True), # R4689
    ('ina231', '0x43:3', 'pp3300_hub',      3.3 , 0.01 , 'j2', True), # R376
    ('ina231', '0x43:1', 'pp3300_tcpc_c0',  3.3 , 0.1  , 'j2', True), # R138
    ('ina231', '0x43:2', 'pp1200_tcpc_c0',  1.2 , 0.1  , 'j2', True), # R268
    ('ina231', '0x44:3', 'pp864_s4c',       0.86, 0.02 , 'j3', True), # R195
    ('ina231', '0x44:1', 'pp870_s5c_s6c',   0.87, 0.02 , 'j3', True), # R193
    ('ina231', '0x44:2', 'pp868_s2a',       0.87, 0.02 , 'j3', True), # R197
    ('ina231', '0x44:0', 'pp1800_l10a',     1.8 , 0.3  , 'j3', True), # R209
    ('ina231', '0x45:3', 'pp1125_s1a',      1.13, 0.02 , 'j3', True), # R1
    ('ina231', '0x45:1', 'pp912_s3a',       0.91, 0.02 , 'j3', True), # R200
    ('ina231', '0x45:2', 'pp600_l6a',       0.6 , 0.01 , 'j3', True), # R377
    ('ina231', '0x45:0', 'pp800_l9a',       0.6 , 0.05 , 'j3', True), # R205
    ('ina231', '0x46:3', 'pp3300_l10c',     3.3 , 0.1  , 'j3', True), # R216
    ('ina231', '0x46:1', 'pp3300_l11c',     3.3 , 0.1  , 'j3', True), # R214
    ('ina231', '0x46:2', 'pp864_s7c',       0.86, 0.02 , 'j3', True), # R194
    ('ina231', '0x46:0', 'lcd_bl_vout',    12.0 , 0.01 , 'j3', True), # R227
]
