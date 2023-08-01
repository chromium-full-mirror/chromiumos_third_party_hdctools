# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# these devices are pac1934 devices
inas = [
#  drvname     addr:port   name                     nom         sense       mux   is_calib
  ('pac1934',  '0x10:0',   'PP0770_SOC_IN',        13.350,      0.010,      'rem',True),  # R380
  ('pac1934',  '0x10:1',   'PP1250_SOC',            1.250,      0.010,      'rem',True),  # R875
  ('pac1934',  '0x10:2',   'PP0770_SOC',            0.770,      0.002,      'rem',True),  # R911
  ('pac1934',  '0x10:3',   'PPVAR_VCCSA_IN',       13.350,      0.010,      'rem',True),  # R379
  ('pac1934',  '0x11:0',   'PP1065_MEM_S3',         1.065,      0.002,      'rem',True),  # R398
  ('pac1934',  '0x11:1',   'PP1065_SOC_S3',         1.065,      0.002,      'rem',True),  # R876
  ('pac1934',  '0x11:2',   'PP1800_MEM_S3',         1.800,      0.010,      'rem',True),  # RS2
  ('pac1934',  '0x11:3',   'PP1800_Z1',             1.800,      0.100,      'rem',True),  # R988
  ('pac1934',  '0x12:0',   'PP3300_WLAN_X',         3.300,      0.010,      'rem',True),  # R873
  ('pac1934',  '0x12:1',   'PP3300_S5',             3.300,      0.005,      'rem',True),  # R590
  ('pac1934',  '0x12:2',   'PP1800_EC_Z1',          1.800,      0.010,      'rem',True),  # R699
  ('pac1934',  '0x12:3',   'PP3300_SSD_X',          3.300,      0.005,      'rem',True),  # R236
  ('pac1934',  '0x13:0',   'PP3300_EDP_X',          3.300,      0.010,      'rem',True),  # R657
  ('pac1934',  '0x13:1',   'PP3300_UCAM_X',         3.300,      0.010,      'rem',True),  # R3519
  ('pac1934',  '0x13:2',   'PP3300_TCHSCR_X',       3.300,      0.010,      'rem',True),  # R658
  ('pac1934',  '0x13:3',   'PP1800_TCHSCR_X',       1.800,      0.010,      'rem',True),  # R990
  ('pac1934',  '0x14:0',   'PP3300_USB_Z1',         3.300,      0.100,      'rem',True),  # R655
  ('pac1934',  '0x14:1',   'PP3300_Z1',             3.300,      0.100,      'rem',True),  # R553
  ('pac1934',  '0x14:2',   'PP3300_Z5',             3.300,      0.010,      'rem',True),  # R1085
  ('pac1934',  '0x14:3',   'PPVAR_SYS',            13.350,      0.001,      'rem',True),  # R905
  ('pac1934',  '0x15:0',   'PP3300_TCHPAD_X',       3.300,      0.010,      'rem',True),  # R15
  ('pac1934',  '0x15:1',   'PP1800_FP_X',           1.800,      0.500,      'rem',True),  # R124
  ('pac1934',  '0x15:2',   'PP3300_FP_X',           3.300,      0.500,      'rem',True),  # R123
  ('pac1934',  '0x15:3',   'PP1800_S5',             1.800,      0.002,      'rem',True),  # R866
  ('pac1934',  '0x17:0',   'PP1500_RTC_Z5',         1.500,      0.500,      'rem',True),  # R832
  ('pac1934',  '0x17:1',   'PP1800_GSC_Z1',         1.800,      0.010,      'rem',True),  # R414
  ('pac1934',  '0x17:2',   'PP3300_EC_Z1',          3.300,      0.010,      'rem',True),  # R700
  ('pac1934',  '0x17:3',   'PP3300_GSC_Z1',         3.300,      0.010,      'rem',True),  # R415
  ('pac1934',  '0x18:1',   'PPVAR_SYS_EDP',        13.350,      0.005,      'rem',True),  # R231
  ('pac1934',  '0x18:2',   'PP5500_HDMI_X',         5.000,      0.010,      'rem',True),  # R695
  ('pac1934',  '0x18:3',   'PP5000_Z1',             5.000,      0.005,      'rem',True),  # R591
  ('pac1934',  '0x19:0',   'PPVAR_VCCSA',           1.520,      0.002,      'rem',True),  # R912
  ('pac1934',  '0x19:1',   'VCCCORE_VIN',           1.520,      0.010,      'rem',True),  # R399
  ('pac1934',  '0x19:2',   'PPVAR_VCCCORE_PH1',     1.520,      0.001,      'rem',True),  # R906
  ('pac1934',  '0x19:3',   'PPVAR_VCCCORE_PH2',     1.520,      0.001,      'rem',True),  # R907
  ('pac1934',  '0x1A:0',   'PPVAR_PWR_IN',         20.000,      0.001,      'rem',True),  # R904
  ('pac1934',  '0x1A:1',   'PPVAR_VCCGT',           1.520,      0.002,      'rem',True),  # R909
  ('pac1934',  '0x1A:2',   'PPVAR_SYS_VCCGT_VIN',  13.350,      0.010,      'rem',True),  # R378
  ('pac1934',  '0x1A:3',   'PP1250_SOC_VIN',       13.350,      0.010,      'rem',True),  # R448
  ('pac1934',  '0x1B:0',   'PPVAR_SYS_DB',         13.350,      0.005,      'rem',True),  # R4901
  ('pac1934',  '0x1B:1',   'PPVAR_S5_DB',           3.300,      0.005,      'rem',True),  # R4902
  ('pac1934',  '0x1B:2',   'PP0500_MEM_S3',         0.500,      0.002,      'rem',True),  # R874
  ('pac1934',  '0x1B:3',   'PP5000_C_FAN',          5.000,      0.010,      'rem',True),  # R939
]
