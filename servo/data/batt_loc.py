# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

config_type='sweetberry'

# the names j2, j3, and j4 are the white banks on sweetberry
inas = [
    ('ina231', (1,3),   'vbat_100mohm' , 7.7, 0.100, 'j2', True),
    ('ina231', (2,4),   'vbat_010mohm' , 7.7, 0.010, 'j2', True),
]
