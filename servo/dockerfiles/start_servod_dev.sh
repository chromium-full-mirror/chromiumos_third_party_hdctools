# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

#!/bin/bash
# TODO(b/320508176) Figure out a more targeted way to update the genesys firmware.
#/usr/bin/fwupdtool install --filter="updatable" /usr/local/genesys/GenesysLogic_GL3590_64.17.cab | tr -d ?
echo $(date +"%Y-%m-%d %H:%M:%S,%3N") "Starting servod"
servod --host 0.0.0.0 $1
