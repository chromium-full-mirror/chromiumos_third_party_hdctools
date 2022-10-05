# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# generates primus_rev0
revs = [0]
config_type='servod'

inas = [

    ('pac1934', '0x10:0', 'PP5000_Z1',      5.0, 0.002, 'rem', True),   #PR4502
    ('pac1934', '0x10:1', 'PP3300_S5',      3.0, 0.005, 'rem', True),   #PR4510
    ('pac1934', '0x10:2', 'PPVAR_VCCIN_AUX',1.8, 0.002, 'rem', True),   #PR5012
    ('pac1934', '0x10:3', 'PP3300_EDP_X',   3.3, 0.020, 'rem', True),   #R4018

    ('pac1934', '0x11:0', 'PP1100_DRAM',    1.1, 0.002, 'rem', True),   #PR5108
    ('pac1934', '0x11:1', 'PP0600_VDDQ',    0.6, 0.005, 'rem', True),   #PR5106
    ('pac1934', '0x11:2', 'PP1800_DRAM',    1.8, 0.005, 'rem', True),   #PR5107
    ('pac1934', '0x11:3', 'PPVAR_SYS',      9.2, 0.020, 'rem', True),   #PR5103

    ('pac1934', '0x12:0', 'PP3300_FP_DX',   3.3,  5.000, 'rem', True),   #R4026
    ('pac1934', '0x12:1', 'PP1800_FP_DX',   1.8,  5.000, 'rem', True),   #R4025
    ('pac1934', '0x12:2', 'PPVAR_VBUS_IN_N',20.0, 0.001, 'rem', True),   #PR4436
    ('pac1934', '0x12:3', 'PP3300_DBG',     3.3,  0.010, 'rem', True),   #R8843

    ('pac1934', '0x13:0', 'PP1800_S5',      1.8, 0.005, 'rem', True),   #PR5303
    ('pac1934', '0x13:1', 'PP3300_Z1',      3.3, 0.001, 'rem', True),   #R4005
    ('pac1934', '0x13:2', 'PP3300_WLAN_X',  3.3, 0.005, 'rem', True),   #R6116
    ('pac1934', '0x13:3', 'PP3300_WWAN_X',  3.3, 0.005, 'rem', True),   #R6259

    ('pac1934', '0x15:0', 'PP3300_EC_Z1',   3.3, 2.000, 'rem', True),   #R2440
    ('pac1934', '0x15:1', 'PP1800_EC_Z1_R', 1.8, 2.000, 'rem', True),   #R2441
    ('pac1934', '0x15:2', 'PP3300_USB_Z1',  3.3, 1.000, 'rem', True),   #R4004
    ('pac1934', '0x15:3', 'PP3300_SEQ',     3.3, 0.001, 'rem', True),   #R3901

    ('pac1934', '0x14:1', 'PP3300_HDMI_X',  3.3, 0.020, 'rem', True),   #R5704
    ('pac1934', '0x14:2', 'PP5000_HDMI_X',  5.0, 0.010, 'rem', True),   #R5701
    ('pac1934', '0x14:3', 'PP5000_FAN_R',   5.0, 0.001, 'rem', True),   #R2612

    ('pac1934', '0x16:0', 'PP3300_EC_Z2',   3.3, 0.001, 'rem', True),   #R2439
    ('pac1934', '0x16:1', 'PP3300_GSC_Z2',  3.3, 1.000, 'rem', True),   #R9120
    ('pac1934', '0x16:2', 'PP3300_RTC_Z2',  3.3, 0.001, 'rem', True),   #PR5202
    ('pac1934', '0x16:3', 'PP3300_Z2',      3.3, 0.010, 'rem', True),   #PR5201

    ('pac1934', '0x17:0', 'PP1800_SOC_S5',  1.8, 0.005, 'rem', True),   #R2202
    ('pac1934', '0x17:1', 'PP3300_SOC_S5',  3.3, 0.005, 'rem', True),   #R2203
    ('pac1934', '0x17:2', 'PP3300_SSD_X',   3.3, 0.005, 'rem', True),   #R6301

    ('pac1934', '0x18:1', 'PP3300_TCHPAD_X',3.3, 0.020, 'rem', True),   #R6510
    ('pac1934', '0x18:2', 'PP3300_TCHSCR_X',3.3, 0.020, 'rem', True),   #R4009

    ('pac1934', '0x19:3', 'PP3300_FCAM',    3.3, 0.010, 'rem', True),   #R4013

]
