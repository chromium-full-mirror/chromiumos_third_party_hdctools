#!/bin/bash
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# Cleans up the test results directory on the Cloudtop.

set -e

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <RUN_ID>"
    exit 1
fi

RUN_ID=$1
RESULTS_DIR="/tmp/servod_test_results/$RUN_ID"

if [ -d "$RESULTS_DIR" ]; then
    echo "Removing results directory: $RESULTS_DIR"
    rm -rf "$RESULTS_DIR"
    echo "Cleanup complete."
else
    echo "Warning: Results directory not found: $RESULTS_DIR"
fi
