# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Created using go/sense-point-template

config_type='sweetberry'

inas = [
    ('ina231', '0x40:3', 'ppvar_vbat_100mohm_s3',  7.7 , 0.1  , 'j2', True), # value is valid in S3, not in S0
    ('ina231', '0x40:1', 'ppvar_vbat_010mohm_s0',  7.7 , 0.01 , 'j2', True), # value is valid in S0, not in S3
]
