# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# generates ocicat_rev0
revs = [1]

# these devices are pac1954 devices
inas = [
    # drvname  addr:port   name         nom  sense  mux  is_calib
    ("pac1954", "0x10:0", "CS_PP3300_S5", 3.3, 0.005, "rem", True),  # R1001
    ("pac1954", "0x11:0", "CS_P1V1_MEM", 1.1, 0.01, "rem", True),  # R1000
    ("pac1954", "0x11:1", "CS_PPVAR_PCORE", 13.5, 0.01, "rem", True),  # R2063
    ("pac1954", "0x11:2", "CS_PP1250_SOC_S5", 1.25, 0.01, "rem", True),  # R1007
    ("pac1954", "0x11:3", "VAL_VIN_BULK_DRAM", 5.0, 0.005, "rem", True),  # R7004
    ("pac1954", "0x12:0", "CS_PP3300_WLAN", 3.3, 0.005, "rem", True),  # R1429
    ("pac1954", "0x12:1", "CS_PPVAR_LP_ECORE", 13.5, 0.01, "rem", True),  # R2065
    ("pac1954", "0x12:2", "CS_PP3300_SOC_S5", 3.3, 0.005, "rem", True),  # R109
    ("pac1954", "0x12:3", "CS_PP0770_SOC_S3", 0.77, 0.002, "rem", True),  # R1003
    ("pac1954", "0x13:0", "CS_PP1800_SOC_S5", 1.8, 0.005, "rem", True),  # R108
    ("pac1954", "0x13:1", "CS_PP5000_S5", 5.0, 0.005, "rem", True),  # R248
    ("pac1954", "0x13:2", "CS_PPVAR_VCCGT", 13.5, 0.01, "rem", True),  # R2064
    ("pac1954", "0x13:3", "CS_PP1500_RTC_Z5", 1.5, 0.05, "rem", True),  # R1816
    ("pac1954", "0x14:0", "CS_PPVAR_SYS_KB_BL", 5.0, 0.02, "rem", True),  # R119
    ("pac1954", "0x14:1", "CS_PPVAR_VCCSA", 13.5, 0.01, "rem", True),  # R2066
    ("pac1954", "0x14:2", "CS_PP3300_TCHPAD_S5", 3.3, 0.02, "rem", True),  # R1499
    ("pac1954", "0x14:3", "CS_PP3300_EC_Z1", 3.3, 0.1, "rem", True),  # R802
    ("pac1954", "0x15:0", "CS_PP0770_SOC_S5", 0.77, 0.01, "rem", True),  # R1813
    ("pac1954", "0x15:1", "CS_PP1800_EC_Z1", 1.8, 0.1, "rem", True),  # R2043
    ("pac1954", "0x15:2", "CS_PP1800_GSC_Z1", 1.8, 0.1, "rem", True),  # R1322
    ("pac1954", "0x15:3", "CS_PP3300_GSC_Z1", 3.3, 0.1, "rem", True),  # R417
    ("pac1954", "0x16:0", "CS_PP3300_UCAM_X", 3.3, 0.005, "rem", True),  # R1661
    ("pac1954", "0x16:1", "CS_PPVAR_SYS_EDP", 13.5, 0.01, "rem", True),  # R3012
    ("pac1954", "0x16:2", "CS_PPVAR_VBUS_IN", 13.5, 0.01, "rem", True),  # R60000
    ("pac1954", "0x16:3", "CS_PPVAR_BAT", 3.3, 0.005, "rem", True),  # 60001
    ("pac1954", "0x18:0", "CS_PP1800_CODEC_S5", 1.8, 0.02, "rem", True),  # R510
    ("pac1954", "0x18:1", "CS_PP5000_CODEC_S5", 5.0, 0.005, "rem", True),  # R514
    ("pac1954", "0x18:2", "CS_PP3300_SSD_S5", 3.3, 0.005, "rem", True),  # R1427
    ("pac1954", "0x18:3", "CS_PP5000_FAN_X", 5.0, 0.005, "rem", True),  # R4302
    ("pac1954", "0x19:0", "CS_PP3300_Z5", 3.3, 0.01, "rem", True),  # R1078
    ("pac1954", "0x19:1", "CS_PP3300_PD_Z1", 3.3, 0.01, "rem", True),  # R695
    ("pac1954", "0x19:2", "CS_PP1800_Z1", 1.8, 0.1, "rem", True),  # R1101
    ("pac1954", "0x19:3", "CS_PP3300_Z1", 3.3, 0.1, "rem", True),  # R1092
    ("pac1954", "0x1b:0", "CS_PP3300_UFS_S5", 3.3, 0.005, "rem", True),  # R1518
    ("pac1954", "0x1b:1", "CS_PP3300_EDP_X", 3.3, 0.02, "rem", True),  # R3024
    ("pac1954", "0x1b:2", "CS_PP1800_S5", 1.8, 0.01, "rem", True),  # R1727
    ("pac1954", "0x1b:3", "CS_PP3300_TCHSCR_X", 3.3, 0.02, "rem", True),  # R1674
]
