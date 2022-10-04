# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

config_type='sweetberry'

inas = [
    ('ina231', '0x40:3', 'vbat', 7.70, 1.000, 'j2', True), # R569, originally 0.01 Ohm
]
