# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

revs = [0]
inas = [
    # drvname      slv        name                          nom      sense  mux    is_calib refdes
    ("pac1934", "0x10:0", "3v_vdd_hmlt_m2p", 3.300, 0.01, "rem", True),  # R6607
    ("pac1934", "0x10:1", "1p2v_wsa0_vddio", 1.200, 0.02, "rem", True),  # RA6101
    ("pac1934", "0x10:2", "3valwp", 3.300, 0.002, "rem", True),  # PR308
    ("pac1934", "0x10:3", "3v_gsc_z1", 3.300, 0.02, "rem", True),  # RK602
    ("pac1934", "0x11:0", "3p8v_vph_pwr_1b_gfx", 3.800, 0.002, "rem", True),  # PR174
    ("pac1934", "0x11:1", "2p9v_vreg_l7m", 2.900, 0.02, "rem", True),  # RV10715
    ("pac1934", "0x11:2", "2p8v_vreg_l7b", 2.800, 0.01, "rem", True),  # PR1219
    ("pac1934", "0x11:3", "3p8v_vph_pwr_1b_apc0", 3.800, 0.002, "rem", True),  # PR168
    ("pac1934", "0x12:0", "0p8v_vreg_s7i_s8i", 0.800, 0.005, "rem", True),  # PR166
    ("pac1934", "0x12:1", "0p8v_vreg_s5i_s6i", 0.800, 0.005, "rem", True),  # PR164
    ("pac1934", "0x12:2", "0p9v_vreg_s1i", 0.900, 0.01, "rem", True),  # PR157
    ("pac1934", "0x12:3", "1p08v_vreg_s2i_s3i", 1.080, 0.005, "rem", True),  # PR158
    ("pac1934", "0x14:0", "0p75v_vreg_s6c", 0.750, 0.01, "rem", True),  # PR170
    ("pac1934", "0x14:1", "0p75v_vreg_s3c", 0.750, 0.01, "rem", True),  # PR171
    ("pac1934", "0x14:2", "0p71v_vreg_s7c_s8c", 0.710, 0.005, "rem", True),  # PR175
    ("pac1934", "0x14:3", "0p73v_vreg_s1c_s2c", 0.730, 0.005, "rem", True),  # PR173
    ("pac1934", "0x16:0", "8p8vb_disp_bl", 8.800, 0.1, "rem", True),  # R579
    ("pac1934", "0x16:1", "3v_vreg_edp", 3.300, 0.01, "rem", True),  # RV9921
    ("pac1934", "0x16:2", "vin_sm3201", 8.800, 0.01, "rem", True),  # PRO6
    ("pac1934", "0x16:3", "3v_vreg_ts", 3.300, 0.02, "rem", True),  # RV7804
    ("pac1934", "0x17:0", "3v_vreg_nvme", 3.300, 0.01, "rem", True),  # R6608
    ("pac1934", "0x17:1", "5valw", 5.000, 0.01, "rem", True),  # PR505
    ("pac1934", "0x17:2", "8p8vb_batt", 8.800, 0.005, "rem", True),  # PRB363
    ("pac1934", "0x17:3", "0p5v_vreg_s8d", 0.500, 0.01, "rem", True),  # PR155
    ("pac1934", "0x18:0", "1p8v_vdd_txrx_px", 1.800, 0.02, "rem", True),  # RA6003
    ("pac1934", "0x18:1", "1p8v_vdd_buck", 1.800, 0.02, "rem", True),  # RA6004
    ("pac1934", "0x18:2", "1p2v_vreg_l12b_sd", 1.200, 0.02, "rem", True),  # R10754
    ("pac1934", "0x18:3", "3v_ec_z1", 3.300, 2.2, "rem", True),  # RK845
    ("pac1934", "0x19:0", "3v_vreg_l9b", 3.300, 0.01, "rem", True),  # PR1214
    ("pac1934", "0x19:1", "0p9v_vreg_s4i", 0.900, 0.01, "rem", True),  # PR1212
    ("pac1934", "0x19:2", "2p8v_vreg_l6b", 2.800, 0.01, "rem", True),  # PR1213
    ("pac1934", "0x19:3", "3p8v_vph_pwr_1a_apc2", 3.800, 0.002, "rem", True),  # PR209
    ("pac1934", "0x1F:0", "1p2v_wsa1_vddio", 1.200, 0.02, "rem", True),  # RA6201
    ("pac1934", "0x1F:1", "8p8vb_vsys_wsa_l", 8.800, 0.01, "rem", True),  # RA9929
    ("pac1934", "0x1F:2", "1p8v_vreg_l3m", 1.800, 0.02, "rem", True),  # RV10713
    ("pac1934", "0x1F:3", "1p8v_vreg_l4m", 1.800, 0.02, "rem", True),  # RV10714
]
