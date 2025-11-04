# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# these devices are pac1934 devices
revs = [0]
inas = [
#  drvname     addr:port   name                     nom         sense       mux   is_calib
  ('pac1934',  '0x10:0',   'PP3800_APC0_VIN',       3.800,      0.002,      'rem',True),  # PR8303
  ('pac1934',  '0x10:1',   'PP3800_APC1_VIN',       3.800,      0.002,      'rem',True),  # PR9570
  ('pac1934',  '0x10:2',   'PP0730_S12J',           0.730,      0.010,      'rem',True),  # PRS5901
  ('pac1934',  '0x10:3',   'PP0500_VDDQ_MEM',       0.500,      0.010,      'rem',True),  # PRS6104
  ('pac1934',  '0x11:0',   'PPVAR_BATT_DISCHG',     8.800,      0.005,      'rem',True),  # PR4603
  ('pac1934',  '0x11:1',   'PP3300_TCHPAD_S3',      3.300,      0.010,      'rem',True),  # RS3601
  ('pac1934',  '0x11:2',   'PP3300_EC_Z1',          3.300,      0.010,      'rem',True),  # RS2202
  ('pac1934',  '0x11:3',   'PP3300_GSC_Z1',         3.300,      0.010,      'rem',True),  # RS1902
  ('pac1934',  '0x12:0',   'PP3800_VPH_A',          3.800,      0.010,      'rem',True),  # PRS5101
  ('pac1934',  '0x12:1',   'PP3300_Z1',             3.300,      0.005,      'rem',True),  # PRS6111
  ('pac1934',  '0x12:2',   'PP5000_S5',             5.000,      0.010,      'rem',True),  # PRS4805
  ('pac1934',  '0x12:3',   'PP3300_NVME_X',         3.300,      0.010,      'rem',True),  # RS2601
  ('pac1934',  '0x13:0',   'PP3300_TCHSCR_X',       3.300,      0.010,      'rem',True),  # RS3202
  ('pac1934',  '0x13:1',   'PP3300_DISP_X',         3.300,      0.010,      'rem',True),  # RS3201
  ('pac1934',  '0x13:2',   'PP0900_RT_X',           0.900,      0.010,      'rem',True),  # R4042
  ('pac1934',  '0x13:3',   'PPVAR_EDP_BL',          8.800,      0.020,      'rem',True),  # R56132
  ('pac1934',  '0x14:0',   'PP3300_FP_S3',          3.300,      0.010,      'rem',True),  # RS3501
  ('pac1934',  '0x14:1',   'PP0900_RT2_X',          0.900,      0.010,      'rem',True),  # R4150
  ('pac1934',  '0x14:2',   'PP3300_UCAM_X',         3.300,      0.010,      'rem',True),  # R2816
  ('pac1934',  '0x14:3',   'PP3300_WLAN_X',         3.300,      0.010,      'rem',True),  # RS2801
  ('pac1934',  '0x15:0',   'PP1200_L12B_S3',        1.200,      0.020,      'rem',True),  # R56133
  ('pac1934',  '0x15:1',   'PP1800_L15B_S3',        1.800,      0.020,      'rem',True),  # R56135
  ('pac1934',  '0x15:2',   'PP3800_GFX_VIN',        3.800,      0.010,      'rem',True),  # PRS6102
  ('pac1934',  '0x15:3',   'PP0800_S56I',           0.800,      0.010,      'rem',True),  # PRS5804
  ('pac1934',  '0x16:0',   'PP3800_VPH_B',          3.800,      0.010,      'rem',True),  # PRS1711
  ('pac1934',  '0x16:1',   'PP1080_S23I',           1.080,      0.010,      'rem',True),  # PRS5802
  ('pac1934',  '0x16:2',   'PP0900_VDD2L_MEM',      0.900,      0.010,      'rem',True),  # PRS5801
  ('pac1934',  '0x16:3',   'PP1800_L1I_S3',         1.800,      0.020,      'rem',True),  # R56134
  ('pac1934',  '0x19:0',   'PP0800_S34J',           0.800,      0.010,      'rem',True),  # PRS5902
  ('pac1934',  '0x19:1',   'PP0730_S12C',           0.730,      0.010,      'rem',True),  # PRS5701
  ('pac1934',  '0x19:2',   'PP0710_S78C',           0.710,      0.010,      'rem',True),  # PRS6110
  ('pac1934',  '0x19:3',   'PP0730_S678J',          0.730,      0.010,      'rem',True),  # PRS5903
]
