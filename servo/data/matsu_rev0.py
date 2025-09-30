# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# these devices are pac1954 devices
inas = [
    #    drvname   addr:port   name               nom     sense       mux   is_calib
    ("pac1954", "0x10:0", "PP1800_Z1", 1.800, 0.100, "rem", True),  # R1090
    ("pac1954", "0x10:1", "PP3300_SOC_S5", 3.300, 0.005, "rem", True),  # R109
    ("pac1954", "0x10:2", "PP1800_SOC_S5", 1.800, 0.005, "rem", True),  # R108
    ("pac1954", "0x10:3", "PP1500_RTC_Z5", 1.500, 0.500, "rem", True),  # R1816
    ("pac1954", "0x11:0", "PP3300_Z5", 3.300, 0.010, "rem", True),  # R1078
    ("pac1954", "0x11:1", "PP3300_Z1", 3.300, 0.100, "rem", True),  # R1088
    # ("pac1954", "0x11:2", "PP5000_KB_BL", 5.000, 0.000, "rem", True),  # R5192
    # ("pac1954", "0x11:3", "PP3300_TCHPAD", 3.300, 0.000, "rem", True),  # R5188
    ("pac1954", "0x12:0", "PP1800_S5", 1.800, 0.003, "rem", True),  # R1727
    ("pac1954", "0x12:1", "PP3300_SSD_S5", 3.300, 0.005, "rem", True),  # R510
    # ("pac1954", "0x12:2", "PP3300_WLAN_S5", 3.300, 0.000, "rem", True),  # R1429
    ("pac1954", "0x12:3", "PPVAR_SYS_GT", 11.100, 0.001, "rem", True),  # PR2
    ("pac1954", "0x13:0", "PPVAR_SYS_PCORE", 11.100, 0.001, "rem", True),  # PR1
    ("pac1954", "0x13:1", "PPVAR_SYS_EDP", 11.100, 0.050, "rem", True),  # R1672
    ("pac1954", "0x13:2", "PPVAR_SYS_LPECORE", 5.000, 0.001, "rem", True),  # PR4
    ("pac1954", "0x13:3", "PP0770_SOC_S3", 0.770, 0.002, "rem", True),  # R1001
    ("pac1954", "0x14:0", "PP1800_MEM", 1.800, 0.010, "rem", True),  # RS5
    ("pac1954", "0x14:1", "PP0520_MEM_S3", 0.520, 0.010, "rem", True),  # RS15
    # ("pac1954", "0x14:2", "PP5000_FAN_X", 5.000, 0.000, "rem", True),  # R5209
    ("pac1954", "0x14:3", "PP1065_MEM", 1.065, 0.001, "rem", True),  # R1561
    ("pac1954", "0x15:0", "PP3300_UCAM_X", 3.300, 0.01, "rem", True),  # R1661
    ("pac1954", "0x15:1", "PP3300_PD_Z1", 3.300, 0.010, "rem", True),  # R1207
    ("pac1954", "0x15:2", "PP3300_EDP_X", 3.300, 0.02, "rem", True),  # R1673
    ("pac1954", "0x15:3", "PP3300_TCHSCR_X", 3.300, 0.02, "rem", True),  # R1674
    ("pac1954", "0x16:0", "PP1800_GSC_Z1", 1.800, 0.100, "rem", True),  # R1322
    ("pac1954", "0x16:1", "PP3300_EC_Z1", 3.300, 0.100, "rem", True),  # R802
    ("pac1954", "0x16:2", "PPVAR_VBUS_IN", 11.100, 0.010, "rem", True),  # R430
    ("pac1954", "0x16:3", "PP1800_EC_Z1", 1.800, 0.100, "rem", True),  # R2043
    ("pac1954", "0x17:0", "PP0770_SOC_S5", 0.770, 0.002, "rem", True),  # R1813
    ("pac1954", "0x17:1", "PP1250_SOC_S5", 1.250, 0.010, "rem", True),  # R2154
    ("pac1954", "0x17:2", "PP5000_S5", 5.000, 0.001, "rem", True),  # R1828
    ("pac1954", "0x17:3", "PPVAR_SYS_SA", 11.100, 0.001, "rem", True),  # PR3
    ("pac1954", "0x18:1", "PP3300_GSC_Z1", 3.300, 0.100, "rem", True),  # R417
    ("pac1954", "0x18:2", "PPVAR_BAT", 11.100, 0.005, "rem", True),  # R448
    # ("pac1954", "0x19:0", "PP2500_3300_UFS_VCC", 3.300, 0.000, "rem", True),  # R5310
    ("pac1954", "0x19:1", "PP3300_S5", 3.300, 0.005, "rem", True),  # RS1
    ("pac1954", "0x19:2", "PP1800_UFS_S5", 1.800, 0.01, "rem", True),  # R5316
    # ("pac1954", "0x19:3", "PP1200_UFS_S0", 1.200, 0.000, "rem", True),  # R5311
]
