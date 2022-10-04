# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# generates nissa_mlb_rev1
revs = [1]

# these devices are pac1954 devices
inas = [
# drvname      slv         name                     nom         sense       mux   is_calib
  ('pac1954',  '0x10:0',   'PP1050_MEM_S3',         1.050,      0.002,      'rem',True),#R898
  ('pac1954',  '0x10:1',   'PP1800_MEM_S3',         1.800,      0.02,       'rem',True),#R896
  ('pac1954',  '0x10:2',   'PP3300_GSC_Z1',         3.300,      0.5,        'rem',True),#R881
  ('pac1954',  '0x10:3',   'PP0500_MEM_S3',         0.500,      0.005,      'rem',True),#R897
  ('pac1954',  '0x11:0',   'PP3300_S5',             3.300,      0.02,       'rem',True),#R882
  ('pac1954',  '0x11:1',   'PPVAR_VNNEXT',          0.780,      0.01,       'rem',True),#R964
  ('pac1954',  '0x11:2',   'PP3300_WLAN_X',         3.300,      0.01,       'rem',True),#R886
  ('pac1954',  '0x11:3',   'PP3300_SOC_S5',         3.300,      0.05,       'rem',True),#R885
  ('pac1954',  '0x12:0',   'PP1050_V1P05EXT',       1.050,      0.01,       'rem',True),#R965
  ('pac1954',  '0x12:1',   'PP3300_EC_Z1',          3.300,      2.2,        'rem',True),#R645
  ('pac1954',  '0x12:2',   'PP1800_S5',             1.800,      0.005,      'rem',True),#R716
  ('pac1954',  '0x12:3',   'PP1800_SOC_S5',         1.800,      0.005,      'rem',True),#R890
  ('pac1954',  '0x13:0',   'PPVAR_VCCIN_AUX',       1.800,      0.002,      'rem',True),#R875
  ('pac1954',  '0x13:1',   'PP5000_S5',             5.000,      0.005,      'rem',True),#R878
  ('pac1954',  '0x13:2',   'PP3300_Z1',             3.300,      0.005,      'rem',True),#R880
  ('pac1954',  '0x13:3',   'PPVAR_BL_PWR_F',        6.000,      0.1,        'rem',True),#R866
]
