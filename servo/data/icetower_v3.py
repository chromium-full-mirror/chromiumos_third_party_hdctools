# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

inas = [
#    drvname,   slv,       name,         nom,    sense,  mux,    is_calib
   ('pac1954',  '0x10:0',  'ppvar_mcu',  3.300,  0.5,    'rem',  True),
   ('pac1954',  '0x10:1',  'ppvar_fp',   3.300,  0.5,    'rem',  True),
   ('pac1954',  '0x10:2',  'pp3300_fp',  3.300,  0.5,    'rem',  True),
   ('pac1954',  '0x10:3',  'pp1800_fp',  1.800,  0.5,    'rem',  True),
]
