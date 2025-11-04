# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# generates lapis_rev0.py
revs = [0]
inas = [
    # drvname      slv        name                    nom      sense  mux     is_calib
    ("pac1934", "0x10:0", "BAT", 8.800, 0.005, "rem", True),  # PS8902
    ("pac1934", "0x10:1", "AC_SOURCE_IN", 20.000, 0.005, "rem", True),  # CR8901
    ("pac1934", "0x10:2", "3VA", 3.300, 0.02, "rem", True),  # SR9702
    ("pac1934", "0x10:3", "3VA_EC_CR8802", 3.300, 0.02, "rem", True),  # CR8802
    ("pac1934", "0x11:0", "1P8VA_EC_SR4002", 1.800, 0.02, "rem", True),  # SR4002
    ("pac1934", "0x11:1", "5VSUS", 5.000, 0.005, "rem", True),  # SR8704
    ("pac1934", "0x11:2", "1P8VSUS_SR8301", 1.800, 0.02, "rem", True),  # SR8301
    ("pac1934", "0x11:3", "3VSUS_SR8702", 3.300, 0.005, "rem", True),  # SR8702
    ("pac1934", "0x12:0", "VCCPRIM_VNNAON", 0.770, 0.005, "rem", True),  # SR8203
    ("pac1934", "0x12:1", "1P8VSUS_SR2601", 1.800, 0.01, "rem", True),  # SR2601
    ("pac1934", "0x12:2", "3VSUS_SR2602", 3.300, 0.01, "rem", True),  # SR2602
    ("pac1934", "0x12:3", "VCCPRIM_IO", 1.250, 0.005, "rem", True),  # SR8204
    ("pac1934", "0x13:0", "AC_BAT_SYS_SR8101", 8.800, 0.01, "rem", True),  # SR8101
    ("pac1934", "0x13:1", "VCCGT", 1.520, 0.005, "rem", True),  # SR8111
    ("pac1934", "0x13:2", "VCCSA", 1.520, 0.005, "rem", True),  # SR8113
    ("pac1934", "0x13:3", "VCCLP_ECORE", 1.520, 0.005, "rem", True),  # SR8114
    ("pac1934", "0x14:0", "VCCST", 0.770, 0.02, "rem", True),  # SR8810
    ("pac1934", "0x14:1", "VDD1", 1.800, 0.02, "rem", True),  # SR8606
    ("pac1934", "0x14:2", "VDD2H", 1.065, 0.01, "rem", True),  # SR8607
    ("pac1934", "0x14:3", "VDDQ", 0.520, 0.02, "rem", True),  # SR8609
    ("pac1934", "0x15:0", "3VS_EDP", 3.300, 0.02, "rem", True),  # SR4502
    ("pac1934", "0x15:1", "ELVDD", 4.600, 0.02, "rem", True),  # SR4505
    ("pac1934", "0x15:2", "3VS_SR4501", 3.300, 0.02, "rem", True),  # SR4501
    ("pac1934", "0x15:3", "1P8VS_SR4505", 1.800, 0.02, "rem", True),  # SR4505
    ("pac1934", "0x16:0", "3VA_EC_SR3001", 3.300, 0.02, "rem", True),  # SR3001
    ("pac1934", "0x16:1", "1P8VSUS", 1.800, 0.02, "rem", True),  # SR3002
    ("pac1934", "0x16:2", "3VA_EC", 3.300, 0.01, "rem", True),  # SR4101
    ("pac1934", "0x16:3", "1P8VA_EC", 1.800, 0.01, "rem", True),  # SR4102
    ("pac1934", "0x17:0", "3VS", 3.300, 0.02, "rem", True),  # SR4804
    ("pac1934", "0x17:1", "3VSUS_SR4805", 3.300, 0.02, "rem", True),  # SR4805
    ("pac1934", "0x17:2", "3VSUS", 3.300, 0.02, "rem", True),  # SR5301
    ("pac1934", "0x17:3", "3VS_SSD", 3.300, 0.02, "rem", True),  # SR5401
    ("pac1934", "0x18:0", "3VA_EC_SR4603", 3.300, 0.01, "rem", True),  # SR4603
    ("pac1934", "0x18:1", "1P8VS_A_SR3602", 1.800, 0.02, "rem", True),  # SR3602
    ("pac1934", "0x18:2", "5VSUS_IO", 5.000, 0.02, "rem", True),  # SR3603
    ("pac1934", "0x18:3", "AC_BAT_SYS_SR8102", 8.800, 0.01, "rem", True),  # SR8102
    ("pac1934", "0x19:0", "5VS", 5.000, 0.02, "rem", True),  # SR3101
    ("pac1934", "0x19:1", "3VS_SR4701", 3.300, 0.02, "rem", True),  # SR4701
    ("pac1934", "0x19:2", "PP5000_TCHPAD_X", 5.000, 0.02, "rem", True),  # CR3104
    ("pac1934", "0x19:3", "5VS_FAN", 5.000, 0.02, "rem", True),  # SR5001
    ("pac1934", "0x1a:0", "AC_BAT_SYS_SR8103", 8.800, 0.01, "rem", True),  # SR8103
    ("pac1934", "0x1a:1", "3V_RT0", 3.000, 0.02, "rem", True),  # SR8812
    ("pac1934", "0x1a:2", "PP3300_FP_X", 3.300, 0.02, "rem", True),  # CR7003
    ("pac1934", "0x1a:3", "VCCCORE_SR8110", 1.600, 0.005, "rem", True),  # SR8110
    ("pac1934", "0x1b:0", "VCCCORE_SR8108", 1.600, 0.005, "rem", True),  # SR8108
    ("pac1934", "0x1b:1", "VCCCORE", 1.600, 0.005, "rem", True),  # SR8109
    ("pac1934", "0x1b:2", "3VA_SR0601", 3.300, 0.02, "rem", True),  # SR0601
    ("pac1934", "0x1b:3", "3VSUS_SR8001", 3.300, 0.02, "rem", True),  # SR8001
    ("pac1934", "0x1c:0", "AC_BAT_SYS_SR8104", 8.800, 0.01, "rem", True),  # SR8104
    ("pac1934", "0x1c:1", "AC_BAT_SYS_SR8106", 8.800, 0.01, "rem", True),  # SR8106
    ("pac1934", "0x1c:2", "AC_BAT_SYS_SR8107", 8.800, 0.01, "rem", True),  # SR8107
    ("pac1934", "0x1c:3", "1P8VS_CODEC_A", 1.800, 0.02, "rem", True),  # SR3604
    ("pac1934", "0x1d:0", "1P8VS_A", 1.800, 0.02, "rem", True),  # SR3901
    ("pac1934", "0x1d:1", "AC_BAT_SYS", 8.800, 0.01, "rem", True),  # SR3903
    ("pac1934", "0x1d:2", "3VSUS_SR3601", 3.300, 0.02, "rem", True),  # SR3601
]
