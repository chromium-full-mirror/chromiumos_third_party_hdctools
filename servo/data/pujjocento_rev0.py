# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Pujjocento rev0 on-board adc map"""

# generates pujjocento/pujjoteenlo_rev0.xml
revs = [0]

# these devices are pac1934 (4-channels/i2c address) devices
inas = [
#     drvname      slv         name                 nom    sense   mux  is_calib
    ("pac1934", "0x13:0", "CS_PPVAR_BAT_P",         13.20, 0.01,  "rem", True),  # R32
    ("pac1934", "0x13:1", "PP3300_Z1_P",            3.300, 0.01,  "rem", True),  # R6416
    ("pac1934", "0x13:2", "CS_PPVAR_VBUS_IN_P",     20.00, 0.01,  "rem", True),  # R3409
    ("pac1934", "0x13:3", "PP5000_Z1_P",            13.20, 0.01,  "rem", True),  # R6406
    ("pac1934", "0x17:0", "PRVAR_VCCCORE1_VIN_P",   13.20, 0.01,  "rem", True),  # R6208
    ("pac1934", "0x17:1", "PRVAR_VCCCORE2_VIN_P",   13.20, 0.01,  "rem", True),  # R6210
    ("pac1934", "0x17:2", "PRVAR_VCCGT_VIN_P",      13.20, 0.01,  "rem", True),  # R6209
    ("pac1934", "0x17:3", "PRVAR_SYS_VCCIN_AUX_P",  13.20, 0.002, "rem", True),  # R6328
]
