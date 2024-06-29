# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# These devices are pac1934 devices
inas = [
#   drvname      addr:port  name                    nom     sense   mux    is_calib
    ('pac1934',  '0x10:0',  'PP3300_RTC',           3.3,    0.5,    'rem', True),# R1753
    ('pac1934',  '0x10:1',  'PP1800_SOC_S5',        1.8,    0.005,  'rem', True),# R2018
    ('pac1934',  '0x10:2',  'PP3300_SOC_S5',        3.3,    0.005,  'rem', True),# R2017
    ('pac1934',  '0x10:3',  'PP3300_FP_X',          3.3,    0.5,    'rem', True),# R8832
    ('pac1934',  '0x11:0',  'PP1800_S5_IN',         1.8,    0.01,   'rem', True),# R1313
    ('pac1934',  '0x11:1',  'PPVAR_SYS_VCCIN_AUX',  13.2,   0.002,  'rem', True),# R1543
    ('pac1934',  '0x11:2',  'PPVAR_SYS_VCCCORE_GT', 13.2,   0.01,   'rem', True),# R1677
    ('pac1934',  '0x11:3',  'PPVAR_SYS_VCCGT',      13.2,   0.01,   'rem', True),# R1676
    ('pac1934',  '0x12:0',  'PP3300_Z5',            3.3,    0.01,   'rem', True),# R1116
    ('pac1934',  '0x12:1',  'PP0500_MEM_S0',        0.5,    0.01,   'rem', True),# R1724
    ('pac1934',  '0x12:2',  'PP3300_S5',            3.3,    0.001,  'rem', True),# R1910
    ('pac1934',  '0x12:3',  'PPVAR_SYS_5000_Z1',    13.2,   0.001,  'rem', True),# R1215
    ('pac1934',  '0x13:0',  'PPVAR_VBUS_IN',        20,     0.01,   'rem', True),# R1001
    ('pac1934',  '0x13:1',  'PP1200_UFS3_S0',       1.2,    0.02,   'rem', True),# RS4501
    ('pac1934',  '0x13:2',  'PP1800_UFS2_S5',       1.8,    0.02,   'rem', True),# RS4502
    ('pac1934',  '0x13:3',  'PP2500_3300_UFS_VCC',  3.3,    0.02,   'rem', True),# RS4503
    ('pac1934',  '0x14:0',  'PP1800_FP_X',          1.8,    0.5,    'rem', True),# R8831
    ('pac1934',  '0x14:1',  'PP3300_UCAM_X',        3.3,    0.01,   'rem', True),# R4435
    ('pac1934',  '0x14:2',  'PP3300_TCHSCR_X',      3.3,    0.01,   'rem', True),# R8036
    ('pac1934',  '0x14:3',  'PP3300_WLAN_X',        3.3,    0.01,   'rem', True),# R5933
    ('pac1934',  '0x15:0',  'PP5000_CODEC_S5',      5,      0.02,   'rem', True),# R4933
    ('pac1934',  '0x15:1',  'PP5000_CODEC_PVDD_S5', 5,      0.005,  'rem', True),# R4927
    ('pac1934',  '0x15:2',  'PP3300_CODEC_S5',      3.3,    0.02,   'rem', True),# R4915
    ('pac1934',  '0x15:3',  'PP1800_CODEC_HDA_S5',  1.8,    0.02,   'rem', True),# R4916
    ('pac1934',  '0x17:0',  'PP5000_FAN_X',         5,      0.005,  'rem', True),# R5511
    ('pac1934',  '0x17:1',  'PP3300_GSC_Z1',        3.3,    0.01,   'rem', True),# R3203
    ('pac1934',  '0x17:2',  'PP3300_EC_Z1',         3.3,    0.5,    'rem', True),# R3648
    ('pac1934',  '0x17:3',  'PP1800_EC_S5',         1.8,    0.5,    'rem', True),# R3640
    ('pac1934',  '0x18:0',  'PP1800_MEM_S3',        1.8,    0.01,   'rem', True),# R1722
    ('pac1934',  '0x18:1',  'PP1065_MEM_S3',        1.065,  0.001,  'rem', True),# R1725
    ('pac1934',  '0x18:2',  'PPVAR_SYS_3300_Z1',    13.2,   0.01,   'rem', True),# R1115
    ('pac1934',  '0x18:3',  'PP3300_EDP_X',         3.3,    0.01,   'rem', True),# R4436
    ('pac1934',  '0x19:0',  'PP3300_SSD_S5',        3.3,    0.005,  'rem', True),# R5410
    ('pac1934',  '0x19:1',  'PP5000_PD_Z1',         5,      0.005,  'rem', True),# R6601
    ('pac1934',  '0x19:2',  'PP3300_DBG',           3.3,    0.01,   'rem', True),# R3330
    ('pac1934',  '0x19:3',  'PPVAR_SYS_EDP_J',      13.2,   0.005,  'rem', True),# R4450
    ('pac1934',  '0x1a:0',  'PP3300_PD_PIN32',      3.3,    0.01,   'rem', True),# R6603
    ('pac1934',  '0x1a:1',  'PP3300_S5_SD',         3.3,    0.01,   'rem', True),# R4512
    ('pac1934',  '0x1a:2',  'PP3300_TCHPAD',        3.3,    0.02,   'rem', True),# R8406
    ('pac1934',  '0x1a:3',  'VCC_KB_BL_CONN',       5,      0.02,   'rem', True),# R8457
]
