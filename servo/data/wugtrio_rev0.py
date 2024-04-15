# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Wugtrio rev0 on-board adc map"""

# generates wugtrio_rev0.xml
# https://docs.google.com/spreadsheets/d/1CCIl9ASTo-Jnl39P1KIHGsl489LDAt_af2ZVUXyMEfM/edit?resourcekey=0-ONMVTS6LLdC-bwhLDgDuPQ#gid=0
revs = [0]

# thest devices are [ina231] devices

inas = [
# drvname      slv      name                        nom     sense   mux     is_calib
  ('ina231',   '0x40',  'ppvar_vbus_in',            20.000, 0.01,   'rem',  True),  # RS4
  ('ina231',   '0x41',  'ppvar_sys',                8.850,  0.005,  'rem',  True),  # R264
  ('ina231',   '0x42',  'ppvar_batt_dischg',        8.850,  0.005,  'rem',  True),  # RS15
  ('ina231',   '0x43',  'pp4200_s5',                4.200,  0.005,  'rem',  True),  # R535
  ('ina231',   '0x44',  'pp3300_z1',                3.300,  0.01,   'rem',  True),  # R533
  ('ina231',   '0x45',  'pp5000_z1',                5.000,  0.005,  'rem',  True),  # R546
  ('ina231',   '0x46',  'pp3300_ec_z1',             3.300,  0.02,   'rem',  True),  # RS16
  ('ina231',   '0x47',  'pp3300_gsc_z1',            3.300,  0.02,   'rem',  True),  # RS19
  ('ina231',   '0x48',  'pp1800_vio18_s3',          1.800,  0.02,   'rem',  True),  # RS11
  ('ina231',   '0x49',  'pp1800_gsc_z1',            1.800,  0.02,   'rem',  True),  # RS1
  ('ina231',   '0x4A',  'pp3300_wlan',              3.300,  0.02,   'rem',  True),  # RS24
  ('ina231',   '0x4B',  'pp3300_hub',               3.300,  0.02,   'rem',  True),  # RS3001
  ('ina231',   '0x4C',  'pp5000_base',              5.000,  0.02,   'rem',  True),  # RS3801
  ('ina231',   '0x4D',  'ppvar_mipi_bl_vin',        8.850,  0.02,   'rem',  True),  # RS2503
  ('ina231',   '0x4E',  'pp5000_mipi_disp_z1',      3.300,  0.02,   'rem',  True),  # RS3802
  ('ina231',   '0x4F',  'pp3300_mipi_disp_tchscr',  3.300,  0.02,   'rem',  True),  # RS2501
]
