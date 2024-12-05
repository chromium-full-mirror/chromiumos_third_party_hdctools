#!/bin/bash
# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

found_updatable=0
for dev in /sys/bus/usb/devices/[0-9]*; do
	grep -q 05e3 $dev/idVendor 2>/dev/null && \
	grep -q 0610 $dev/idProduct && \
	grep -q '^Google$' $dev/manufacturer && \
	grep -q -v '^6417$' $dev/bcdDevice && \
	found_updatable=1
done
if [ $found_updatable -eq 1 ]; then
	/usr/bin/fwupdtool install --plugins genesys --filter="updatable" /usr/local/genesys/GenesysLogic_GL3590_64.17.cab | tr -d ?
fi

echo $(date --utc +"%Y-%m-%dT%H:%M:%S.%3N%:z") "Starting servod"
/usr/bin/python3 /usr/local/lib/python3.11/dist-packages/servo/data/grpc_server/grpc_server_setup.py &
exec servod --host 0.0.0.0 $1 &

wait -n
exit $?
