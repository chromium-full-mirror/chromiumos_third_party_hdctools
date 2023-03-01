# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Geralt rev0 opt on-board adc map"""

# generates geralt_rev0_opt.xml

# these devices are [ina231] devices
inas = [
# drvname      slv      name                        nom     sense   mux     is_calib
  ('ina231',   '0x40',  'ppvar_vbus_in',            20.000, 0.01,   'rem',  True),  # RS19
  ('ina231',   '0x41',  'ppvar_sys',                8.800,  0.01,   'rem',  True),  # RS20
  ('ina231',   '0x42',  'ppvar_batt_dischg',        8.800,  0.01,   'rem',  True),  # RS21
  ('ina231',   '0x43',  'pp4200_pmic_vin',          4.200,  0.01,   'rem',  True),  # RS22
  ('ina231',   '0x44',  'pp3300_z1',                3.300,  0.01,   'rem',  True),  # RS23
  ('ina231',   '0x45',  'pp5000_z1',                5.000,  0.01,   'rem',  True),  # RS24
  ('ina231',   '0x46',  'pp3300_c0_mux',            3.300,  0.02,   'rem',  True),  # RS28
  ('ina231',   '0x47',  'pp3300_c1_mux',            3.300,  0.02,   'rem',  True),  # RS25
  ('ina231',   '0x48',  'pp1800_ec_z1',             1.800,  0.02,   'rem',  True),  # RS8
  ('ina231',   '0x49',  'pp4200_gpu_vin',           4.200,  0.01,   'rem',  True),  # RS1
  ('ina231',   '0x4A',  'pp4200_core_vin',          4.200,  0.01,   'rem',  True),  # RS3
  ('ina231',   '0x4B',  'pp4200_bc_vin',            4.200,  0.01,   'rem',  True),  # RS5
  ('ina231',   '0x4C',  'pp4200_lc_vin',            4.200,  0.01,   'rem',  True),  # RS2
  ('ina231',   '0x4D',  'ppvar_oled_vin',           8.800,  0.01,   'rem',  True),  # RS14
  ('ina231',   '0x4E',  'pp3300_edp_tchscr',        3.300,  0.02,   'rem',  True),  # RS15
  ('ina231',   '0x4F',  'pp3300_edp_disp',          3.300,  0.02,   'rem',  True),  # RS13
]
