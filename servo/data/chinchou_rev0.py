# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""chinchou rev0 on-board adc map"""

# generates chinchou_rev0.xml
revs = [0]

# thest devices are [ina231] devices
inas = [
# drvname      slv      name                        nom     sense   mux     is_calib
  ('ina231',   '0x40',  'ppvar_vbus_in',            20.000, 0.01,   'rem',  True),  # RS19
  ('ina231',   '0x41',  'ppvar_sys',                12.000, 0.01,   'rem',  True),  # RS20
  ('ina231',   '0x42',  'ppvar_batt_dischg',        12.000, 0.01,   'rem',  True),  # RS21
  ('ina231',   '0x43',  'pp4200_z2',                4.200,  0.01,   'rem',  True),  # RS22
  ('ina231',   '0x44',  'pp3300_z2',                3.300,  0.01,   'rem',  True),  # RS23
  ('ina231',   '0x45',  'pp5000_z2',                5.000,  0.01,   'rem',  True),  # RS24
  ('ina231',   '0x46',  'pp3300_ec_z2',             3.300,  0.02,   'rem',  True),  # RS9
  ('ina231',   '0x47',  'pp3300_gsc_z2',            3.300,  0.02,   'rem',  True),  # RS7
  ('ina231',   '0x48',  'pp1800_vio18_s3',          1.800,  0.02,   'rem',  True),  # RS4
  ('ina231',   '0x49',  'pp1800_gsc_z2',            1.800,  0.02,   'rem',  True),  # RS6
  ('ina231',   '0x4A',  'pp3300_wlan',              3.300,  0.02,   'rem',  True),  # RS16
  ('ina231',   '0x4B',  'pp3300_U3_hub',            3.300,  0.02,   'rem',  True),  # RS17
  ('ina231',   '0x4C',  'PP3300_TCHSCR',            3.300,  0.02,   'rem',  True),  # RS18
  ('ina231',   '0x4D',  'PP3300_TCHPAD',            3.300,  0.02,   'rem',  True),  # RS11
  ('ina231',   '0x4E',  'PPVAR_BL',                 12.000, 0.02,   'rem',  True),  # RS10
  ('ina231',   '0x4F',  'PP3300_DISP',              3.300,  0.02,   'rem',  True),  # RS12
]
