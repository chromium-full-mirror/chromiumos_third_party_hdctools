# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# these devices are pac1954 devices
inas = [
    #    drvname   addr:port   name               nom     sense       mux   is_calib
    ("pac1954", "0x10:0", "PP0P77_SOC_IN", 11.100, 0.010, "rem", True),  # R380
    ("pac1954", "0x10:1", "PPVAR_VCCSA_IN", 11.100, 0.010, "rem", True),  # R379
    ("pac1954", "0x10:2", "PP1250_SOC", 1.250, 0.010, "rem", True),  # R875
    ("pac1954", "0x10:3", "PP0P77_SOC", 0.770, 0.002, "rem", True),  # R911
    ("pac1954", "0x11:0", "PP1065_MEM", 1.065, 0.003, "rem", True),  # R1181
    ("pac1954", "0x11:1", "PP1800_MEM", 1.800, 0.010, "rem", True),  # RS5
    ("pac1954", "0x11:2", "PP1800_S5", 1.800, 0.003, "rem", True),  # R866
    ("pac1954", "0x11:3", "PP0500_MEM_S3", 0.500, 0.001, "rem", True),  # RS4
    ("pac1954", "0x12:0", "PPVAR_VCCCORE_PH1", 1.650, 0.002, "rem", True),  # R906
    ("pac1954", "0x12:1", "PP3300_S5", 3.300, 0.005, "rem", True),  # R590
    ("pac1954", "0x12:2", "PP3300_Z5", 3.300, 0.010, "rem", True),  # R1085
    ("pac1954", "0x12:3", "PP5000_Z1", 5.000, 0.005, "rem", True),  # R591
    ("pac1954", "0x13:0", "PP3300_FCAM_X", 3.300, 0.010, "rem", True),  # R58
    ("pac1954", "0x13:1", "PP1800_TCHSCR_X", 1.800, 0.020, "rem", True),  # R990
    ("pac1954", "0x13:2", "PP3300_EDP_X", 3.300, 0.020, "rem", True),  # R657
    ("pac1954", "0x13:3", "PP3300_TCHSCR_X", 3.300, 0.020, "rem", True),  # R658
    ("pac1954", "0x14:0", "PP1800_EC_Z1", 1.800, 0.010, "rem", True),  # R699
    ("pac1954", "0x14:1", "PPVAR_VCCGT_IN", 1.500, 0.010, "rem", True),  # R378
    ("pac1954", "0x14:2", "PP3300_Z1", 3.300, 0.100, "rem", True),  # R553
    ("pac1954", "0x14:3", "PP3300_EC_Z1", 3.300, 0.010, "rem", True),  # R700
    ("pac1954", "0x15:0", "PP1800_FP_X", 1.800, 0.500, "rem", True),  # R124
    ("pac1954", "0x15:1", "PP3300_FP_X", 3.300, 0.500, "rem", True),  # R123
    ("pac1954", "0x15:2", "PP5000_TCHPAD_X", 5.000, 0.010, "rem", True),  # R16
    ("pac1954", "0x15:3", "PPVAR_VCCCORE_PH2", 1.650, 0.002, "rem", True),  # R907
    ("pac1954", "0x16:0", "PP3300_WWAN_X", 3.300, 0.005, "rem", True),  # R235
    ("pac1954", "0x16:1", "PP3300_GSC_Z1", 3.300, 0.010, "rem", True),  # R415
    ("pac1954", "0x16:2", "PP3300_SSD_X", 3.300, 0.005, "rem", True),  # R236
    ("pac1954", "0x16:3", "PP3300_HDMI_X", 3.300, 0.020, "rem", True),  # R983
    ("pac1954", "0x17:0", "PP3300_WLAN_X", 3.300, 0.010, "rem", True),  # R873
    ("pac1954", "0x17:1", "PP1800_GSC_Z1", 1.800, 0.010, "rem", True),  # R414
    ("pac1954", "0x17:2", "PP1500_RTC_Z5", 1.500, 0.500, "rem", True),  # R832
    ("pac1954", "0x17:3", "PP5000_HDMI_X", 5.000, 0.010, "rem", True),  # R695
    ("pac1954", "0x18:0", "PP3300_SD", 3.300, 0.010, "rem", True),  # R143
    ("pac1954", "0x18:1", "PPVAR_SYS_SD", 11.100, 0.010, "rem", True),  # R144
    ("pac1954", "0x18:2", "PPVAR_VBUS_IN", 20.000, 0.001, "rem", True),  # R904
    ("pac1954", "0x18:3", "PP5000_FAN", 5.000, 0.010, "rem", True),  # R939
    ("pac1954", "0x19:0", "PPVAR_SYS", 11.100, 0.001, "rem", True),  # R905
    ("pac1954", "0x19:2", "PPVAR_VCCSA", 1.500, 0.002, "rem", True),  # R912
    ("pac1954", "0x19:3", "PPVAR_VCCCORE_IN", 11.100, 0.010, "rem", True),  # R399
    ("pac1954", "0x1A:0", "PP1800_UWB_DIG_X", 1.800, 0.100, "rem", True),  # R1051
    ("pac1954", "0x1A:1", "PP3300_TCHPAD_X", 3.300, 0.020, "rem", True),  # R15
    ("pac1954", "0x1A:2", "PPVAR_VCCGT_PH1", 1.500, 0.002, "rem", True),  # R909
    ("pac1954", "0x1A:3", "PP1250_SOC_IN", 11.100, 0.025, "rem", True),  # R448
    ("pac1954", "0x1B:0", "PP3300_USB_Z1", 3.300, 0.100, "rem", True),  # R655
    ("pac1954", "0x1B:1", "PP1065_SOC_S3", 1.065, 0.003, "rem", True),  # R1184
    ("pac1954", "0x1B:2", "PP1800_Z1", 1.800, 0.100, "rem", True),  # R988
    ("pac1954", "0x1B:3", "PPVAR_SYS_EDP", 11.100, 0.005, "rem", True),  # R231
    ("pac1954", "0x1C:0", "PP1200_WCAM_X", 1.200, 0.010, "rem", True),  # R1151
    ("pac1954", "0x1C:1", "PP1800_WCAM_X", 1.800, 0.010, "rem", True),  # R1152
    ("pac1954", "0x1C:2", "PP3000_WCAM_VCM_X", 3.000, 0.010, "rem", True),  # R1153
    ("pac1954", "0x1C:3", "PP2800_WCAM_X", 2.800, 0.010, "rem", True),  # R1154
    ("pac1954", "0x1D:0", "PP1800_S5_IN", 11.100, 0.001, "rem", True),  # R865
    ("pac1954", "0x1D:1", "PP1800_SOC_S5", 1.800, 0.010, "rem", True),  # R336
    ("pac1954", "0x1D:2", "PP3300_S5_IN", 11.100, 0.001, "rem", True),  # R864
    ("pac1954", "0x1D:3", "PP3300_SOC_S5", 3.300, 0.010, "rem", True),  # R335
    ("pac1954", "0x1E:0", "PP3300_Z5_IN", 11.100, 0.010, "rem", True),  # R833
    ("pac1954", "0x1E:1", "PP5000_Z1_IN", 11.100, 0.001, "rem", True),  # R867
    ("pac1954", "0x1E:2", "PP1800_USB_S5", 1.800, 0.010, "rem", True),  # R619
    ("pac1954", "0x1E:3", "PP3300_USB_S5", 3.300, 0.010, "rem", True),  # R618
]
