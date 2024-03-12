# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Kyogre rev0 on-board adc map"""

# Generates kyogre_rev0.xml
revs = [0]

# INA231 (1-channel/i2c address) are used

inas = [
#   drvname,   slv,     name,               nom,   sense, mux,   is_calib
   ('ina231',  '0x40',  'ppvar_batt',       9.0,   0.01,  'rem', True),  # RS18
   ('ina231',  '0x41',  'ppvar_sys'  ,      9.0,   0.01,  'rem', True),  # RSV1303
   ('ina231',  '0x42',  'ppvar_vbus_in',    15.0,  0.01,  'rem', True),  # RSV1301
   ('ina231',  '0x43',  'pp5000_z2',        5.0,   0.01,  'rem', True),  # RSV1201
   ('ina231',  '0x44',  'pp4200_z2',        4.2,   0.01,  'rem', True),  # RSV1201
   ('ina231',  '0x45',  'pp3300_z2',        3.3,   0.01,  'rem', True),  # RSV1101
   ('ina231',  '0x46',  'pp3300_gsc_z2',    3.3,   0.02,  'rem', True),  # RS10
   ('ina231',  '0x47',  'pp1800_gsc_z2',    1.8,   0.02,  'rem', True),  # RS9
   ('ina231',  '0x48',  'pp3300_ec_z2',     3.3,   2.2,   'rem', True),  # R352
   ('ina231',  '0x49',  'pp3300_hub',       3.3,   0.02,  'rem', True),  # RS19
   ('ina231',  '0x4a',  'pp3300_c0_mux',    3.3,   0.02,  'rem', True),  # RS16
   ('ina231',  '0x4b',  'pp3300_disp',      3.3,   0.02,  'rem', True),  # RS11
   ('ina231',  '0x4c',  'pp3300_tchscr',    3.3,   0.02,  'rem', True),  # RS13
   ('ina231',  '0x4d',  'pp1800_vio18_s3',  1.8,   0.01,  'rem', True),  # RS8
   ('ina231',  '0x4e',  'pp3300_wlan',      3.3,   0.02,  'rem', True),  # RS20
   ('ina231',  '0x4f',  'ppvar_bl',         9.0,   0.02,  'rem', True),  # RS12
]
