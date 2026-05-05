#!/bin/bash
# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

set -x

log_output() {
  echo "$(date -Iseconds)" "${@}"
  logger -t "${UPSTART_JOB}" "${@}"
}

/usr/bin/fwupdtool install --filter="updatable" /usr/local/genesys/GenesysLogic_Google_Servo_GL3590_64.18.cab | tr -d "?"

LOG_BACKUP_COUNT=1024

# Default port to be 9999.
PORT="${PORT:-9999}"
mkdir -p /var/lib/servod

log_output "Pre-start PORT=""${PORT}"" BOARD=""${BOARD}"" MODEL=""${MODEL}"" SERIAL=""${SERIAL}""."

for CMD in iptables-legacy ip6tables-legacy ; do
    "${CMD}" -A INPUT -p tcp --dport "${PORT}" -j ACCEPT || log_output "Failed to configure ${CMD}."
done

log_output "Pre-start complete."

if [ -z "${BOARD}" ]; then
    log_output "No board specified; terminating"
    stop
    exit 0
fi

MODEL_MSG=""
MODEL_FLAG=""
if [ -n "${MODEL}" ]; then
    MODEL_FLAG="--model ${MODEL}"
    MODEL_MSG=" model ${MODEL}"
fi

SERIAL_FLAG=""
SERIAL_MSG=""
if [ -z "${SERIAL}" ]; then
    log_output "No serial specified"
else
    SERIAL_FLAG="--serialname ${SERIAL}"
    SERIAL_MSG="using servo serial ${SERIAL}"
fi

BOARD_FLAG="--board ${BOARD}"
PORT_FLAG="--port ${PORT}"

if [ "${DEBUG}" = "1" ]; then
    DEBUG_FLAG="--debug"
else
    DEBUG_FLAG=""
fi

if [ "${NOBOARD}" = "1" ]; then
    NOBOARD_FLAG="--noboard"
else
    NOBOARD_FLAG=""
fi

if [ -n "${DUMP_XML}" ]; then
    DUMP_XML_FLAG="--dump-xml ${DUMP_XML}"
else
    DUMP_XML_FLAG=""
fi

CONFIG_FLAG=""
if [ -n "${CONFIG}" ]; then
    CONFIG_FLAG="--config ${CONFIG}"
fi

REC_MODE_FLAG=""
if [ -n "${REC_MODE}" ]; then
    REC_MODE_FLAG="--servo-recovery"
fi

if [ "${DUAL_V4}" = "1" ]; then
    DEVICE_DISCOVERY_FLAG="--device-discovery=full"
else
    DEVICE_DISCOVERY_FLAG=""
fi

NAME_FLAG=""
if [ -n "${NAME}" ]; then
    NAME_FLAG="--name ${NAME}"
fi

if [ -n "${SERVO_REBOOT}" ] && [ -n "${SERIAL}" ]; then
    servodtool device -s "${SERIAL}" reboot
    sleep 5
fi

# Optionally update the servo firmware, if the firmware is already at the correct
# version this is a no-op
# SERVO_FW_CHANNEL should be one of - stable, beta, dev, prev (it is case sensitive)
# SERVO_TYPE should be one of servo_v4 or servo_v4p1
if [ -n "${SERVO_FW_CHANNEL}" ] && [ -n "${SERIAL}" ] && [ -n "${SERVO_TYPE}" ]; then
    servo_updater -s "${SERIAL}" -c "${SERVO_FW_CHANNEL}" -b "${SERVO_TYPE}"
fi

log_output "start generate gRPC Files...."

cp /usr/local/lib/python3.13/dist-packages/servo/protoc-gen-custom_grpc.py \
    /usr/local/lib/python3.13/dist-packages/servo/protoc-gen-custom_grpc
chmod +x /usr/local/lib/python3.13/dist-packages/servo/protoc-gen-custom_grpc

/usr/bin/python3 /usr/local/lib/python3.13/dist-packages/servo/grpc.py

log_output "Finish generate gRPC Files"

log_output "starting grpc server ...................."
data_args=" /usr/local/lib/python3.13/dist-packages/servo/data/grpc_server/grpc_server_setup.py "
data_args+=" --grpc-core-host localhost"
data_args+=" --grpc-core-port 50052"
data_args+=" --grpc-data-port 50051"
data_args+=" --logs /var/log/servod_${PORT}"
data_args+=" ${DEBUG_FLAG}"

IFS=" " read -r -a dargs <<< "${data_args}"
/usr/bin/python3 "${dargs[@]}" &

log_output "Launching servod for ${BOARD} ${MODEL_MSG} on port ${PORT} ${SERIAL_MSG}"
servod_args=" --host 0.0.0.0 "
servod_args+=" --log-dir /var/log"
servod_args+=" --log-dir-backup-count ${LOG_BACKUP_COUNT}"
servod_args+=" ${BOARD_FLAG}"
servod_args+=" ${MODEL_FLAG}"
servod_args+=" ${SERIAL_FLAG}"
servod_args+=" ${PORT_FLAG}"
servod_args+=" ${DEBUG_FLAG}"
servod_args+=" ${NOBOARD_FLAG}"
servod_args+=" ${DUMP_XML_FLAG}"
servod_args+=" ${REC_MODE_FLAG}"
servod_args+=" ${CONFIG_FLAG}"
servod_args+=" ${NAME_FLAG}"
servod_args+=" ${DEVICE_DISCOVERY_FLAG}"
servod_args+=" --grpc-core-port 50052"
servod_args+=" --grpc-data-host localhost"
servod_args+=" --grpc-data-port 50051"

IFS=" " read -r -a args <<< "${servod_args}"
servod "${args[@]}" &

wait -n
exit $?
