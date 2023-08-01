# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# generates dibbi_mlb_rev0
revs = [0]
inas = [
# drvname      slv         name                     nom         sense       mux   is_calib
  ('pac1954',  '0x10:0',   'PP1100_DRAM_S3',        1.100,      0.002,      'rem',True),#R245
  ('pac1954',  '0x10:1',   'PP600_DRAM_S3',         0.600,      0.01,       'rem',True),#R243
  ('pac1954',  '0x10:2',   'PP1800_DRAM_S3',        1.800,      0.1,        'rem',True),#R424
  ('pac1954',  '0x10:3',   'PPVAR_VCCIN_IN',        1.8,        0.002,      'rem',True),#R372
  ('pac1954',  '0x11:0',   'PPVAR_SYS_SNS_N',       19,         0.01,       'rem',True),#R499
  ('pac1954',  '0x11:1',   'PP5000_Z1',             5.000,      0.01,       'rem',True),#R267
  ('pac1954',  '0x11:2',   'PP1050_VCCIO_EXT_IN',   1.050,      0.05,       'rem',True),#R379
  ('pac1954',  '0x11:3',   'PP3300_Z1',             3.300,      0.01,       'rem',True),#R266
  ('pac1954',  '0x12:1',   'PP1800_AGSH_S0',        1.800,      0.02,       'rem',True),#R247
  ('pac1954',  '0x12:3',   'PP1800_SOC_S5',         1.800,      0.01,       'rem',True),#R469
  ('pac1954',  '0x13:1',   'PP3300_S5',             3.300,      0.02,       'rem',True),#R248
  ('pac1954',  '0x13:2',   'PP1800_EMMC_S5',        1.800,      0.1,        'rem',True),#R246
  ('pac1954',  '0x13:3',   'PP3300_LAN_S5',         3.300,      0.05,       'rem',True),#R492
  ('pac1954',  '0x14:0',   'PPVAR_VCCIN_AUX_IN',    1.8,        0.002,      'rem',True),#R397
  ('pac1954',  '0x14:1',   'PP1800_S5',             1.800,      0.01,       'rem',True),#R276
  ('pac1954',  '0x14:2',   'PP3300_GSC_Z1',         3.300,      0.5,        'rem',True),#R399
  ('pac1954',  '0x15:0',   'PP3300_SOC_S5',         3.300,      0.05,       'rem',True),#R249
  ('pac1954',  '0x15:1',   'PP3300_EMMC_S5',        3.300,      0.1,        'rem',True),#R250
  ('pac1954',  '0x15:2',   'PP3300_WLAN_S5',        3.300,      0.05,       'rem',True),#R470
  ('pac1954',  '0x15:3',   'PP3300_USB_C0_Z1',      3.300,      1.0,        'rem',True),#R398
]
