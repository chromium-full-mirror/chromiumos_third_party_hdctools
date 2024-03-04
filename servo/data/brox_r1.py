# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# these devices are pac1954 devices
inas = [
#drvname      addr:port   name                   nom       sense        mux  is_calib
('pac1954',  '0x10:0',   'PP3300_S5_SD',         3.3,      0.01,       'rem',True),  # R482
('pac1954',  '0x10:1',   'PPVAR_SYS_KB_BL',      13.2,     0.02,       'rem',True),  # R1167
('pac1954',  '0x10:2',   'PP3300_EC_Z1',         3.3,      0.1,        'rem',True),  # R802
('pac1954',  '0x10:3',   'PP3300_DBG',           3.3,      0.01,       'rem',True),  # R30
('pac1954',  '0x11:0',   'PP1800_EC_S5',         1.8,      0.1,        'rem',True),  # R635
('pac1954',  '0x11:1',   'PP3300_TCHPAD',        3.3,      0.02,       'rem',True),  # R232
('pac1954',  '0x11:2',   'PP5000_FAN_X',         5,        0.005,      'rem',True),  # R1017
('pac1954',  '0x11:3',   'PP3300_WLAN_X',        3.3,      0.005,      'rem',True),  # R294
('pac1954',  '0x12:0',   'PP3300_Z1',            3.3,      0.001,      'rem',True),  # R634
('pac1954',  '0x12:1',   'PP3300_SSD_S5',        3.3,      0.005,      'rem',True),  # R221
('pac1954',  '0x12:2',   'PP3300_RTC',           3.3,      1,          'rem',True),  # R629
('pac1954',  '0x12:3',   'PP3300_S5',            3.3,      0.001,      'rem',True),  # R656
('pac1954',  '0x13:0',   'PPVAR_SYS_EDP',        9,        0.05,       'rem',True),  # R559
('pac1954',  '0x13:1',   'PP1065_MEM',           1.065,    0.001,      'rem',True),  # R906
('pac1954',  '0x13:2',   'PP3300_UCAM_X',        3.3,      0.005,      'rem',True),  # R67
('pac1954',  '0x13:3',   'PP1800_MEM',           1.8,      0.01,       'rem',True),  # RS5
('pac1954',  '0x14:0',   'PPVAR_SYS_1800_S5',    1.8,      0.02,       'rem',True),  # R69
('pac1954',  '0x14:1',   'PP1800_S5',            1.8,      0.002,      'rem',True),  # R171
('pac1954',  '0x14:2',   'PP1800_SOC_S5',        1.8,      0.005,      'rem',True),  # R108
('pac1954',  '0x14:3',   'PP3300_SOC_S5',        3.3,      0.005,      'rem',True),  # R109
('pac1954',  '0x15:0',   'PP3300_EDP_X',         3.3,      0.02,       'rem',True),  # R657
('pac1954',  '0x15:1',   'PP3300_TCHSCR_X',      3.3,      0.02,       'rem',True),  # R658
('pac1954',  '0x15:2',   'PPVAR_VCCIN_AUX',      1.8,      0.001,      'rem',True),  # R1274
('pac1954',  '0x15:3',   'PPVAR_SYS_VCCIN_AUX',  1.8,      0.002,      'rem',True),  # R692
('pac1954',  '0x16:0',   'PP3300_Z5',            3.3,      0.5,        'rem',True),  # R904
('pac1954',  '0x16:1',   'PPVAR_SYS_5000_Z1',    5,        0.01,       'rem',True),  # R597
('pac1954',  '0x16:2',   'PPVAR_SYS_3300_Z1',    3.3,      0.02,       'rem',True),  # R1009
('pac1954',  '0x16:3',   'PP5000_Z1',            5,        0.001,      'rem',True),  # R560
('pac1954',  '0x17:0',   'PPVAR_VBUS_IN',        13.2,     0.001,      'rem',True),  # R600
('pac1954',  '0x17:1',   'PP5000_PD_Z1',         5,        0.005,      'rem',True),  # R985
('pac1954',  '0x17:2',   'PP3300_PD_PIN32',      3.3,      0.01,       'rem',True),  # R986
('pac1954',  '0x17:3',   'PP0500_MEM_S3',        0.5,      0.01,       'rem',True),  # RS1
('pac1954',  '0x18:0',   'PP3300_GSC_Z1',        3.3,      0.3,        'rem',True),  # R993
('pac1954',  '0x18:1',   'PP2500_3300_UFS_VCC',  3.3,      0.01,       'rem',True),  # R1128
('pac1954',  '0x18:2',   'PP1800_UFS_S5',        1.8,      0.01,       'rem',True),  # R1101
('pac1954',  '0x18:3',   'PP1200_UFS_S0',        1.2,      0.01,       'rem',True),  # R1103
('pac1954',  '0x19:0',   'PP5000_CODEC_PVDD_S5', 5,        0.005,      'rem',True),  # R1049
('pac1954',  '0x19:1',   'PP3300_CODEC_S5',      3.3,      0.1,        'rem',True),  # R1048
('pac1954',  '0x19:2',   'PP1800_CODEC_HDA_S5',  1.8,      0.1,        'rem',True),  # R923
('pac1954',  '0x19:3',   'PP5000_CODEC_S5',      5,        0.1,        'rem',True),  # R1050
]
