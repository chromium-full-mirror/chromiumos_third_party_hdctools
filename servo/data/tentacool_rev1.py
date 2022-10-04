# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""tentacool/tentacruel rev1 on-board adc map"""

# generates tentacool_rev1
revs = [1]

# these devices are ina231 (1-channels/i2c address) devices
inas = [
#    drvname,    slv,        name,                nom,    sense, mux,   is_calib
   ('ina231',   '0x40',     'ppvar_batt_chg',     8.00,   0.010, 'rem', True),  # RS15
   ('ina231',   '0x41',     'ppvar_sys',          8.00,   0.010, 'rem', True),  # R264
   ('ina231',   '0x42',     'ppvar_vbus_in',      20.00,  0.010, 'rem', True),  # RS4
   ('ina231',   '0x43',     'pp5000_z2',          5.000,  0.010, 'rem', True),  # R546
   ('ina231',   '0x44',     'pp4200_z2',          4.200,  0.010, 'rem', True),  # R535
   ('ina231',   '0x45',     'pp3300_z2',          3.300,  0.020, 'rem', True),  # R533
   ('ina231',   '0x46',     'pp3300_gsc_z2',      3.300,  0.020, 'rem', True),  # RS19
   ('ina231',   '0x47',     'pp1800_gsc_z2',      1.800,  0.020, 'rem', True),  # RS18
   ('ina231',   '0x48',     'pp3300_ec_z2',       3.300,  0.020, 'rem', True),  # RS16
   ('ina231',   '0x49',     'pp3300_hub',         3.300,  0.020, 'rem', True),  # RS12
   ('ina231',   '0x4a',     'pp3300_c0_mux',      3.300,  0.020, 'rem', True),  # RS13
   ('ina231',   '0x4b',     'pp3300_c1_mux',      3.300,  0.020, 'rem', True),  # RS25
   ('ina231',   '0x4c',     'pp3300_tchscr',      3.300,  0.020, 'rem', True),  # RS22
   ('ina231',   '0x4d',     'pp1800_vio18_s3',    1.800,  0.020, 'rem', True),  # RS11
   ('ina231',   '0x4e',     'pp3300_wlan',        3.300,  0.020, 'rem', True),  # RS24
   ('ina231',   '0x4f',     'pp3300_lte',         3.300,  0.020, 'rem', True),  # Unused
]
