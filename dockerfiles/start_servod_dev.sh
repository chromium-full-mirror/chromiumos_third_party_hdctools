#!/bin/bash
# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

found_updatable=0
for dev in /sys/bus/usb/devices/[0-9]*; do
  grep -q 05e3 "${dev}"/idVendor 2>/dev/null && \
  (grep -q 0610 "${dev}"/idProduct || grep -q 0625 "${dev}"/idProduct) && \
  grep -q '^Google$' "${dev}"/manufacturer && \
  grep -q -v '^6418$' "${dev}"/bcdDevice && \
  found_updatable=1
done
if [ "${found_updatable}" -eq 1 ]; then
  /usr/bin/fwupdtool install --plugins genesys --filter="updatable" \
  /usr/local/genesys/GenesysLogic_Google_Servo_GL3590_64.18.cab | tr -d "?"
fi

echo "DEV: starting grpc server ...................."
DEBUG_ARG=""
if [[ " ${1} " =~ " --debug " ]] || [[ " ${1} " =~ " -d " ]]; then
  DEBUG_ARG="--debug"
fi

/usr/bin/python3 \
  /usr/local/lib/python3.13/dist-packages/servo/data/grpc_server/grpc_server_setup.py \
  --grpc-core-host localhost --grpc-core-port 50052 --grpc-data-port 50051 \
  --logs /var/log/servod_9999 ${DEBUG_ARG} &

echo "$(date --utc +\"%Y-%m-%dT%H:%M:%S.%3N%:z\")" "DEV: Starting servod"
IFS=" " read -r -a args <<< "${1}"
exec servod --host 0.0.0.0 "${args[@]}" --grpc-core-port 50052 \
	--grpc-data-host localhost --grpc-data-port 50051 &

wait -n
exit $?
