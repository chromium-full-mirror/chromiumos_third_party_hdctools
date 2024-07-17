# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# generates navi_rev0_alt.py

inas = [
# drvname      slv        name                    nom      sense  mux     is_calib
  ('pac1934',  '0x10:0',  'pp3700_gpu_in',        3.700,   0.02,  'rem',  True),  #RS21
  ('pac1934',  '0x10:1',  'pp3700_gpustack_in',   3.700,   0.02,  'rem',  True),  #RS18
  ('pac1934',  '0x10:2',  'pp3700_s5',            3.700,   0.01,  'rem',  True),  #R219
  ('pac1934',  '0x10:3',  'pp3700_apu_in',        3.700,   0.02,  'rem',  True),  #RS22
  ('pac1934',  '0x11:0',  'pp3700_core_in',       3.700,   0.02,  'rem',  True),  #RS27
  ('pac1934',  '0x11:1',  'pp3700_proc_b_in',     3.700,   0.02,  'rem',  True),  #RS30
  ('pac1934',  '0x11:2',  'pp3700_proc_m_in',     3.700,   0.02,  'rem',  True),  #RS19
  ('pac1934',  '0x11:3',  'pp3700_proc_l_in',     3.700,   0.02,  'rem',  True),  #RS28
]
