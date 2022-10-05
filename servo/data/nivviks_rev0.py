# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Nivviks rev0 on-board adc map"""

# generates nissa_rev0
revs = [0]

# these devices are pac1954 (4-channels/i2c address) devices
inas = [
#  drvname,    slv,    name,   nom,    sense,  mux,    is_calib
   ('pac1954',  '0x10:0',  'PP1050_MEM_S3',  '1.05 ',  '0.002',  'rem', True),
   ('pac1954',  '0x10:1',  'PP1800_MEM_S3',  '1.80 ',  '0.02',  'rem', True),
   ('pac1954',  '0x10:2',  'PP3300_GSC_Z1',  '3.30 ',  '0.5',  'rem', True),
   ('pac1954',  '0x10:3',  'PP0500_MEM_S3',  '0.50 ',  '0.005',  'rem', True),
   ('pac1954',  '0x14:0',  'PP3300_S5',  '3.30 ',  '0.02',  'rem', True),
   ('pac1954',  '0x14:1',  'PPVAR_VNNEXT',  '0.78 ',  '0.01',  'rem', True),
   ('pac1954',  '0x14:2',  'PP3300_WLAN_X',  '3.30 ',  '0.01',  'rem', True),
   ('pac1954',  '0x14:3',  'PP3300_SOC_S5',  '3.30 ',  '0.05',  'rem', True),
   ('pac1954',  '0x12:0',  'PP1050_V1P05EXT',  '1.05 ',  '0.01',  'rem', True),
   ('pac1954',  '0x12:1',  'PP3300_EC_Z1',  '3.30 ',  '2.2',  'rem', True),
   ('pac1954',  '0x12:2',  'PP1800_S5',  '1.80 ',  '0.005',  'rem', True),
   ('pac1954',  '0x12:3',  'PP1800_SOC_S5',  '1.80 ',  '0.005',  'rem', True),
   ('pac1954',  '0x13:0',  'PPVAR_VCCIN_AUX',  '1.80 ',  '0.002',  'rem', True),
   ('pac1954',  '0x13:1',  'PP5000_S5',  '5.00 ',  '0.005',  'rem', True),
   ('pac1954',  '0x13:2',  'PP3300_Z1',  '3.30 ',  '0.005',  'rem', True),
   ('pac1954',  '0x13:3',  'PPVAR_BL_PWR',  '6.00 ',  '0.1',  'rem', True),
]
