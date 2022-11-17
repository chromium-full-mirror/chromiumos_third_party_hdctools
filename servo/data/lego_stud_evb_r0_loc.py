# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

config_type='sweetberry'

inas = [
    ('ina231', (7,13), 'PP3300_LEGO',               3.30, 0.010, 'android', True), # R28
    ('ina231', (2,8), 'PPVAR_HV_BRICK_A',           5.00, 0.025, 'android', True), # R92
    ('ina231', (9,15), 'BASE_IO_A0',                3.30, 0.0001, 'android', True), # Stud IO
    ('ina231', (4,10), 'PP5000_LEGO_STUD_EVB',      5.00, 0.010, 'android', True), # R41
    ('ina231', (6,12), 'PPVAR_IO_BRICK_A0',         3.30, 0.025, 'android', True), # R93
    ('ina231', (19,25), 'BASE_IO_B3',               3.30, 0.0001, 'android', True), # Stud IO
    ('ina231', (20,26), 'PP3300_STUD_EVB',          3.30, 0.010, 'android', True), # R152
    ('ina231', (21,27), 'PP1800_LEGO',              1.80, 0.010, 'android', True), # R27
    ('ina231', (22,28), 'PPVAR_IO_BRICK_A1',        3.30, 0.025, 'android', True), # R94
    ('ina231', (23,29), 'BASE_IO_C6',               3.30, 0.0001, 'android', True), # Stud IO
    ('ina231', (24,30), 'PP1800_STUD_EVB',          1.80, 0.010, 'android', True), # R89
    ('ina231', (32,38), 'PPVAR_HV_BRICK_B',         5.00, 0.025, 'android', True), # R95
    ('ina231', (39,45), 'BASE_IO_D9',               3.30, 0.0001, 'android', True), # Stud IO
    ('ina231', (34,40), 'PP5000_STUD_EVB',          5.00, 0.010, 'android', True), # R153
    ('ina231', (41,47), 'PP5000_LEGO',              5.00, 0.010, 'android', True), # R29
    ('ina231', (36,42), 'PPVAR_IO_BRICK_B0',        3.30, 0.025, 'android', True), # R96
    ('ina231', (49,55), 'BRICK_IO_A1',              3.30, 0.0001, 'android', True), # Stud IO
    ('ina231', (52,58), 'PPVAR_IO_BRICK_B1',        3.30, 0.025, 'android', True), # R97
    ('ina231', (53,59), 'BRICK_IO_B4',              3.30, 0.0001, 'android', True), # Stud IO
    ('ina231', (67,73), 'PPVAR_SYS',                11.80, 0.002, 'android', True), # R111
    ('ina231', (62,68), 'PPVAR_HV_BRICK_C',         5.00, 0.025, 'android', True), # R98
    ('ina231', (69,75), 'BRICK_IO_C7',              3.30, 0.0001, 'android', True), # Stud IO
    ('ina231', (66,72), 'PPVAR_IO_BRICK_C0',        3.30, 0.025, 'android', True), # R99
    ('ina231', (79,85), 'BRICK_IO_D8',              3.30, 0.0001, 'android', True), # Stud IO
    ('ina231', (82,88), 'PPVAR_IO_BRICK_C1',        3.30, 0.025, 'android', True), # R100
    ('ina231', (92,98), 'PPVAR_HV_BRICK_D',         5.00, 0.025, 'android', True), # R101
    ('ina231', (96,102), 'PPVAR_IO_BRICK_D0',       3.30, 0.025, 'android', True), # R102
    ('ina231', (112,118), 'PPVAR_IO_BRICK_D1',      3.30, 0.025, 'android', True), # R103
]
