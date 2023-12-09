# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

#!/bin/bash

/usr/bin/fwupdtool install --filter="updatable" /usr/local/genesys/GenesysLogic_GL3590_64.17.cab | tr -d ?

echo "DEV: starting grpc server ...................."
/usr/bin/python3 /usr/local/lib/python3.11/dist-packages/servo/data/grpc_server/grpc_server_setup.py &
echo "DEV: starting servod ...................."
servod --host 0.0.0.0 $1
