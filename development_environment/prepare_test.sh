#!/bin/bash
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# Prepares the environment on the Cloudtop for a remote test run.

set -e

RUN_ID=$(date +%Y%m%d_%H%M%S)_$(uuidgen | cut -d- -f1)
IMAGE_NAME="us-docker.pkg.dev/chromeos-hw-tools-dev/servod-scratch/servod:haddowk"
RESULTS_DIR="/tmp/servod_test_results/$RUN_ID"

mkdir -p "$RESULTS_DIR"

echo "Test Run ID: $RUN_ID"
echo "Image Name: $IMAGE_NAME"
echo "Results Directory: $RESULTS_DIR"
echo ""
echo "Run the following command on the local gLinux machine:"
echo "./run_test_on_local.sh <CLOUDTOP_HOSTNAME> $RUN_ID $IMAGE_NAME"
