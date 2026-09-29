# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# these devices are pac1934 devices
inas = [
    # drvname  addr:port   name         nom  sense  mux  is_calib
    ("pac1934", "0x10:0", "PPVAR_BAT", 15.4, 0.01, "rem", True),  # PR5020(inverse)
    ("pac1934", "0x10:1", "PPVAR_VBUS_IN", 20, 0.01, "rem", True),  # PR501
    ("pac1934", "0x10:2", "PP3300_Z5", 3.3, 0.01, "rem", True),  # PR640
    ("pac1934", "0x10:3", "PP3300_Z1", 3.3, 0.01, "rem", True),  # R4301
    ("pac1934", "0x11:0", "PP1800_Z1", 1.8, 0.01, "rem", True),  # R4305
    ("pac1934", "0x11:1", "PP5000_S5", 15.4, 0.005, "rem", True),  # PR6103
    ("pac1934", "0x11:2", "PP1800_S5", 15.4, 0.005, "rem", True),  # PR6308
    ("pac1934", "0x11:3", "PP3300_S5", 15.4, 0.005, "rem", True),  # PR6203
    ("pac1934", "0x12:0", "PP0770_SOC_S5", 15.4, 0.005, "rem", True),  # PR5829
    ("pac1934", "0x12:1", "PP1800_SOC_S5", 1.8, 0.01, "rem", True),  # R1400 (inverse)
    ("pac1934", "0x12:2", "PP3300_SOC_S5", 3.3, 0.01, "rem", True),  # R1401
    ("pac1934", "0x12:3", "PP1250_SOC_S5", 1.25, 0.01, "rem", True),  # PR5905
    ("pac1934", "0x13:0", "PPVAR_SYS_CORE", 15.4, 0.005, "rem", True),  # PR5408
    ("pac1934", "0x13:1", "PPVAR_VCCGT", 15.4, 0.005, "rem", True),  # PR5505
    ("pac1934", "0x13:2", "PPVAR_VCCSA", 15.4, 0.005, "rem", True),  # PR5605
    ("pac1934", "0x13:3", "PPVAR_VCCLPECORE", 15.4, 0.005, "rem", True),  # PR5708
    ("pac1934", "0x14:0", "PP0770_SOC_S3", 0.77, 0.01, "rem", True),  # PR5800
    ("pac1934", "0x14:1", "PP1800_MEM_S3", 1.8, 0.01, "rem", True),  # PR6000
    ("pac1934", "0x14:2", "PP1065_MEM_S3", 1.065, 0.005, "rem", True),  # PR6020
    ("pac1934", "0x14:3", "PP0520_MEM_S3", 0.5, 0.005, "rem", True),  # PR6010(inverse)
    ("pac1934", "0x15:0", "PP5000_IMVP_S5", 5.0, 0.1, "rem", True),  # PR5146
    ("pac1934", "0x15:3", "PP1500_RTC_Z5", 1.5, 0.01, "rem", True),  # R4308
    ("pac1934", "0x16:0", "PP3300_EC_Z1", 3.3, 0.01, "rem", True),  # R2650
    ("pac1934", "0x16:1", "PP1800_EC_Z1", 1.8, 0.01, "rem", True),  # R2649
    ("pac1934", "0x16:2", "PP3300_GSC_Z1", 3.3, 0.01, "rem", True),  # R2549
    ("pac1934", "0x16:3", "PP1800_GSC_Z1", 1.8, 0.01, "rem", True),  # R2548
    ("pac1934", "0x17:1", "PP5000_FAN_X", 5.0, 0.1, "rem", True),  # R4001
    ("pac1934", "0x17:2", "PP3300_WLAN_S5", 3.3, 0.01, "rem", True),  # R3115
    ("pac1934", "0x17:3", "PP3300_SSD_S5", 3.3, 0.01, "rem", True),  # R4345
    ("pac1934", "0x18:0", "PP1200_HDMI_S5", 1.2, 0.01, "rem", True),  # R3002(inverse)
    ("pac1934", "0x18:1", "PP3300_HDMI_S5", 3.3, 0.01, "rem", True),  # R3006
    ("pac1934", "0x18:2", "PP3300_USB_C_RT", 3.3, 0.02, "rem", True),  # R3600
    ("pac1934", "0x19:0", "PP5000_KB_BL", 5, 0.01, "rem", True),  # PR6610
    ("pac1934", "0x19:1", "PP3300_CAM_X", 3.3, 0.01, "rem", True),  # R4327
    ("pac1934", "0x19:2", "PP5000_LB_S5", 5, 0.01, "rem", True),  # PR4202
    ("pac1934", "0x1A:0", "PP5000_FPAD", 5, 0.01, "rem", True),  # R4318
    ("pac1934", "0x1A:1", "PP3300_FPAD_S5", 3.3, 0.02, "rem", True),  # R4353
    ("pac1934", "0x1A:2", "PP1800_FPAD", 1.8, 0.01, "rem", True),  # R4319
    ("pac1934", "0x1A:3", "PP3300_FP_X", 3.3, 0.01, "rem", True),  # R4311
    ("pac1934", "0x1B:0", "PP3300_EDP_X", 3.3, 0.01, "rem", True),  # R4325
    ("pac1934", "0x1B:1", "EDP_BL", 15.4, 0.01, "rem", True),  # PR6611
    ("pac1934", "0x1B:2", "PP3300_TCHSCR_X", 3.3, 0.01, "rem", True),  # R4324
]
