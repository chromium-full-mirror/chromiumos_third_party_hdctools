# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""c1nv rev0 on-board adc map"""

# generates c1nv_rev0.xml
revs = [0]

# test devices are [pac1934] devices
inas = [
    #  drvname       addr:port  name                        nom     sense   mux    is_calib
    ("pac1934", "0x11:0", "+4P6V_VREG_ELVDD", 4.600, 0.010, "rem", True),  # RV10758
    ("pac1934", "0x11:1", "VCC_SENSE_9P06VB_VBATT", 9.060, 0.005, "rem", True),  # PRB03
    ("pac1934", "0x11:2", "+3V_VREG_EDP", 3.300, 0.010, "rem", True),  # RV9921
    (
        "pac1934",
        "0x12:2",
        "VCC_SENSE_0P7V_VREG_L4F0",
        0.752,
        0.010,
        "rem",
        True,
    ),  # PR1182
    ("pac1934", "0x13:0", "+9P06_VB", 9.060, 0.020, "rem", True),  # RA2
    (
        "pac1934",
        "0x13:1",
        "VCC_SENSE_1P8V_VREG_L15B0",
        1.800,
        0.010,
        "rem",
        True,
    ),  # PR1177
    (
        "pac1934",
        "0x13:2",
        "VCC_SENSE_1P2V_VREG_L18B0",
        1.200,
        0.010,
        "rem",
        True,
    ),  # PR1178
    (
        "pac1934",
        "0x13:3",
        "VCC_SENSE_1P8V_VREG_L3H0",
        1.800,
        0.010,
        "rem",
        True,
    ),  # PRI53
    ("pac1934", "0x16:0", "VCC_SENSE_0P9VS_0", 0.900, 0.005, "rem", True),  # PR1166
    ("pac1934", "0x16:1", "VCC_SENSE_0P9VS_1", 0.900, 0.005, "rem", True),  # PR1150
    ("pac1934", "0x16:2", "+3V_VDD_HMLT_M2", 3.300, 0.010, "rem", True),  # R10784
    ("pac1934", "0x16:3", "+3V_VREG_FP", 3.300, 0.020, "rem", True),  # R8821
    ("pac1934", "0x17:0", "+3V_EC_Z1_R", 3.300, 0.020, "rem", True),  # RK855
    ("pac1934", "0x17:1", "+3V_GSC_Z1", 3.300, 0.020, "rem", True),  # RK602
    ("pac1934", "0x17:2", "VCC_SENSE_3VALW_Z1", 3.300, 0.001, "rem", True),  # PR307
    ("pac1934", "0x17:3", "VCC_SENSE_5VALW", 5.000, 0.001, "rem", True),  # PR510
    ("pac1934", "0x19:0", "VCC_SENSE_2P5V_UFS", 2.500, 0.005, "rem", True),  # RS59
    ("pac1934", "0x19:1", "VCC_SENSE_1P2V_UFS", 1.200, 0.005, "rem", True),  # RS61
    ("pac1934", "0x19:2", "+3V_CAM", 3.300, 0.010, "rem", True),  # RV10832
]
