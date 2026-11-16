# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# these devices are pac1934 devices
revs = [0]
inas = [
    #  drvname     addr:port   name                     nom         sense       mux   is_calib
    ("pac1934", "0x10:0", "VREG_L5B_0P752", 0.752, 0.010, "rem", True),  # RS4506
    ("pac1934", "0x10:1", "PPVAR_SYS", 13.200, 0.010, "rem", True),  # R3131
    ("pac1934", "0x10:2", "PPVAR_BATT_DISCHG", 13.200, 0.010, "rem", True),  # R3508
    ("pac1934", "0x10:3", "PP3300_WLAN", 3.300, 0.020, "rem", True),  # R5547
    ("pac1934", "0x11:0", "PP5000_Z1", 5.000, 0.005, "rem", True),  # R3310 R3311
    ("pac1934", "0x11:1", "PP5000_SPKR_L", 5.000, 0.020, "rem", True),  # RS8601
    ("pac1934", "0x11:2", "PP3300_PDC", 3.300, 0.020, "rem", True),  # RS6201
    ("pac1934", "0x11:3", "PP5000_HUB", 5.000, 0.020, "rem", True),  # RS9701
    ("pac1934", "0x12:0", "PP3300_Z1", 3.300, 0.010, "rem", True),  # R203
    ("pac1934", "0x12:1", "PP3300_GSC_Z1", 3.300, 0.020, "rem", True),  # RS8302
    ("pac1934", "0x12:2", "VPH_PWR", 3.800, 0.002, "rem", True),  # R5119
    ("pac1934", "0x12:3", "PPVAR_VBUS_IN", 20.000, 0.010, "rem", True),  # R3126
    ("pac1934", "0x13:0", "VREG_S2B_0P876", 0.876, 0.002, "rem", True),  # R4301
    ("pac1934", "0x13:1", "PP3300_UCAM", 3.300, 0.020, "rem", True),  # RS5901
    ("pac1934", "0x13:2", "VREG_S3B_S4B_S5B_0P752", 0.752, 0.002, "rem", True),  # R4401
    ("pac1934", "0x13:3", "PP3300_REDRIVER", 3.300, 0.020, "rem", True),  # RS6401
    ("pac1934", "0x14:0", "PP3300_EDP", 3.300, 0.010, "rem", True),  # RS5902
    ("pac1934", "0x14:1", "PP3300_TCHSCR", 3.300, 0.020, "rem", True),  # RS5903
    ("pac1934", "0x14:2", "PP3300_TCHPAD", 3.300, 0.020, "rem", True),  # RS7901
    ("pac1934", "0x14:3", "PP3300_EC_Z1", 3.300, 0.020, "rem", True),  # RS8202
    ("pac1934", "0x15:0", "VREG_S6C_S7C_S8C_0P752", 0.752, 0.002, "rem", True),  # R4003
    ("pac1934", "0x15:1", "VREG_S9C", 1.084, 0.002, "rem", True),  # R4001
    ("pac1934", "0x15:2", "VREG_S10C_0P752", 0.752, 0.002, "rem", True),  # R4004
    ("pac1934", "0x15:3", "VREG_S2C_S3C_S4C_0P752", 0.752, 0.002, "rem", True),  # R3901
    ("pac1934", "0x16:0", "PPVAR_EDP_BL", 13.200, 0.010, "rem", True),  # RS5904
    ("pac1934", "0x16:1", "VREG_L8B_0P904", 0.904, 0.010, "rem", True),  # RS4503
    ("pac1934", "0x16:2", "PP5000_SPKR_R", 5.000, 0.020, "rem", True),  # RS9801
    ("pac1934", "0x16:3", "VREG_S6B_0P752", 0.752, 0.002, "rem", True),  # R4402
    ("pac1934", "0x17:0", "VREG_L7B_2P5", 2.500, 0.010, "rem", True),  # RS4501
    ("pac1934", "0x17:1", "VREG_L3B_0P504", 0.504, 0.010, "rem", True),  # RS4504
    ("pac1934", "0x17:2", "VREG_L9B_1P2", 1.200, 0.010, "rem", True),  # RS4502
    ("pac1934", "0x17:3", "VREG_L18B_1P8_DDR", 1.800, 0.020, "rem", True),  # R2701
]
