# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Rull rev0 on-board adc map"""
# generates rull/roric/ruke_rev0.xml
revs = [0]
# these devices are pac1934 (4-channels/i2c address) devices
inas = [
    #     drvname      slv         name          nom     sense   mux  is_calib
    ("pac1934", "0x10:0", "PP1800_SOC_S5", 1.800, 0.01, "rem", True),  # R890
    ("pac1934", "0x10:1", "PP3300_GSC_Z1", 3.300, 0.02, "rem", True),  # R881
    ("pac1934", "0x10:2", "PP3300_EC_Z1", 3.300, 0.02, "rem", True),  # R645
    ("pac1934", "0x10:3", "PP1800_Z1", 1.800, 0.02, "rem", True),  # R889
    ("pac1934", "0x11:0", "PP3300_SSD_S5", 3.300, 0.01, "rem", True),  # R1075
    ("pac1934", "0x11:1", "PP3300_TCHPAD_S5", 3.300, 0.02, "rem", True),  # R884
    ("pac1934", "0x11:2", "CS_PPVAR_BAT", 13.20, 0.005, "rem", True),  # R32
    ("pac1934", "0x11:3", "PP5000_Z1", 5.000, 0.005, "rem", True),  # R94752
    ("pac1934", "0x12:0", "PP3300_SOC_S5", 3.300, 0.02, "rem", True),  # R885
    ("pac1934", "0x12:1", "PP1800_MEM_S5", 1.800, 0.01, "rem", True),  # R951
    ("pac1934", "0x12:2", "PP3300_EMMC_S5", 3.300, 0.02, "rem", True),  # R883
    ("pac1934", "0x13:0", "PP3300_Z1", 3.300, 0.005, "rem", True),  # R94757
    ("pac1934", "0x13:1", "PP3300_S5", 3.300, 0.01, "rem", True),  # R882
    ("pac1934", "0x13:2", "PP3300_WLAN_X", 3.300, 0.01, "rem", True),  # R886
    ("pac1934", "0x13:3", "PP3300_Z5", 3.300, 0.01, "rem", True),  # R80
    ("pac1934", "0x14:0", "PP0500_MEM_S3", 0.500, 0.02, "rem", True),  # R94751
    ("pac1934", "0x14:1", "PP3300_EDP_X_OUT", 3.300, 0.02, "rem", True),  # R12003
    ("pac1934", "0x14:2", "PPVAR_BL_PWR", 13.20, 0.02, "rem", True),  # R91271
    ("pac1934", "0x14:3", "PPAVR_VBUS_IN", 20.00, 0.01, "rem", True),  # R3409
    ("pac1934", "0x15:0", "PP5000_SPK_S5", 5.000, 0.02, "rem", True),  # R91330
    ("pac1934", "0x15:1", "PP1800_CPVDD_S5", 1.800, 0.01, "rem", True),  # R9040
    ("pac1934", "0x15:2", "PP1800_S5", 1.800, 0.005, "rem", True),  # R94754
    ("pac1934", "0x15:3", "PP5000_S5", 5.000, 0.005, "rem", True),  # XW4219
    ("pac1934", "0x17:0", "PP2500_3300_UFS", 2.500, 0.02, "rem", True),  # R1099
    ("pac1934", "0x17:1", "PP1200_UFS", 1.200, 0.02, "rem", True),  # R128_2
    ("pac1934", "0x17:2", "PP1050_MEM_S3", 1.050, 0.005, "rem", True),  # R94749
    ("pac1934", "0x17:3", "PP1800_MEM_S3", 1.800, 0.02, "rem", True),  # R94748
    ("pac1934", "0x1a:0", "VAR_VCCCORE1_VIN", 13.20, 0.01, "rem", True),  # R94740
    ("pac1934", "0x1a:1", "VAR_VCCCORE2_VIN", 13.20, 0.01, "rem", True),  # R94745
    ("pac1934", "0x1a:2", "PRVAR_VCCGT_VIN", 13.20, 0.01, "rem", True),  # R94744
    ("pac1934", "0x1a:3", "PRVAR_SYS_VCCIN_AUX", 13.20, 0.011, "rem", True),  # R94741
]
