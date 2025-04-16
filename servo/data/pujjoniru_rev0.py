# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Pujjoniru rev0 on-board adc map"""

# generates pujjoniru_rev0
revs = [0]

# these devices are pac1934 (4-channels/i2c address) devices
inas = [
    #     drvname      slv         name          nom     sense   mux  is_calib
    ("pac1934", "0x10:0", "PP1800_SOC_S5", 1.800, 0.01, "rem", True),  # R890
    ("pac1934", "0x10:1", "PP3300_GSC_Z1", 3.300, 0.02, "rem", True),  # R881
    ("pac1934", "0x10:2", "PP2500_3300_UFS", 3.300, 0.02, "rem", True),  # R1128
    ("pac1934", "0x10:3", "PP1800_UFS", 1.800, 0.02, "rem", True),  # R1101
    ("pac1934", "0x11:0", "PP3300_TCHPAD_S5", 3.300, 0.02, "rem", True),  # R884
    ("pac1934", "0x11:1", "PP1800_Z1", 1.800, 0.02, "rem", True),  # R889
    ("pac1934", "0x11:2", "PP1800_S5", 1.800, 0.01, "rem", True),  # R94755
    ("pac1934", "0x11:3", "PP3300_WLAN_X", 3.300, 0.01, "rem", True),  # R886
    ("pac1934", "0x12:0", "PP5000_S5", 5.000, 0.01, "rem", True),  # R4220
    ("pac1934", "0x12:1", "CS_KB_BL", 5.000, 0.02, "rem", True),  # R8457
    ("pac1934", "0x12:2", "CS_PP3300_S5_SD", 3.300, 0.01, "rem", True),  # R4512
    ("pac1934", "0x12:3", "PP5000_Z1", 5.000, 0.01, "rem", True),  # R94753
    ("pac1934", "0x14:0", "PP0500_MEM_S3", 0.520, 0.01, "rem", True),  # R94751
    ("pac1934", "0x14:1", "PP3300_EDP_X_OUT", 3.300, 0.02, "rem", True),  # R12003
    ("pac1934", "0x14:2", "PPVAR_BL_PWR", 11.30, 0.005, "rem", True),  # R4450
    ("pac1934", "0x14:3", "CS_PPAVR_VBUS_IN", 20.00, 0.01, "rem", True),  # R3409
    ("pac1934", "0x13:0", "PP3300_Z5", 3.300, 0.01, "rem", True),  # R80
    ("pac1934", "0x13:1", "PP3300_Z1", 3.300, 0.01, "rem", True),  # R94756
    ("pac1934", "0x13:2", "PP3300_S5", 3.300, 0.01, "rem", True),  # R882
    ("pac1934", "0x13:3", "CS_PPVAR_BAT", 11.30, 0.01, "rem", True),  # R32
    ("pac1934", "0x17:0", "PRVAR_VCCCORE1_VIN", 11.30, 0.002, "rem", True),  # R872
    ("pac1934", "0x17:1", "PRVAR_VCCCORE2_VIN", 11.30, 0.002, "rem", True),  # R874
    ("pac1934", "0x17:2", "PRVAR_VCCGT_VIN", 11.30, 0.002, "rem", True),  # R873
    ("pac1934", "0x17:3", "PRVAR_SYS_VCCIN_AUX", 11.30, 0.005, "rem", True),  # R92087
    ("pac1934", "0x16:0", "PP3300_EC_Z1", 3.300, 0.02, "rem", True),  # R645
    ("pac1934", "0x16:1", "PP3300_SOC_S5", 3.300, 0.01, "rem", True),  # R885
    ("pac1934", "0x16:2", "PP5000_FAN", 5.000, 0.01, "rem", True),  # R8529
    ("pac1934", "0x16:3", "PP3300_TCHSCR", 3.300, 0.02, "rem", True),  # R3931
    ("pac1934", "0x15:1", "PP1050_MEM_S3", 1.050, 0.01, "rem", True),  # R94750
    ("pac1934", "0x15:3", "PP1800_MEM_S3", 1.800, 0.01, "rem", True),  # R94748
]
