# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

#!/bin/bash

set -x

/usr/bin/fwupdtool install --filter="updatable" /usr/local/genesys/GenesysLogic_GL3590_64.17.cab | tr -d ?

CONFIG_FILE_DIR="/var/lib/servod"
CONFIG_FILE=$CONFIG_FILE_DIR/config_$PORT
LOG="/var/log/servod_$PORT.STARTUP.log"
LOG_BACKUP_COUNT=1024

# Default port to be 9999.
PORT=${PORT:-9999}
mkdir -p /var/lib/servod
. /hdctools/chromeos/servod_utils.sh

log_output "Pre-start PORT=$PORT BOARD=$BOARD MODEL=$MODEL SERIAL=$SERIAL."

for CMD in iptables-legacy ip6tables-legacy ; do
    $CMD -A INPUT -p tcp --dport $PORT -j ACCEPT || log_output "Failed to configure $CMD."
done

log_output "Update config. PORT=$PORT BOARD=$BOARD MODEL=$MODEL SERIAL=$SERIAL."

# We'll want to update the config file with all the args passed in.
update_config $CONFIG_FILE BOARD $BOARD
update_config $CONFIG_FILE MODEL $MODEL
update_config $CONFIG_FILE SERIAL $SERIAL
update_config $CONFIG_FILE CONFIG $CONFIG
update_config $CONFIG_FILE DUAL_V4 $DUAL_V4

log_output "Store servo hub location and servo micro serial if presents. "\
    "$CONFIG_FILE $SERIAL"
cache_servov4_hub_and_servo_micro $CONFIG_FILE $SERIAL
log_output "Pre-start complete."

SERVO_MICRO_VIDPID="18d1:501a"
SERVO_V4_VIDPID="18d1:501b"

if [ ! -f $CONFIG_FILE ]; then
    log_output "No configuration file ($CONFIG_FILE); terminating"
    stop
    exit 0
fi

if [ -z "$BOARD" ]; then
    log_output "No board specified; terminating"
    stop
    exit 0
fi

MODEL_MSG=""
MODEL_FLAG=""
if [ -n "$MODEL" ]; then
    MODEL_FLAG="--model ${MODEL}"
    MODEL_MSG=" model ${MODEL}"
fi

SERIAL_FLAG=""
SERIAL_MSG=""
if [ -z "$SERIAL" ]; then
    log_output "No serial specified"
else
    SERIAL_FLAG="--serialname ${SERIAL}"
    SERIAL_MSG="using servo serial $SERIAL"
fi

BOARD_FLAG="--board ${BOARD}"
PORT_FLAG="--port ${PORT}"

if [ "$DEBUG" = "1" ]; then
    DEBUG_FLAG="--debug"
else
    DEBUG_FLAG=""
fi

CONFIG_FLAG=""
if [ ! -z "$CONFIG" ]; then
    CONFIG_FLAG="--config ${CONFIG}"
fi

REC_MODE_FLAG=""
if [ ! -z "$REC_MODE" ]; then
    REC_MODE_FLAG="--servo-recovery"
fi

if [ "$DUAL_V4" = "1" ]; then
    DEVICE_DISCOVERY_FLAG="--device-discovery=full"
else
    DEVICE_DISCOVERY_FLAG=""
fi

NAME_FLAG=""
if [ ! -z "$NAME" ]; then
    NAME_FLAG="--name $NAME"
fi

if ([ -n "$SERVO_REBOOT" ] && [ -n "$SERIAL" ]); then
    servodtool device -s $SERIAL reboot
    sleep 5
fi

# Optionally update the servo firmware, if the firmware is already at the correct
# version this is a no-op
# SERVO_FW_CHANNEL should be one of - stable, beta, dev, prev (it is case sensitive)
# SERVO_TYPE should be one of servo_v4 or servo_v4p1
if ([ -n "$SERVO_FW_CHANNEL" ] && [ -n "$SERIAL" ] && [ -n "$SERVO_TYPE" ]); then
    servo_updater -s $SERIAL -c $SERVO_FW_CHANNEL -b $SERVO_TYPE
fi

log_output "Launching servod for $BOARD $MODEL_MSG on port $PORT $SERIAL_MSG"

servod \
    --host 0.0.0.0 \
    --log-dir-backup-count $LOG_BACKUP_COUNT \
    $BOARD_FLAG \
    $MODEL_FLAG \
    $SERIAL_FLAG \
    $PORT_FLAG \
    $DEBUG_FLAG \
    $REC_MODE_FLAG \
    $CONFIG_FLAG \
    $NAME_FLAG \
    $DEVICE_DISCOVERY_FLAG
