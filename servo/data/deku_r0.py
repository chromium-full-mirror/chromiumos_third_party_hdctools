# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Generates Deku r0
# Power Supply : 19.5V Barrel Jack
revs = [0]

# these devices are pac1954 devices
inas = [
#drvname      addr:port   name                          nom       sense        mux   is_calib
('pac1954',  '0x10:0',   'PP1800_MEM_S3',               1.8,      0.005,       'rem',True),  # R745
('pac1954',  '0x10:1',   'PP1065_MEM_S3',               1.065,    0.003,       'rem',True),  # R1299
('pac1954',  '0x10:2',   'PP1065_SOC_S3',               1.065,    0.003,       'rem',True),  # R1300
('pac1954',  '0x10:3',   'PP0500_MEM_S3',               0.5,      0.001,       'rem',True),  # R1296
('pac1954',  '0x11:0',   'PPVAR_SYS_R',                 19.5,     0.002,       'rem',True),  # R763
('pac1954',  '0x11:1',   'PP1800_Z1',                   1.8,      0.1,         'rem',True),  # R73
('pac1954',  '0x11:2',   'PP3300_Z1',                   3.3,      0.01,        'rem',True),  # R535
('pac1954',  '0x11:3',   'PP3300_GSC_Z1',               3.3,      0.01,        'rem',True),  # R758
('pac1954',  '0x12:0',   'PPVAR_SYS_VCCSA_VIN',         19.5,     0.01,        'rem',True),  # R735
('pac1954',  '0x12:1',   'PPVAR_SYS_VCCORE_VIN',        19.5,     0.005,       'rem',True),  # R739
('pac1954',  '0x12:2',   'PPVAR_SYS_PP0P77_SOC_S5_VIN', 19.5,     0.01,        'rem',True),  # R736
('pac1954',  '0x12:3',   'PPVAR_SYS_VCCGT_VIN',         19.5,     0.005,       'rem',True),  # R744
('pac1954',  '0x13:0',   'PP1800_S5',                   1.8,      0.003,       'rem',True),  # R166
('pac1954',  '0x13:1',   'PP3300_S5',                   3.3,      0.005,       'rem',True),  # RS1
('pac1954',  '0x13:2',   'PP5000_B_Z1',                 5,        0.003,       'rem',True),  # R775
('pac1954',  '0x13:3',   'PP3300_SSD_X',                3.3,      0.005,       'rem',True),  # R506
('pac1954',  '0x14:0',   'PP3300_WLAN_S5',              3.3,      0.01,        'rem',True),  # R517
('pac1954',  '0x14:1',   'PP3300_LAN_S5',               3.3,      0.01,        'rem',True),  # R753
('pac1954',  '0x14:2',   'PPVAR_SYS_PP1250_SOC_S5_VIN', 19.5,     0.01,        'rem',True),  # R875
('pac1954',  '0x14:3',   'PP5000_A_Z1',                 5,        0.003,       'rem',True),  # R540
]
