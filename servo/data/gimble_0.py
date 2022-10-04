# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# generates gimble_rev0
revs = [0]
config_type='servod'

inas = [

    ('pac1934', '0x10:0', 'pp3300_soc_s5',  3.3, 0.005, 'rem', True),   #R2205
    ('pac1934', '0x10:1', 'pp1800_s5',      1.8, 0.005, 'rem', True),   #PR5303
    ('pac1934', '0x10:2', 'pp1800_s5_r',    1.8, 0.005, 'rem', True),   #PR5303
    ('pac1934', '0x10:3', 'pp3300_edp_x',   3.3, 0.020, 'rem', True),   #R5507

    ('pac1934', '0x11:0', 'pp1800_dram',    1.8, 0.005, 'rem', True),   #PR5107
    ('pac1934', '0x11:1', 'pp600_vddq',     0.6, 0.010, 'rem', True),   #PR5106
    ('pac1934', '0x11:2', 'pp3300_fcam_x',  3.3, 0.010, 'rem', True),   #R5510
    ('pac1934', '0x11:3', 'pp5000_z1',      5.0, 0.002, 'rem', True),   #PR4502

    ('pac1934', '0x12:0', 'pp3300_z2_r',    3.3, 0.010, 'rem', True),   #PR5201
    ('pac1934', '0x12:1', 'pp3300_rtc_z2',  3.3, 0.001, 'rem', True),   #PR5202
    ('pac1934', '0x12:2', 'pp3300_wlan_x',  3.3, 0.005, 'rem', True),   #R6106
    ('pac1934', '0x12:3', 'pp3300_s5',      3.3, 0.005, 'rem', True),   #PR4510

    ('pac1934', '0x13:0', 'ppvar_sys',      9.2, 0.005, 'rem', True),   #R5511
    ('pac1934', '0x13:1', 'pp3300_tchscr_x',3.3, 0.020, 'rem', True),   #R5509
    ('pac1934', '0x13:2', 'pp3300_gsc_z2',  3.3, 0.100, 'rem', True),   #R2511
    ('pac1934', '0x13:3', 'pp1100_dram',    1.1, 0.002, 'rem', True),   #PR5108

    ('pac1934', '0x14:0', 'pp3300_ssd_x',   3.3,  0.005, 'rem', True),   #R6303
    ('pac1934', '0x14:1', 'pp3300_fp_x',    3.3,  0.020, 'rem', True),   #R3909
    ('pac1934', '0x14:2', 'pp1800_fp_sens_x',1.8, 0.020, 'rem', True),   #R3908
    ('pac1934', '0x14:3', 'pp3300_sd_dx',   3.3,  0.020, 'rem', True),   #R3905

    ('pac1934', '0x16:0', 'pp3300_seq',     3.3, 0.001, 'rem', True),   #R4011
    ('pac1934', '0x16:1', 'ppvar_vccin_aux',1.8, 0.002, 'rem', True),   #PR5012
    ('pac1934', '0x16:2', 'pp3300_z1_r',    3.3, 0.001, 'rem', True),   #R3902
    ('pac1934', '0x16:3', 'pp3300_usb_z1',  3.3, 0.100, 'rem', True),   #R3903

    ('pac1934', '0x18:0', 'ppvar_vbus_in_n',20.0, 0.001, 'rem', True),   #PR4435
    ('pac1934', '0x18:1', 'pp3300_dbg',     3.3,  0.010, 'rem', True),   #R8808

    ('pac1934', '0x19:0', 'pp3300_ec_z1',   3.3, 2.200, 'rem', True),   #R2401
    ('pac1934', '0x19:1', 'pp3300_ec_z2',   3.3, 0.001, 'rem', True),   #R2419
    ('pac1934', '0x19:2', 'pp1800_ec_z1',   1.8, 2.200, 'rem', True),   #R2418
    ('pac1934', '0x19:3', 'pp3300_tchpad_x',3.3, 0.020, 'rem', True),   #R6502

]
