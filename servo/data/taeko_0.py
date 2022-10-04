# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""taeko rev0 on-board adc map"""

# generates taeko_rev0
revs = [0]

inas = [
#    drvname,    slv,        name,                   nom,    sense, mux,   is_calib
   ('pac1934',   '0x10:0',   'pp3300_ec_z2',         3.300,  0.000, 'rem', False), # R338
   ('pac1934',   '0x10:1',   'pp3300_gsc_z2',        3.300,  0.100, 'rem', True),  # R1008
   ('pac1934',   '0x10:2',   'pp3300_wlan_x',        3.300,  0.005, 'rem', True),  # R294
   ('pac1934',   '0x10:3',   'pp3300_soc_s5',        3.300,  0.005, 'rem', True),  # R109

   ('pac1934',   '0x11:0',   'pp1800_soc_s5',        1.800,  0.005, 'rem', True),  # R108
   ('pac1934',   '0x11:1',   'pp1800_sensor_s5',     1.800,  0.000, 'rem', False), # R762
   ('pac1934',   '0x11:2',   'pp3300_seq',           3.300,  0.000, 'rem', False), # R1067
   ('pac1934',   '0x11:3',   'pp3300_tchpad_x',      3.300,  0.020, 'rem', True),  # R232

   ('pac1934',   '0x12:0',   'pp3300_ssd_x',         3.300,  0.005, 'rem', True),  # R221
   ('pac1934',   '0x12:1',   'pp3300_z1',            3.300,  0.000, 'rem', False), # R656
   ('pac1934',   '0x12:2',   'pp3300_usb_z1',        3.300,  0.100, 'rem', True),  # R655
   ('pac1934',   '0x12:3',   'pp3300_ec_z1',         3.300,  2.200, 'rem', True),  # R1184

   ('pac1934',   '0x13:0',   'pp1800_ec_z1',         1.800,  2.200, 'rem', True),  # R348

   ('pac1934',   '0x14:0',   'ppvar_sys_edp',        6.100,  0.005, 'rem', True),  # R559
   ('pac1934',   '0x14:1',   'pp3300_edp_x',         3.300,  0.020, 'rem', True),  # R657
   ('pac1934',   '0x14:2',   'pp3300_fcam_x',        3.300,  0.010, 'rem', True),  # R582
   ('pac1934',   '0x14:3',   'pp3300_hps_x',         3.300,  0.100, 'rem', True),  # R583

   ('pac1934',   '0x15:0',   'pp1800_sensor_edp',    3.300,  0.000, 'rem', False), # R1666
   ('pac1934',   '0x15:1',   'pp3300_tchscr_x',      3.300,  0.020, 'rem', True),  # R658
   ('pac1934',   '0x15:2',   'pp1800_s5',            1.800,  0.005, 'rem', True),  # R467
   ('pac1934',   '0x15:3',   'pp5000_fan',           5.000,  0.000, 'rem', False), # R249

   ('pac1934',   '0x16:0',   'pp1800_dram',          1.800,  0.010, 'rem', True),  # R671
   ('pac1934',   '0x16:1',   'pp1100_dram',          1.100,  0.002, 'rem', True),  # R672
   ('pac1934',   '0x16:2',   'pp0600_vddq',          0.600,  0.005, 'rem', True),  # R673
   ('pac1934',   '0x16:3',   'ppvar_vccin_aux',      1.800,  0.002, 'rem', True),  # R494

   ('pac1934',   '0x17:1',   'pp3300_rtc_z2',        3.300,  0.000, 'rem', False), # R459
   ('pac1934',   '0x17:2',   'pp3300_z2',            3.300,  0.010, 'rem', True),  # R1085
   ('pac1934',   '0x17:3',   'ppvar_pp5000_kb_bl_l', 5.000,  0.020, 'rem', True),  # R1167

   ('pac1934',   '0x18:0',   'pp5000_z1',            5.000,  0.002, 'rem', True),  # R468
   ('pac1934',   '0x18:1',   'ppvar_sys_sd',         9.000,  0.010, 'rem', True),  # R209
   ('pac1934',   '0x18:2',   'pp3300_s5_sd',         3.300,  0.010, 'rem', True),  # R591
   ('pac1934',   '0x18:3',   'pp3300_s5',            3.300,  0.005, 'rem', True),  # R473

   ('pac1934',   '0x19:0',   'pp1800_fp_sens',       1.800,  0.500, 'rem', True),  # R632
   ('pac1934',   '0x19:1',   'pp3300_fp_x',          3.300,  0.500, 'rem', True),  # R999
   ('pac1934',   '0x19:2',   'ppvar_vbus_in',        15.000, 0.001, 'rem', True),  # R600
   ('pac1934',   '0x19:3',   'pp3300_dbg',           3.300,  0.010, 'rem', True),  # R1017
]
