# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# generates roach_rev0
revs = [0]
inas = [
# drvname      slv         name              nom         sense       mux   is_calib
  ('ina231',   '0x40',   'pp3300_base',      3.300,      0.02,       'rem',True),#RS2
  ('ina231',   '0x41',   'pp3300_ec',        3.300,      0.02,       'rem',True),#RS4
  ('ina231',   '0x42',   'pp3300_tchpad',    3.300,      0.02,       'rem',True),#RS3
  ('ina231',   '0x43',   'pp3300_kb_bl',     3.300,      0.02,       'rem',True),#RS1
]
