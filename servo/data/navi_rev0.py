# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# generates navi_rev0.py
revs = [0]
inas = [
# drvname      slv        name                    nom      sense  mux     is_calib
  ('pac1934',  '0x10:0',  'ppvar_sys',            7.800,   0.01,  'rem',  True),  #R533
  ('pac1934',  '0x10:1',  'pp3300_z1',            3.300,   0.01,  'rem',  True),  #R203
  ('pac1934',  '0x10:2',  'pp3700_s5',            3.700,   0.01,  'rem',  True),  #R219
  ('pac1934',  '0x10:3',  'pp5000_z1',            5.000,   0.01,  'rem',  True),  #R205
  ('pac1934',  '0x11:0',  'pp3300_hub_in_z1',     3.300,   0.02,  'rem',  True),  #RS14
  ('pac1934',  '0x11:1',  'pp3300_wlan_s3',       3.300,   0.02,  'rem',  True),  #RS8
  ('pac1934',  '0x11:2',  'pp3300_ec_z1',         3.300,   0.02,  'rem',  True),  #RS2
  ('pac1934',  '0x11:3',  'pp1800_vio18_s3',      1.800,   0.02,  'rem',  True),  #RS20
]
