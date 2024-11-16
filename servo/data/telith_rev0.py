# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Telith rev0 on-board adc map"""

# generates telith_rev0.xml
revs = [0]

# these devices are pac1934 (4-channels/i2c address) devices
inas = [
#     drvname      slv         name          nom     sense   mux  is_calib
    ("pac1934", "0x10:0", "PPAVR_VCCIN_AUX", 13.20,  0.005, "rem", True),  # R92087
    ("pac1934", "0x10:1", "PPAVR_BAT",       13.20,  0.01,  "rem", True),  # R32
    ("pac1934", "0x10:2", "PP3300_EC_Z1",    3.300,  0.01,  "rem", True),  # R645
    ("pac1934", "0x10:3", "PP1800_Z1",       1.800,  0.02,  "rem", True),  # R889
    ("pac1934", "0x11:0", "PP5000_Z1",       5.000,  0.005, "rem", True),  # R4209
    ("pac1934", "0x11:1", "PP0500_MEM_S3",   0.500,  0.005, "rem", True),  # R3901
    ("pac1934", "0x11:2", "PP1050_MEM_S3",   1.050,  0.002, "rem", True),  # R3909
    ("pac1934", "0x11:3", "PP1800_MEM_S3",   1.800,  0.02,  "rem", True),  # R3910
    ("pac1934", "0x12:0", "PP1800_SOC_S5",   1.800,  0.005, "rem", True),  # R890
    ("pac1934", "0x12:1", "PP3300_Z5",       3.300,  0.01,  "rem", True),  # R80
    ("pac1934", "0x12:2", "PP1200_WCAM_X",   1.200,  0.2,   "rem", True),  # R895
    ("pac1934", "0x12:3", "PP3300_SOC_S5",   3.300,  0.05,  "rem", True),  # R885
    ("pac1934", "0x13:0", "PP3300_S5",       3.300,  0.02,  "rem", True),  # R882
    ("pac1934", "0x13:1", "PP3300_WLAN",     3.300,  0.005, "rem", True),  # R886
    ("pac1934", "0x13:2", "PP3300_GSC_Z1",   3.300,  0.5,   "rem", True),  # R881
    ("pac1934", "0x13:3", "PP1800_S5",       1.800,  0.005, "rem", True),  # R716
    ("pac1934", "0x14:0", "PP3300_Z1",       3.300,  0.005, "rem", True),  # R880
    ("pac1934", "0x14:1", "PP3300_EDP_X",    3.300,  0.005, "rem", True),  # R12003
    ("pac1934", "0x14:2", "PPAVR_BL_PWR",    13.20,  0.01,  "rem", True),  # R92078
    ("pac1934", "0x14:3", "PP3300_TP",       3.300,  0.01,  "rem", True),  # R3931
    ("pac1934", "0x15:0", "PP1800_CODEC",    1.800,  0.01,  "rem", True),  # R4217
    ("pac1934", "0x15:1", "PPAVR_VBUS_IN",   20.00,  0.001, "rem", True),  # R600
    ("pac1934", "0x15:2", "PP5000_S5",       5.000,  0.005, "rem", True),  # R4215
    ("pac1934", "0x15:3", "PP5000_SPK_S5",   5.000,  0.01,  "rem", True),  # R91330
]
