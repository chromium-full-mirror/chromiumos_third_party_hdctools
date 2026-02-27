#!/bin/bash
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# Runs tests inside a Docker container on the local machine and copies logs to the Cloudtop.

set -e

if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <CLOUDTOP_HOSTNAME> <RUN_ID> <IMAGE_NAME>"
    exit 1
fi

CLOUDTOP_HOST=$1
RUN_ID=$2
IMAGE_NAME=$3

CONTAINER_NAME="servod_test_$RUN_ID"
LOCAL_LOG_BASE="/tmp/servod_test_logs"
LOCAL_LOG_DIR="$LOCAL_LOG_BASE/$RUN_ID"
CLOUDTOP_RESULTS_DIR="/tmp/servod_test_results/$RUN_ID"

# Clean up any previous run
rm -rf "$LOCAL_LOG_DIR"
mkdir -p "$LOCAL_LOG_DIR"

echo "Pulling image: $IMAGE_NAME"
docker pull "$IMAGE_NAME"

echo "Running tests in container: $CONTAINER_NAME"
echo "Logs will be stored in: $LOCAL_LOG_DIR"
start-servod -c local --docker-label "$IMAGE_NAME" -t -n "$CONTAINER_NAME" --logs "$LOCAL_LOG_BASE"

LOG_FILE_PATH="$LOCAL_LOG_DIR/$CONTAINER_NAME/latest.DEBUG"

if [ -f "$LOG_FILE_PATH" ]; then
    echo "Copying log file to Cloudtop: $CLOUDTOP_HOST:$CLOUDTOP_RESULTS_DIR/"
    scp "$LOG_FILE_PATH" "${CLOUDTOP_HOST}:${CLOUDTOP_RESULTS_DIR}/latest.DEBUG"
    echo "Log transfer complete."
else
    echo "Error: Log file not found at $LOG_FILE_PATH"
fi

echo "Cleaning up local log directory: $LOCAL_LOG_DIR"
rm -rf "$LOCAL_LOG_DIR"

echo "Local test run complete."
