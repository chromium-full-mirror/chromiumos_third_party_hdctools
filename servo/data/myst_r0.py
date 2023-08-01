# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

inas = [
# drvname      addr         name                         nom         sense    mux   is_calib
  ('pac1954',  '0x10:0',   'PPVAR_VDDCR_SR_VIN',         11.10,      0.05,    'rem', True),#RS7
  ('pac1954',  '0x10:1',   'PPVAR_VDDCR_SOC_VIN',        11.10,      0.01,    'rem',True),#RS6
  ('pac1954',  '0x10:2',   'PP1100_S0_N',                1.100,      0.005,   'rem',True),#RS21
  ('pac1954',  '0x10:3',   'PPVAR_VDDCR_VIN',            11.10,      0.001,   'rem',True),#RS5

  ('pac1954',  '0x11:1',   'PP1800_GSC_Z1',              1.800,      0.3,     'rem',True),#RS41
  ('pac1954',  '0x11:2',   'PP3300_GSC_Z1',              3.300,      0.3,     'rem',True),#RS42
  ('pac1954',  '0x11:3',   'PP0500_MEM_S0_VDD_MEMQ',     0.500,      0.001,   'rem',True),#RS29

  ('pac1954',  '0x12:0',   'PP3300_Z1',                  3.300,      0.005,   'rem',True),#RS2
  ('pac1954',  '0x12:1',   'PPVAR_SYS_SUB',              11.10,      0.01,    'rem',True),#RS51
  ('pac1954',  '0x12:2',   'PPVAR_MEM_S0',               0.780,      0.001,   'rem',True),#RS18
  ('pac1954',  '0x12:3',   'PP0750_MISC_S5',             0.750,      0.01,    'rem',True),#RS10

  ('pac1954',  '0x13:0',   'PP3300_S0',                  3.300,      0.005,   'rem',True),#RS19
  ('pac1954',  '0x13:1',   'PP1800_S0',                  1.800,      0.01,    'rem',True),#RS20
  ('pac1954',  '0x13:2',   'PP1800_S5',                  1.800,      0.01,    'rem',True),#RS11
  ('pac1954',  '0x13:3',   'PP3300_S5',                  3.300,      0.1,     'rem',True),#RS12

  ('pac1954',  '0x14:0',   'PP3300_WLAN_X',              3.300,      0.02,    'rem',True),#R1177
  ('pac1954',  '0x14:1',   'PP0900_VDD2L_MEM_S3',        0.900,      1,       'rem',True),#RS15
  ('pac1954',  '0x14:2',   'PP1050_VDD2H_MEM_S3',        1.050,      0.001,   'rem',True),#RS4
  ('pac1954',  '0x14:3',   'PPVAR_VBUS_IN',              20.00,      0.001,   'rem',True),#RS43

  ('pac1954',  '0x15:0',   'PP1800_VDD_18_S0',           1.800,      0.01,    'rem',True),#RS23
  ('pac1954',  '0x15:1',   'PP1050_MEM_S3_VDDIO_MEM_S3', 1.050,      0.005,   'rem',True),#RS30
  ('pac1954',  '0x15:2',   'PP1800_Z1',                  1.800,      0.01,    'rem',True),#RS9
  ('pac1954',  '0x15:3',   'PP1800_VDD_18_S5',           1.800,      0.01,    'rem',True),#RS24

  ('pac1954',  '0x16:0',   'PPVAR_SYS_VIN_VDDQ_MEM_S0',  11.1,       0.1,     'rem',True),#RS16
  ('pac1954',  '0x16:1',   'PP1800_VDD1_MEM_S3',         1.800,      0.3,     'rem',True),#RS14
  ('pac1954',  '0x16:2',   'PP5000_S5',                  5.000,      0.005,   'rem',True),#RS3
  ('pac1954',  '0x16:3',   'PP0750_MISC_S0',             0.750,      0.005,   'rem',True),#RS22

  ('pac1954',  '0x17:0',   'PP3300_VDD_33_S0',           3.300,      0.1,     'rem',True),#RS27
  ('pac1954',  '0x17:1',   'PP3300_Z5_VDDBT_RTC',        3.300,      1000,    'rem',True),#RS26
  ('pac1954',  '0x17:2',   'PP1800_VDDIO_AUDIO',         1.800,      0.2,     'rem',True),#RS25
  ('pac1954',  '0x17:3',   'PP3300_VDD_33_S5',           3.300,      0.1,     'rem',True),#RS28

  ('pac1954',  '0x18:0',   'PP1800_EC_Z1',               1.800,      1,       'rem',True),#RS32
  ('pac1954',  '0x18:2',   'PP3300_Z5',                  3.300,      0.5,     'rem',True),#RS8
  ('pac1954',  '0x18:3',   'PP3300_EC_Z1',               3.300,      0.2,     'rem',True),#RS31

  ('pac1954',  '0x19:0',   'PPVAR_BAT',                  11.10,      0.005,   'rem',True),#RS1
  ('pac1954',  '0x19:1',   'PPVAR_SYS',                  11.10,      0.001,   'rem',True),#RS44
  ('pac1954',  '0x19:2',   'PPVAR_SYS_KB_BL',            11.10,      0.3,     'rem',True),#RS38

  ('pac1954',  '0x1A:1',   'PP3300_SD_S0',               3.300,      0.01,    'rem',True),#RS40
  ('pac1954',  '0x1A:3',   'PP3300_SSD_S0',              3.300,      0.02,    'rem',True),#RS39

  ('pac1954',  '0x1B:0',   'PP3300_CAM_X',               3.300,      0.02,    'rem',True),#RS46
  ('pac1954',  '0x1B:1',   'PP3300_DISP_X',              3.300,      0.02,    'rem',True),#RS45
  ('pac1954',  '0x1B:2',   'PP0900_RT_X',                0.900,      0.01,    'rem',True),#RS36
  ('pac1954',  '0x1B:3',   'PPVAR_BL_PWR',               11.1,       0.2,     'rem',True),#RS37

  ('pac1954',  '0x1C:0',   'PP5000_S5_SUB',              5.000,      0.005,   'rem',True),#RS47
  ('pac1954',  '0x1C:1',   'PP3300_S5_SUB',              3.300,      0.5,     'rem',True),#RS49
  ('pac1954',  '0x1C:2',   'PP3300_WWAN_X_SUB',          3.300,      0.01,    'rem',True),#R1178
  ('pac1954',  '0x1C:3',   'PP0900_RT_X_SUB',            0.900,      0.01,    'rem',True),#RS50
]
