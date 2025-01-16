# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# generates skywalker_rev0.py
revs = [0]
inas = [
# drvname      slv        name                    nom      sense  mux     is_calib
  ('pac1954',  '0x10:0',  'ppvar_sys',            13.200,  0.01,  'rem',  True),  #R533
  ('pac1954',  '0x10:1',  'ppvar_vbus_in',        15.000,  0.01,  'rem',  True),  #R501
  ('pac1954',  '0x10:2',  'ppvar_batt_chg',       13.200,  0.01,  'rem',  True),  #R1667
  ('pac1954',  '0x10:3',  'ppvar_batt_dischg',    13.200,  0.01,  'rem',  True),  #R1667
  ('pac1954',  '0x11:0',  'pp3300_z1',            3.300,   0.01,  'rem',  True),  #R203
  ('pac1954',  '0x11:1',  'pp5000_z1',            5.000,   0.01,  'rem',  True),  #R205
  ('pac1954',  '0x11:2',  'pp3700_s5',            3.700,   0.01,  'rem',  True),  #R219
  ('pac1954',  '0x11:3',  'pp1800_vio18_s3',      1.800,   0.02,  'rem',  True),  #RS33
  ('pac1954',  '0x12:0',  'ppvar_dvdd_gpu',       0.750,   0.002, 'rem',  True),  #RS45
  ('pac1954',  '0x12:1',  'ppvar_dvdd_core',      0.750,   0.002, 'rem',  True),  #RS31
  ('pac1954',  '0x12:2',  'ppvar_dvdd_apu',       0.750,   0.002, 'rem',  True),  #RS32
  ('pac1954',  '0x12:3',  'ppvar_dvdd_proc_l',    0.750,   0.002, 'rem',  True),  #RS40
  ('pac1954',  '0x13:0',  'pp0750_dvdd_sram_core',0.750,   0.002, 'rem',  True),  #RS30
  ('pac1954',  '0x13:1',  'pp3700_proc_b_in',     3.700,   0.01,  'rem',  True),  #RS38
  ('pac1954',  '0x13:2',  'pp3700_proc_b_t_in',   3.700,   0.01,  'rem',  True),  #RS29
  ('pac1954',  '0x13:3',  'pp1800_ec_s3',         1.800,   0.02,  'rem',  True),  #RS41
  ('pac1954',  '0x14:0',  'pp1800_ec_z1',         1.800,   0.02,  'rem',  True),  #RS42
  ('pac1954',  '0x14:1',  'pp3300_ec_z1',         3.300,   0.02,  'rem',  True),  #RS35
  ('pac1954',  '0x14:2',  'pp1800_gsc_z1',        1.800,   0.02,  'rem',  True),  #RS36
  ('pac1954',  '0x14:3',  'pp3300_gsc_z1',        3.300,   0.02,  'rem',  True),  #RS37
  ('pac1954',  '0x15:0',  'pp3300_c0_sub_z1',     3.300,   0.02,  'rem',  True),  #RS43
  ('pac1954',  '0x15:1',  'pp3300_c1_sub_z1',     3.300,   0.02,  'rem',  True),  #RS44
  ('pac1954',  '0x15:2',  'pp3300_fp_x',          3.300,   0.02,  'rem',  True),  #RS15
  ('pac1954',  '0x15:3',  'pp1800_fp_x',          1.800,   0.02,  'rem',  True),  #RS16
  ('pac1954',  '0x16:0',  'pp3300_edp_x',         3.300,   0.02,  'rem',  True),  #RS4
  ('pac1954',  '0x16:1',  'ppvar_edp_bl_s3',      13.200,  0.02,  'rem',  True),  #RS24
  ('pac1954',  '0x16:2',  'pp3300_tchscr_x',      3.300,   0.02,  'rem',  True),  #RS5
  ('pac1954',  '0x16:3',  'pp3300_tchpad_s3',     3.300,   0.02,  'rem',  True),  #RS25
  ('pac1954',  '0x17:0',  'pp3300_hub_s3',        3.300,   0.02,  'rem',  True),  #RS34
  ('pac1954',  '0x17:1',  'pp3300_wlan_s3',       3.300,   0.02,  'rem',  True),  #RS8
  ('pac1954',  '0x17:2',  'pp3300_wwan_x',        3.300,   0.02,  'rem',  True),  #RS39
  ('pac1954',  '0x17:3',  'pp3300_ucam_x',        3.300,   0.02,  'rem',  True),  #RS6
]
