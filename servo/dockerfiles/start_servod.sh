#!/bin/bash
# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

set -x

log_output() {
  echo "$(date -Iseconds)" "${@}"
  logger -t "${UPSTART_JOB}" "${@}"
}

/usr/bin/fwupdtool install --filter="updatable" /usr/local/genesys/GenesysLogic_GL3590_64.17.cab | tr -d "?"

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
    SERIAL_FLAG="--serialname ${SERIAL}c;}"
    SERIAL_MSG="using servo serial ${SERIAL}"
fi

BOARD_FLAG="--board ${BOARD}"
PORT_FLAG="--port ${PORT}"

if [ "${DEBUG}" = "1" ]; then
    DEBUG_FLAG="--debug"
else
    DEBUG_FLAG=""
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

log_output "Launching servod for ${BOARD} ${MODEL_MSG} on port ${PORT} ${SERIAL_MSG}"

exec servod \
    --host 0.0.0.0 \
    --log-dir-backup-count "${LOG_BACKUP_COUNT}" \
    "${BOARD_FLAG}" \
    "${MODEL_FLAG}" \
    "${SERIAL_FLAG}" \
    "${PORT_FLAG}" \
    "${DEBUG_FLAG}" \
    "${REC_MODE_FLAG}" \
    "${CONFIG_FLAG}" \
    "${NAME_FLAG}" \
    "${DEVICE_DISCOVERY_FLAG}"
