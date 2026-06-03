# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Generated from Mensa netlist mapping for Calypso program
revs = [0]
inas = [
    #  drvname     addr:port   name                           nom    sense    mux   is_calib
    ("pac1934", "0x10:0", "PP3800_VPH_PWR_MX_A", 3.800, 0.01000, "rem", True),  # PRK127
    ("pac1934", "0x10:1", "PP3800_VPH_PWR_MX_C", 3.800, 0.01000, "rem", True),  # PRK128
    (
        "pac1934",
        "0x10:2",
        "PP3800_VPH_PWR_NSP_2",
        3.800,
        0.00200,
        "rem",
        True,
    ),  # PRK129
    ("pac1934", "0x10:3", "PPVAR_BATT_VBATT", 8.800, 0.00500, "rem", True),  # PRB03
    (
        "pac1934",
        "0x1F:0",
        "PP3800_VPH_PWR_MX_APC0",
        3.800,
        0.01000,
        "rem",
        True,
    ),  # PRK134
    (
        "pac1934",
        "0x1F:1",
        "PP3800_VPH_PWR_DDR_VDD2H",
        3.800,
        0.01000,
        "rem",
        True,
    ),  # PRK137
    (
        "pac1934",
        "0x1F:2",
        "PP3800_VPH_PWR_DDR_2L",
        3.800,
        0.01000,
        "rem",
        True,
    ),  # PRK132
    (
        "pac1934",
        "0x1F:3",
        "PP3800_VPH_PWR_DDR_VDDQ",
        3.800,
        0.01000,
        "rem",
        True,
    ),  # PRK133
    ("pac1934", "0x11:0", "PP4600_VREG_ELVDD", 4.600, 0.01000, "rem", True),  # RV10758
    ("pac1934", "0x11:2", "PP3000_VREG_EDP", 3.000, 0.01000, "rem", True),  # RV9921
    (
        "pac1934",
        "0x11:3",
        "PP3800_VPH_PWR_VDD_APC1",
        3.800,
        0.00100,
        "rem",
        True,
    ),  # PRK120
    ("pac1934", "0x12:0", "PP1800_VREG_L3H0", 1.800, 0.01000, "rem", True),  # PRI53
    ("pac1934", "0x12:1", "PP3800_VPH_PWR_CX", 3.800, 0.01000, "rem", True),  # PRK123
    ("pac1934", "0x12:2", "PP0752_VREG_L4F0", 0.752, 0.01000, "rem", True),  # PR1182
    (
        "pac1934",
        "0x12:3",
        "PP3800_VPH_PWR_LPI_CX",
        3.800,
        0.01000,
        "rem",
        True,
    ),  # PRK124
    ("pac1934", "0x13:0", "PP8800_88VB_R", 8.800, 0.02000, "rem", True),  # RA2
    ("pac1934", "0x13:1", "PP1800_VREG_L15B0", 1.800, 0.01000, "rem", True),  # PR1177
    ("pac1934", "0x13:2", "PP1200_VREG_L18B0", 1.200, 0.01000, "rem", True),  # PR1178
    ("pac1934", "0x13:3", "PP3800_VPH_PWR_APC0", 3.800, 0.00200, "rem", True),  # PRK130
    (
        "pac1934",
        "0x16:0",
        "PP0900_VREG_RT0_CEXT",
        0.900,
        0.00500,
        "rem",
        True,
    ),  # PR1166
    (
        "pac1934",
        "0x16:1",
        "PP0900_VREG_RT1_CEXT",
        0.900,
        0.00500,
        "rem",
        True,
    ),  # PR1150
    ("pac1934", "0x16:2", "PP3000_VDD_HMLT_M2", 3.000, 0.01000, "rem", True),  # R10784
    ("pac1934", "0x16:3", "PP3000_VREG_FP", 3.000, 0.02000, "rem", True),  # R8821
    ("pac1934", "0x17:0", "PP3000_EC_Z1_R", 3.000, 0.02000, "rem", True),  # RK855
    ("pac1934", "0x17:1", "PP3000_GSC_Z1", 3.000, 0.02000, "rem", True),  # RK602
    ("pac1934", "0x17:2", "PP3000_3VALW_Z1", 3.000, 0.01000, "rem", True),  # PR307
    ("pac1934", "0x17:3", "PP5000_5VALW", 5.000, 0.00100, "rem", True),  # PR510
    (
        "pac1934",
        "0x18:0",
        "PP3800_VPH_PWR_MX_GFX",
        3.800,
        0.01000,
        "rem",
        True,
    ),  # PRK136
    (
        "pac1934",
        "0x18:1",
        "PP3800_VPH_PWR_VREG_GFX",
        3.800,
        0.00200,
        "rem",
        True,
    ),  # PRK135
    ("pac1934", "0x18:2", "PP3800_VPH_PWR_NSP1", 3.800, 0.01000, "rem", True),  # PRK125
    ("pac1934", "0x18:3", "PP3800_VPH_PWR_MM", 3.800, 0.01000, "rem", True),  # PRK126
    ("pac1934", "0x19:0", "PP2500_UFS_VCC", 2.500, 0.00500, "rem", True),  # RS59
    ("pac1934", "0x19:1", "PP1200_UFS_VCCQ", 1.200, 0.00500, "rem", True),  # RS61
    ("pac1934", "0x19:2", "PP3000_CAM", 3.000, 0.01000, "rem", True),  # RV10832
    (
        "pac1934",
        "0x19:3",
        "PP3800_VPH_PWR_MX_APC1",
        3.800,
        0.01000,
        "rem",
        True,
    ),  # PRK138
]
