# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

config_type  = 'servod'

revs = [ 0 ]

inline = """
  <map>
    <name>dut_adc_mux</name>
    <doc>valid mux values for DUT's three banks of INA3221 off PCA9546
    ADCs</doc>
    <params clobber_ok="" none="0" bank0="1" bank1="2" bank2="4" bank3="8"></params>
  </map>
  <control>
    <name>dut_adc_mux</name>
    <doc>2 to 1 mux to steer remote i2c dut_adc_mux:bank0/1/3 to three sets of
    12 INA3221 ADCs.</doc>
    <params clobber_ok="" interface="2" drv="pca9546" child="0x70"
    map="dut_adc_mux"></params>
  </control>
"""

inas = [
        ('ina3221', '0x40:0', 'vreg_s2c_s3c_s4c',  0.868, 0.010, 'rem dut_adc_mux:bank0', True), # R2802
        ('ina3221', '0x40:1', 'vreg_s5c_s6c',      0.864, 0.010, 'rem dut_adc_mux:bank0', True), # R2801
        ('ina3221', '0x40:2', 'vreg_s9c_gfx',      0.868, 0.010, 'rem dut_adc_mux:bank0', True), # R2901
        ('ina3221', '0x41:0', 'vreg_s1c',          2.20, 0.100,  'rem dut_adc_mux:bank0', True), # R38
        ('ina3221', '0x41:1', 'vreg_s10c',         0.912, 0.010, 'rem dut_adc_mux:bank0', True), # R2902
        ('ina3221', '0x41:2', 'vreg_s9c',          1.125, 0.010, 'rem dut_adc_mux:bank0', True), # R2903
        ('ina3221', '0x42:0', 'vreg_s6b',          2.20, 0.010,  'rem dut_adc_mux:bank0', True), # R38
        ('ina3221', '0x42:1', 'vreg_l18b',         1.80, 0.500,  'rem dut_adc_mux:bank0', True), # R37
        ('ina3221', '0x42:2', 'ppvar_uim1',        1.80, 0.500,  'rem dut_adc_mux:bank0', True), # R241
        ('ina3221', '0x43:0', 'pp1800_l19b',       1.80, 0.500,  'rem dut_adc_mux:bank0', True), # R217
        ('ina3221', '0x43:1', 'vreg_l7b',          2.95, 0.050,  'rem dut_adc_mux:bank0', True), # R36
        ('ina3221', '0x43:2', 'vreg_s8b',          1.30, 0.100,  'rem dut_adc_mux:bank0', True), # R11309
        ('ina3221', '0x40:0', 'vreg_s1b',          1.90, 0.100,  'rem dut_adc_mux:bank1', True), # R11307
        ('ina3221', '0x40:1', 'vreg_s7b',          0.95, 0.100,  'rem dut_adc_mux:bank1', True), # R11308
        #('ina3221', '0x40:2', 'tp10/11',          0.00, 0.000,  'rem dut_adc_mux:bank1', True), # TP10/TP11
        ('ina3221', '0x41:0', 'pp3300_ts',         3.30, 0.010,  'rem dut_adc_mux:bank1', True), # R454
        ('ina3221', '0x41:1', 'pp3300_edp',        3.30, 0.010,  'rem dut_adc_mux:bank1', True), # R95_LS
        ('ina3221', '0x41:2', 'pp3300_cam',        3.30, 0.010,  'rem dut_adc_mux:bank1', True), # R228
        ('ina3221', '0x42:0', 'lcd_bl_mipi_vp',    0.00, 0.100,  'rem dut_adc_mux:bank1', True), # R46
        ('ina3221', '0x42:1', 'pp3300_l13c',       3.30, 0.100,  'rem dut_adc_mux:bank1', True), # R44
        ('ina3221', '0x42:2', 'pp1800_l12c',       1.80, 0.100,  'rem dut_adc_mux:bank1', True), # R47
        ('ina3221', '0x43:0', 'vph_pwr',           0.00, 0.002,  'rem dut_adc_mux:bank1', True), # R49
        ('ina3221', '0x43:1', 'pp3300_ssd_in',     3.30, 0.010,  'rem dut_adc_mux:bank1', True), # R29
        ('ina3221', '0x43:2', 'pp1800_l18b',       1.80, 0.100,  'rem dut_adc_mux:bank1', True), # R3714
        ('ina3221', '0x40:0', 'pp2850_uf_cam',     2.85, 0.010,  'rem dut_adc_mux:bank3', True), # R65
        #('ina3221', '0x40:1', 'pp1800_uf_cam',    1.80, 0.000,  'rem dut_adc_mux:bank3', False), # No connection
        ('ina3221', '0x40:2', 'pp2850_wf_cam',     2.85, 0.010,  'rem dut_adc_mux:bank3', True), # R63
        #('ina3221', '0x41:0', 'pp1800_wf_cam',    1.80, 0.000,  'rem dut_adc_mux:bank3', False), # No connection
        ('ina3221', '0x41:1', 'pp2850_vcm_wf_cam', 2.85, 0.010,  'rem dut_adc_mux:bank3', True), # R64
        #('ina3221', '0x41:2', 'pp1200_wf_cam',    1.20, 0.010,  'rem dut_adc_mux:bank3', True), # R228
        ('ina3221', '0x42:0', 'vreg_l3b',          0.60, 0.100,  'rem dut_adc_mux:bank3', True), # R39
        ('ina3221', '0x42:1', 'vreg_s3b_s4b_s5b',  0.87, 0.010,  'rem dut_adc_mux:bank3', True), # R2301
        ('ina3221', '0x42:2', 'lcd_bl_edp_vp',     0.00, 0.010,  'rem dut_adc_mux:bank3', True), # R227
]
