# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# generates sapphire_rev0.py
revs = [0]
inas = [
    # drvname      slv        name                nom     sense  mux   is_calib
    ("pac1934", "0x10:0", "ppvar_vbus_in", 8.800, 0.01, "rem", True),  # PR3501
    ("pac1934", "0x10:1", "pp1800_gsc_z1", 1.800, 0.02, "rem", True),  # RS12
    ("pac1934", "0x10:2", "ppvar_batt_chg", 8.800, 0.01, "rem", True),  # PR3532
    ("pac1934", "0x10:3", "ppvar_batt_dischg", 8.800, 0.01, "rem", True),  # PR3532
    ("pac1934", "0x11:0", "pp3300_ec_z1", 3.300, 0.02, "rem", True),  # RS2
    ("pac1934", "0x11:1", "ppvar_sys", 8.800, 0.01, "rem", True),  # PR3507
    ("pac1934", "0x11:2", "pp1800_ec_vcc", 1.800, 0.02, "rem", True),  # RS3
    ("pac1934", "0x11:3", "pp3300_z1", 3.300, 0.01, "rem", True),  # PR3615
    ("pac1934", "0x12:0", "pp5000_mipi_disp_vin", 5.000, 0.02, "rem", True),  # RS39
    ("pac1934", "0x12:1", "pp1800_tchscr_x", 1.800, 0.01, "rem", True),  # RS949313
    ("pac1934", "0x12:2", "ppvar_mipi_bl_vin", 8.800, 0.02, "rem", True),  # RS24
    ("pac1934", "0x12:3", "pp4200_gpu_in", 4.200, 0.02, "rem", True),  # RS21
    # DVT would use pp3300_hub_s3
    ("pac1934", "0x13:0", "pp3300_hub_s3", 3.300, 0.01, "rem", True),  # RS14
    ("pac1934", "0x13:1", "ppvar_base_x", 3.300, 0.02, "rem", True),  # RS43
    ("pac1934", "0x13:2", "pp3300_ucam_x", 3.300, 0.02, "rem", True),  # RS6
    ("pac1934", "0x13:3", "pp5000_spkl_z1", 5.000, 0.01, "rem", True),  # RS45
    ("pac1934", "0x14:0", "pp5000_spkr_z1", 5.000, 0.01, "rem", True),  # RS44
    ("pac1934", "0x14:1", "pp4200_s5", 4.200, 0.01, "rem", True),  # PR3721
    ("pac1934", "0x14:2", "pp3300_wlan_s3", 3.300, 0.02, "rem", True),  # RS8
    ("pac1934", "0x14:3", "pdc_vin_3300", 3.300, 0.01, "rem", True),  # RS41
    ("pac1934", "0x15:0", "pp4200_cpum_in", 4.200, 0.02, "rem", True),  # RS19
    ("pac1934", "0x15:1", "pp4200_cpul_in", 4.200, 0.02, "rem", True),  # RS28
    ("pac1934", "0x15:2", "pp4200_core_in", 4.200, 0.02, "rem", True),  # RS27
    ("pac1934", "0x15:3", "pp4200_apu_in", 4.200, 0.02, "rem", True),  # RS22
    ("pac1934", "0x16:0", "pp1800_vio18_s3", 1.800, 0.02, "rem", True),  # RS20
    ("pac1934", "0x16:1", "pp4200_gpustack_in", 4.200, 0.02, "rem", True),  # RS18
    ("pac1934", "0x16:2", "pp4200_cpub_in", 4.200, 0.02, "rem", True),  # RS30
    ("pac1934", "0x16:3", "pp5000_z1", 5.000, 0.01, "rem", True),  # PR3617
    ("pac1934", "0x17:0", "pp3300_fp_x", 3.300, 0.01, "rem", True),  # R949366
    ("pac1934", "0x17:1", "led_5v_vin", 5.000, 0.01, "rem", True),  # R949367
    ("pac1934", "0x17:2", "pp3300_gsc_z1", 3.300, 0.02, "rem", True),  # RS13
    ("pac1934", "0x17:3", "pp1450_wcam_x", 1.450, 0.01, "rem", True),  # R949004
]
