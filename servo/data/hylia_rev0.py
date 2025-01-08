# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# generates hylia_rev0.py
revs = [0]
inas = [
# drvname      slv        name			nom      sense  mux     is_calib
  ('pac1934',  '0x10:0',  'ppvar_sys',          11.700,  0.01,  'rem',  True),  #R533
  ('pac1934',  '0x10:1',  'ppvar_vbus_in',      20.000,  0.01,  'rem',  True),  #R501
  ('pac1934',  '0x10:2',  'ppvar_batt_dischg',  11.700,  0.01,  'rem',  True),  #R531
  ('pac1934',  '0x10:3',  'ppvar_batt_chg',     11.700,  0.01,  'rem',  True),  #R531
  ('pac1934',  '0x11:0',  'pp3700_gpu_in',      4.200,   0.02,  'rem',  True),  #RS21
  ('pac1934',  '0x11:1',  'pp3300_z1',          3.300,   0.005, 'rem',  True),  #R203
  ('pac1934',  '0x11:2',  'pp1800_vio18_s3',    1.800,   0.02,  'rem',  True),  #RS20
  ('pac1934',  '0x11:3',  'pp3700_gpustack_in', 4.200,   0.02,  'rem',  True),  #RS18
  ('pac1934',  '0x12:0',  'pp3300_edp_x',       3.300,   0.02,  'rem',  True),  #RS4
  ('pac1934',  '0x12:1',  'pp3300_tchscr_x',    3.300,   0.02,  'rem',  True),  #RS5
  ('pac1934',  '0x12:2',  'ppvar_edp_bl_s3',    11.700,  0.02,  'rem',  True),  #RS24
  ('pac1934',  '0x12:3',  'pp3300_ucam_x',      3.300,   0.02,  'rem',  True),  #RS6
  ('pac1934',  '0x13:0',  'pp1800_gsc_z1',      1.800,   0.02,  'rem',  True),  #RS12
  ('pac1934',  '0x13:1',  'pp3300_pdc_z1',      3.300,   0.01,  'rem',  True),  #RS26
  ('pac1934',  '0x13:2',  'pp3300_hub_in_s3',   3.300,   0.02,  'rem',  True),  #RS14
  ('pac1934',  '0x13:3',  'pp3700_s5',          4.200,   0.005, 'rem',  True),  #R219
  ('pac1934',  '0x14:0',  'pp3300_sub_z1',      3.300,   0.02,  'rem',  True),  #RS9
  ('pac1934',  '0x14:1',  'pp3300_wlan_s3',     3.300,   0.02,  'rem',  True),  #RS8
  ('pac1934',  '0x14:2',  'pp3300_fp_x',        3.300,   0.02,  'rem',  True),  #RS15
  ('pac1934',  '0x14:3',  'pp1800_fp_x',        1.800,   0.02,  'rem',  True),  #RS16
  ('pac1934',  '0x15:0',  'pp3700_apu_in',      4.200,   0.02,  'rem',  True),  #RS22
  ('pac1934',  '0x15:1',  'pp3700_proc_m_in',   4.200,   0.02,  'rem',  True),  #RS19
  ('pac1934',  '0x15:2',  'pp3700_core_in',     4.200,   0.02,  'rem',  True),  #RS27
  ('pac1934',  '0x15:3',  'pp3700_proc_l_in',   4.200,   0.02,  'rem',  True),  #RS28
  ('pac1934',  '0x16:0',  'pp3300_ec_z1',       3.300,   0.02,  'rem',  True),  #RS2
  ('pac1934',  '0x16:1',  'pp3700_proc_b_in',   4.200,   0.02,  'rem',  True),  #RS30
  ('pac1934',  '0x16:2',  'pp3300_gsc_z1',      3.300,   0.02,  'rem',  True),  #RS13
  ('pac1934',  '0x16:3',  'pp1800_ec_vcc',      1.800,   0.02,  'rem',  True),  #RS3
  ('pac1934',  '0x17:0',  'pp3300_tchpad_x',    3.300,   0.02,  'rem',  True),  #RS25
  ('pac1934',  '0x17:1',  'pp3300_hub2_in_s3',  5.000,   0.02,  'rem',  True),  #RS1651
  ('pac1934',  '0x17:2',  'pp5000_spkr_z1',     5.000,   0.01,  'rem',  True),  #RS11
  ('pac1934',  '0x17:3',  'pp5000_z1',          5.000,   0.005, 'rem',  True),  #R205
]
