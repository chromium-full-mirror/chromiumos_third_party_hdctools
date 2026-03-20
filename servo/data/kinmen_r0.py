# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# these devices are pac1954 devices
inas = [
    #    drvname   addr:port   name               nom     sense       mux   is_calib
    ("pac1954", "0x10:1", "PP1800_EC_Z1", 1.800, 0.100, "rem", True),  # R1233
    ("pac1954", "0x10:2", "PP1800_Z1", 1.800, 0.100, "rem", True),  # R1090
    ("pac1954", "0x10:3", "PPVAR_BAT", 11.100, 0.005, "rem", True),  # R831
    ("pac1954", "0x11:0", "PP3300_Z5", 3.300, 0.010, "rem", True),  # R1078
    ("pac1954", "0x11:1", "PP1800_S5", 1.800, 0.003, "rem", True),  # R15
    ("pac1954", "0x11:3", "PP1800_SOC_S5", 1.800, 0.010, "rem", True),  # R153
    ("pac1954", "0x12:0", "PP3300_FCAM_X", 3.300, 0.010, "rem", True),  # R1058
    ("pac1954", "0x12:1", "PP3300_SOC_S5", 3.300, 0.010, "rem", True),  # R1565
    ("pac1954", "0x12:2", "PP1500_RTC_Z5", 1.500, 0.500, "rem", True),  # R1074
    ("pac1954", "0x12:3", "PPVAR_SYS_EDP", 11.100, 0.005, "rem", True),  # R381
    ("pac1954", "0x13:1", "PPVAR_VCCCORE_IN", 11.100, 0.001, "rem", True),  # R1675
    ("pac1954", "0x13:2", "PP5000_FAN", 5.000, 0.010, "rem", True),  # R436
    ("pac1954", "0x13:3", "PP5000_IMVP_S5", 5.000, 0.100, "rem", True),  # R1452
    ("pac1954", "0x14:1", "PP3300_DBG", 3.300, 0.010, "rem", True),  # R1092
    ("pac1954", "0x14:2", "PP1065_SOC_S3", 1.065, 0.001, "rem", True),  # R1561
    ("pac1954", "0x14:3", "PP0520_MEM_S3", 0.520, 0.002, "rem", True),  # RS6
    ("pac1954", "0x15:0", "PP3300_EDP_X", 3.300, 0.020, "rem", True),  # R1066
    ("pac1954", "0x15:1", "PP3300_Z5_IN", 3.300, 0.010, "rem", True),  # R1071
    ("pac1954", "0x15:2", "PP3300_TCHSCR_X", 3.300, 0.020, "rem", True),  # R1067
    ("pac1954", "0x16:0", "PP3300_EC_Z1", 3.300, 0.100, "rem", True),  # R1333
    ("pac1954", "0x16:1", "PP3300_Z1", 3.300, 0.100, "rem", True),  # R1088
    ("pac1954", "0x16:2", "PP1800_EC_S5", 1.800, 0.100, "rem", True),  # R635
    ("pac1954", "0x16:3", "PP3300_GSC_Z1", 3.300, 0.100, "rem", True),  # R264
    ("pac1954", "0x17:0", "PPVAR_VBUS_IN", 11.100, 0.001, "rem", True),  # R806
    ("pac1954", "0x17:1", "PP1800_GSC_Z1", 1.800, 0.100, "rem", True),  # R263
    ("pac1954", "0x17:3", "PP5000_S5", 5.000, 0.001, "rem", True),  # R1426
    ("pac1954", "0x18:0", "PP1800_MEM_S3", 1.800, 0.010, "rem", True),  # RS5
    ("pac1954", "0x18:2", "PP3300_S5", 3.300, 0.005, "rem", True),  # RS1
    ("pac1954", "0x19:0", "PP1250_SOC_S5", 1.250, 0.010, "rem", True),  # PR116
    ("pac1954", "0x19:1", "PP1250_SOC_IN", 1.250, 0.020, "rem", True),  # PR111
    ("pac1954", "0x19:2", "PP0700_SOC_S3", 0.700, 0.002, "rem", True),  # R1001
    ("pac1954", "0x19:3", "PP0700_SOC_S5", 0.700, 0.002, "rem", True),  # PR94
    ("pac1954", "0x1A:1", "PP3300_SSD_X", 3.300, 0.005, "rem", True),  # R510
    ("pac1954", "0x1B:0", "VIN_PPVAR_VCCLPECORE", 11.100, 0.001, "rem", True),  # R1678
    ("pac1954", "0x1B:1", "VIN_PPVAR_VCCGT", 11.100, 0.001, "rem", True),  # R1676
    ("pac1954", "0x1B:2", "VIN_PPVAR_VCCCORE_PH1", 11.100, 0.001, "rem", True),  # R1674
    ("pac1954", "0x1B:3", "VIN_PPVAR_VCCSA", 11.100, 0.001, "rem", True),  # R1677
]
