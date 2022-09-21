# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""tentacool/tentacruel proto on-board adc map"""

# generates tentacool_rev0
revs = [0]

# these devices are pac1934 (4-channels/i2c address) devices
inas = [
#    drvname,    slv,        name,                nom,    sense, mux,   is_calib
   ('pac1934',   '0x10:0',   'ppvar_batt_chg',     8.00,  0.010, 'rem', True),  # RS15
   ('pac1934',   '0x10:1',   'ppvar_batt_dischg',  8.00,  0.010, 'rem', True),  # RS15
   ('pac1934',   '0x11:0',   'ppvar_sys',          8.00,  0.010, 'rem', True),  # R264
   ('pac1934',   '0x11:1',   'ppvar_vbus_in',     20.00,  0.010, 'rem', True),  # RS4
   ('pac1934',   '0x12:0',   'ppvar_bl',           8.00,  0.020, 'rem', True),  # R453
   ('pac1934',   '0x12:1',   'pp3300_disp',       3.300,  0.020, 'rem', True),  # RS21
   ('pac1934',   '0x13:0',   'pp3300_c1_mux',     3.300,  0.020, 'rem', True),  # RS25
   ('pac1934',   '0x13:1',   'pp3300_wlan',       3.300,  0.020, 'rem', True),  # RS24
   ('pac1934',   '0x14:0',   'pp3300_hub',        3.300,  0.020, 'rem', True),  # RS12
   ('pac1934',   '0x14:1',   'pp1800_ec_vcc',     1.800,  0.020, 'rem', True),  # RS17
   ('pac1934',   '0x15:0',   'pp3300_tchscr',     3.300,  0.020, 'rem', True),  # RS22
   ('pac1934',   '0x15:1',   'pp3300_ucam',       3.300,  0.020, 'rem', True),  # RS20
   ('pac1934',   '0x16:0',   'pp5000_z2',         5.000,  0.010, 'rem', True),  # R546
   ('pac1934',   '0x16:1',   'pp3300_tchpad',     3.300,  0.020, 'rem', True),  # RS23
   ('pac1934',   '0x17:0',   'pp4200_z2',         4.200,  0.010, 'rem', True),  # R535
   ('pac1934',   '0x17:1',   'pp4200_vcore_in',   4.200,  0.020, 'rem', True),  # RS6
   ('pac1934',   '0x18:0',   'pp4200_bc_in',      4.200,  0.020, 'rem', True),  # RS3
   ('pac1934',   '0x18:1',   'pp4200_lc_in',      4.200,  0.020, 'rem', True),  # RS5
   ('pac1934',   '0x19:0',   'pp4200_vs1_in',     4.200,  0.020, 'rem', True),  # RS7
   ('pac1934',   '0x19:1',   'pp4200_vs2_in',     4.200,  0.020, 'rem', True),  # RS8
   ('pac1934',   '0x1a:0',   'pp4200_emi_in',     4.200,  0.020, 'rem', True),  # RS10
   ('pac1934',   '0x1a:1',   'pp1800_vio18_s3',   1.800,  0.020, 'rem', True),  # RS11
   ('pac1934',   '0x1b:0',   'pp3300_z2',         3.300,  0.020, 'rem', True),  # R533
   ('pac1934',   '0x1b:1',   'pp3300_c0_mux',     3.300,  0.020, 'rem', True),  # RS13
   ('pac1934',   '0x1c:0',   'pp3300_gsc_z2',     3.300,  0.020, 'rem', True),  # RS19
   ('pac1934',   '0x1c:1',   'pp1800_gsc_z2',     1.800,  0.020, 'rem', True),  # RS18
   ('pac1934',   '0x1d:0',   'pp3300_ec_z2',      3.300,  0.020, 'rem', True),  # RS16
   ('pac1934',   '0x1d:1',   'pp1800_ec_z2',      1.800,  0.020, 'rem', True),  # RS14
   ('pac1934',   '0x1e:0',   'pp5000_lspkr',      5.000,  0.020, 'rem', True),  # R1272
   ('pac1934',   '0x1e:1',   'pp3300_cs',         3.300,  0.020, 'rem', True),  # RS26
   # 0x1f:0 is unused
   ('pac1934',   '0x1f:1',   'pp5000_rspkr',      5.000,  0.020, 'rem', True),  # R1273
]
