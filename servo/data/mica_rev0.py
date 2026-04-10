# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""mica rev0 on-board adc map"""

# generates mica_rev0.xml
revs = [0]

# test devices are [pac1954] devices
inas = [
#  drvname       addr:port  name                        nom     sense   mux    is_calib
  ('pac1954',   '0x10:0',  'PPVAR_BATT',               12.00,  0.005,  'rem',True),  # RS4401
  ('pac1954',   '0x10:1',  'BL_PWR',                   12.00,  0.010,  'rem',True),  # RS3200
  ('pac1954',   '0x10:2',  'PP3800_VPH_PWR_A_S5',      3.800,  0.010,  'rem',True),  # RS4901
  ('pac1954',   '0x10:3',  'PP3800_VPH_PWR_B_S5',      3.800,  0.010,  'rem',True),  # RS5101
  ('pac1954',   '0x11:0',  'PP3300_Z1',                3.300,  0.010,  'rem',True),  # RS4501
  ('pac1954',   '0x11:1',  'PP5000_S5',                5.150,  0.010,  'rem',True),  # RS4512
  ('pac1954',   '0x11:2',  'PP3300_GSC_Z1',            3.300,  0.020,  'rem',True),  # R1902
  ('pac1954',   '0x11:3',  'PP3300_EC_Z1',             3.300,  0.020,  'rem',True),  # R2301
  ('pac1954',   '0x12:0',  'PP3300_TCHPAD_S3',         3.300,  0.020,  'rem',True),  # R3606
  ('pac1954',   '0x12:1',  'PP3300_WLAN_X',            3.300,  0.020,  'rem',True),  # RS2801
  ('pac1954',   '0x12:2',  'PP3300_NVME_X',            3.300,  0.020,  'rem',True),  # R2402
  ('pac1954',   '0x12:3',  'PP3300_TCHSCR_X',          3.300,  0.020,  'rem',True),  # RS3202
  ('pac1954',   '0x13:0',  'PP3300_UCAM_X',            3.300,  0.020,  'rem',True),  # RS3300
  ('pac1954',   '0x13:1',  'PP3300_FP_Z1_X',           3.300,  0.020,  'rem',True),  # RS3500
  ('pac1954',   '0x13:2',  'PP3300_DISP_X',            3.300,  0.020,  'rem',True),  # RS3201
  ('pac1954',   '0x13:3',  'PP0900_RT_X',              0.900,  0.010,  'rem',True),  # RS4000
  ('pac1954',   '0x14:0',  'NA',                       0.000,  0.000,  'rem',True),  # NA
  ('pac1954',   '0x14:1',  'GFX_VIN_V',                3.800,  0.002,  'rem',True),  # RS5900
  ('pac1954',   '0x14:2',  'APC0_VIN_V',               3.800,  0.002,  'rem',True),  # RS5800
  ('pac1954',   '0x14:3',  'APC1_VIN_V',               3.800,  0.002,  'rem',True),  # RS6000
  ('pac1954',   '0x15:0',  'PP1200_L12B_S3',           1.200,  0.020,  'rem',True),  # R5404
  ('pac1954',   '0x15:1',  'PP1800_L15B_S3',           1.800,  0.020,  'rem',True),  # R5411
  ('pac1954',   '0x15:2',  'PP0730_S12C_S0',           0.730,  0.002,  'rem',True),  # R5500
  ('pac1954',   '0x15:3',  'PP0710_S78C_S0',           0.710,  0.002,  'rem',True),  # R5510
  ('pac1954',   '0x16:0',  'PP1800_L1I_S3',            1.800,  0.002,  'rem',True),  # R4604
  ('pac1954',   '0x16:1',  'PP0900_VDD2L_MEM_S3',      0.900,  0.010,  'rem',True),  # RS4605
  ('pac1954',   '0x16:2',  'PP1080_S23I_S3',           1.080,  0.005,  'rem',True),  # R4606
  ('pac1954',   '0x16:3',  'PP0800_S56I_S0',           0.800,  0.005,  'rem',True),  # R4608
  ('pac1954',   '0x17:0',  'PP0500_VDDQ_MEM_S0',       0.500,  0.010,  'rem',True),  # RS5801
  ('pac1954',   '0x17:1',  'PP0730_S12J_S3',           0.730,  0.002,  'rem',True),  # R4701
  ('pac1954',   '0x17:2',  'PP0800_S34J_S0',           0.800,  0.002,  'rem',True),  # R4702
  ('pac1954',   '0x17:3',  'PP0730_S678J_S0',          0.730,  0.002,  'rem',True),  # R4703
]
