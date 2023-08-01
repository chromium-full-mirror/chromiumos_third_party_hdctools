# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

revs = [0]
inas = [
# drvname      slv         name                     nom         sense       mux   is_calib
  ('pac1954',  '0x10:0',   'PP3300_SSD_X',     3.300,      0.005,      'rem',True),#R289
  ('pac1954',  '0x10:1',   'PP3300_TCHPAD_S5', 3.300,      0.02,       'rem',True),#R295
  ('pac1954',  '0x10:2',   'PP3300_WLAN_X',    3.300,      0.005,      'rem',True),#R327
  ('pac1954',  '0x10:3',   'PP12000_FAN2',     12.000,     0.02,       'rem',True),#R304
  ('pac1954',  '0x11:0',   'PP1800_SOC_S5',    1.800,      0.005,      'rem',True),#R108
  ('pac1954',  '0x11:1',   'PPVAR_VCCCORE_IN', 20.000,     0.005,      'rem',True),#R1155
  ('pac1954',  '0x11:2',   'PPVAR_VCCGT_IN',   20.000,     0.005,      'rem',True),#R1156
  ('pac1954',  '0x11:3',   'PP1800_S5',        1.800,      0.002,      'rem',True),#R446
  ('pac1954',  '0x12:0',   'PP5000_S5',        5.000,      0.002,      'rem',True),#R436
  ('pac1954',  '0x12:1',   'PP3300_Z1',        3.300,      0.1,        'rem',True),#R656
  ('pac1954',  '0x12:2',   'PP3300_USB_Z1',    3.300,      0.1,        'rem',True),#R1071
  ('pac1954',  '0x12:3',   'PP3300_GPU_X_UNUSED',     3.300,      0.01,          'rem',True),#R1159
  ('pac1954',  '0x13:0',   'PP1200_S5',        1.200,      0.02,       'rem',True),#R746
  ('pac1954',  '0x13:1',   'PPVAR_VCCIN_AUX',  1.000,      0.002,      'rem',True),#R471
  ('pac1954',  '0x13:2',   'PPVAR_GPU_FBVDDQ_IN',20.000,   0.005,      'rem',True),#R732
  ('pac1954',  '0x13:3',   'PP5000_HDMI_X',    5.000,      0.01,       'rem',True),#R787
  ('pac1954',  '0x14:0',   'PPVAR_GPUVDD_IN',20.000,     0.005,      'rem',True),#R731
  ('pac1954',  '0x14:1',   'PP3300_EDP_X',     3.300,      0.02,       'rem',True),#R670
  ('pac1954',  '0x14:2',   'PPVAR_BAT',        16.70,      0.005,      'rem',True),#R1277
  ('pac1954',  '0x14:3',   'PP5000_GPU_X_UNUSED',     5.000,      0.1,          'rem',True),#R1162
  ('pac1954',  '0x15:0',   'PP1800_EC_Z1',     1.800,      2.2,        'rem',True),#R348
  ('pac1954',  '0x15:1',   'PP3300_EC_Z1',     3.300,      2.2,        'rem',True),#R339
  ('pac1954',  '0x15:2',   'PPVAR_SYS_KB_BL',  20.000,     0.02,       'rem',True),#R300
  ('pac1954',  '0x15:3',   'PP3300_GSC_Z2',    3.300,      0.2,        'rem',True),#R1008
  ('pac1954',  '0x16:0',   'PP3300_EC_Z2_UNUSED',     3.300,      2.2,          'rem',True),#R330
  ('pac1954',  '0x16:1',   'PP1100_DRAM_S3',   1.100,      0.002,      'rem',True),#R1151
  ('pac1954',  '0x16:2',   'PP5000_VINB_DRAM', 5.000,      0.002,      'rem',True),#R1074
  ('pac1954',  '0x16:3',   'PP3300_HDMI_X',    3.300,      0.02,       'rem',True),#R768
  ('pac1954',  '0x17:0',   'PP3300_SOC_S5',    3.300,      0.005,      'rem',True),#R109
  ('pac1954',  '0x17:1',   'PP3300_RTC_Z2',    3.300,      1.0,        'rem',True),#R668
  ('pac1954',  '0x17:2',   'PP3300_Z2',        3.300,      0.005,      'rem',True),#R421
  ('pac1954',  '0x17:3',   'PP3300_S5',        3.300,      0.005,      'rem',True),#R445
  ('pac1954',  '0x18:0',   'PP3300_LAN_X',     3.300,      0.005,      'rem',True),#R879
  ('pac1954',  '0x18:1',   'PP3300_SD_X',      3.300,      0.01,       'rem',True),#R589
  ('pac1954',  '0x18:2',   'PP3300_SD_S5',     3.300,      0.01,       'rem',True),#R798
  ('pac1954',  '0x18:3',   'PPVAR_SYS_EDP_X',  20.000,     0.005,      'rem',True),#R313
  ('pac1954',  '0x19:0',   'PPVAR_PEXVDD_GPU_X',0.900,    0.002,      'rem',True),#R735
  ('pac1954',  '0x19:1',   'PP1200_GPU_X',     1.200,      0.002,      'rem',True),#R1085
  ('pac1954',  '0x19:2',   'PPVAR_VBUS_IN',    20.000,     0.001,      'rem',True),#R400
  ('pac1954',  '0x19:3',   'PP12000_FAN1',     12.000,     0.02,       'rem',True),#R249
  ('pac1954',  '0x1A:0',   'PPVAR_CORE_IO_GPU_X',1.800,      0.01,       'rem',True),#R1007
  ('pac1954',  '0x1A:1',   'PP1800_GPU_X',     1.800,      0.002,      'rem',True),#R1158
  ('pac1954',  '0x1A:2',   'PP1800_HDMI_X',    1.800,      0.1,        'rem',True),#R395
  ('pac1954',  '0x1A:3',   'SPARE_DEBUG',      1.000,      499000.0,   'rem',True),#R1052 spare
]
