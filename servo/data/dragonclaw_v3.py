# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

inas = [
#    drvname,   slv,       name,         nom,  sense,  mux,    is_calib
   ('ina3221',  '0x40:0',  'ppvar_mcu',  3.3,  0.5,    'rem',  True),
   ('ina3221',  '0x40:1',  'pp3300_fp',  3.3,  0.5,    'rem',  True),
   ('ina3221',  '0x40:2',  'pp1800_fp',  1.8,  0.5,    'rem',  True),
   ('ina219',   '0x41',    'ppvar_fp',   3.3,  0.5,    'rem',  True),
]
