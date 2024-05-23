# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# these devices are pac1934 devices
inas = [
    # drvname  addr:port   name         nom  sense  mux  is_calib
    ("pac1934", "0x10:0", "PP3300_DBG", 3.3, 0.01, "rem", True),  # R30
    ("pac1934", "0x10:1", "PP3300_GSC_Z1", 3.3, 0.005, "rem", True),  # R993
    ("pac1934", "0x10:2", "PP5000_PD_Z1", 5, 0.005, "rem", True),  # R985
    ("pac1934", "0x10:3", "PP5000_Z1", 5, 0.001, "rem", True),  # R560
    ("pac1934", "0x11:0", "PP3300_SOC_S5", 3.3, 0.005, "rem", True),  # R109
    ("pac1934", "0x11:1", "PP1800_SOC_S5", 1.8, 0.005, "rem", True),  # R108
    ("pac1934", "0x11:2", "PP1800_S5", 1.8, 0.002, "rem", True),  # R171
    ("pac1934", "0x11:3", "PP5000_Z1_1800_S5", 5, 0.02, "rem", True),  # R69
    ("pac1934", "0x12:0", "PP3300_EC_Z1", 3.3, 0.1, "rem", True),  # R802
    ("pac1934", "0x12:1", "PP1200_DRAM", 1.2, 0.002, "rem", True),  # R60300
    ("pac1934", "0x12:2", "PP2500_DRAM", 2.5, 0.01, "rem", True),  # R60360
    ("pac1934", "0x12:3", "PP0600_DRAM", 0.6, 0.01, "rem", True),  # R60350
    ("pac1934", "0x13:0", "PP3300_EDP_X", 3.3, 0.02, "rem", True),  # R657
    ("pac1934", "0x13:1", "PPVAR_SYS_EDP", 13.2, 0.05, "rem", True),  # R559
    ("pac1934", "0x13:2", "PP3300_SSD_S5", 3.3, 0.005, "rem", True),  # R221
    ("pac1934", "0x13:3", "PP3300_PD_PIN32", 3.3, 0.01, "rem", True),  # R986
    ("pac1934", "0x14:0", "PP3300_WLAN_X", 3.3, 0.005, "rem", True),  # R294
    ("pac1934", "0x14:1", "PP3300_TCHPAD", 3.3, 0.02, "rem", True),  # R232
    ("pac1934", "0x14:2", "PP5000_FAN_X", 5, 0.005, "rem", True),  # R1017
    ("pac1934", "0x14:3", "PPVAR_VBUS_IN", 20, 0.01, "rem", True),  # R430
    ("pac1934", "0x15:0", "PP3300_UCAM_X", 3.3, 0.05, "rem", True),  # R67
    ("pac1934", "0x15:1", "PP3300_TCHSCR_X", 3.3, 0.02, "rem", True),  # R658
    ("pac1934", "0x15:2", "PPVAR_SYS_VCCIN_AUX", 1.8, 0.002, "rem", True),  # R692
    ("pac1934", "0x15:3", "PPVAR_VCCIN_AUX", 1.8, 0.001, "rem", True),  # R1274
    ("pac1934", "0x16:0", "PP3300_Z5", 3.3, 0.3, "rem", True),  # R904
    ("pac1934", "0x16:1", "PPVAR_SYS_5000_Z1", 5, 0.01, "rem", True),  # R597
    ("pac1934", "0x16:2", "PP3300_S5", 3.3, 0.001, "rem", True),  # R656
    ("pac1934", "0x16:3", "PP3300_Z1", 3.3, 0.001, "rem", True),  # R634
    ("pac1934", "0x17:0", "PPVAR_SYS_KB_BL", 5, 0.02, "rem", True),  # R1167
    ("pac1934", "0x17:1", "PP1800_EC_S5", 1.8, 0.1, "rem", True),  # R635
    ("pac1934", "0x17:2", "PPVAR_SYS_PP3300_Z1", 13.2, 0.001, "rem", True),  # R1009
    ("pac1934", "0x17:3", "PP3300_RTC", 3.3, 1, "rem", True),  # R629
    ("pac1934", "0x19:0", "PP5000_CODEC_PVDD_S5", 5, 0.005, "rem", True),  # R1049
    ("pac1934", "0x19:1", "PP5000_CODEC_S5", 5, 0.1, "rem", True),  # R1050
    ("pac1934", "0x19:2", "PP1800_CODEC_HDA_S5", 1.8, 0.1, "rem", True),  # R923
    ("pac1934", "0x19:3", "PP3300_CODEC_S5", 3.3, 0.1, "rem", True),  # R1048
    ("pac1934", "0x1A:0", "PPVAR_SYS_VCCCORE_GT", 13.2, 0.005, "rem", True),  # R1137
    ("pac1934", "0x1A:1", "PPVAR_SYS_VCCGT", 13.2, 0.005, "rem", True),  # R1139
    ("pac1934", "0x1A:3", "PPVAR_BAT", 13.2, 0.005, "rem", True),  # R448
]
