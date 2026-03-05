#!/bin/bash
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# A simple test script for bare-metal verification of servod and dut-power.

BOARD=""
MODEL=""
SERIAL=""
PORT="9999"

while getopts "b:m:s:p:" opt; do
  case ${opt} in
    b ) BOARD=$OPTARG ;;
    m ) MODEL=$OPTARG ;;
    s ) SERIAL=$OPTARG ;;
    p ) PORT=$OPTARG ;;
    \? ) echo "Usage: $0 -b <board> [-m <model>] [-s <serial>] [-p <port>]" ; exit 1 ;;
  esac
done

if [ -z "${BOARD}" ]; then
  echo "Error: BOARD (-b) is required."
  exit 1
fi

echo "======================================"
echo "=== 1. BINARY & ENVIRONMENT CHECKS ==="
echo "======================================"
if which servod >/dev/null 2>&1; then
  echo "[PASS] servod is installed at $(which servod)"
else
  echo "[FAIL] servod NOT found"
  exit 1
fi

if which dut-control >/dev/null 2>&1; then
  echo "[PASS] dut-control is installed at $(which dut-control)"
else
  echo "[FAIL] dut-control NOT found"
  exit 1
fi

if which dut-power >/dev/null 2>&1; then
  echo "[PASS] dut-power is installed at $(which dut-power)"
else
  echo "[FAIL] dut-power NOT found"
fi

echo ""
echo "======================================"
echo "=== 2. PYTHON IMPORT & gRPC CHECK  ==="
echo "======================================"
if python3 -c "from servo.core import dut_control" >/dev/null 2>&1; then
  echo "[PASS] dut-control imported successfully (gRPC is working)"
else
  echo "[FAIL] dut-control import failed"
  exit 1
fi

if python3 -c "from measurement_tools import measure_power" >/dev/null 2>&1; then
  echo "[PASS] dut-power imported successfully (measurement_tools is working)"
else
  echo "[FAIL] dut-power import failed"
  exit 1
fi

echo ""
echo "======================================"
echo "=== 3. UPSTART DAEMON LIFECYCLE    ==="
echo "======================================"
START_ARGS="PORT=${PORT} BOARD=${BOARD}"
[ -n "${SERIAL}" ] && START_ARGS="${START_ARGS} SERIAL=${SERIAL}"
[ -n "${MODEL}" ] && START_ARGS="${START_ARGS} MODEL=${MODEL}"

echo "Starting servod via Upstart with: ${START_ARGS}"
# shellcheck disable=SC2086
if ! start servod ${START_ARGS}; then
  echo "[FAIL] Failed to start servod via Upstart"
  exit 1
fi

echo "Waiting 10 seconds for servod to initialize with the real hardware..."
sleep 10
status servod "PORT=${PORT}"

if status servod "PORT=${PORT}" | grep -q "start/running"; then
  echo "[PASS] Servod is running via Upstart."
else
  echo "[FAIL] Servod is NOT running"
  exit 1
fi

echo ""
echo "======================================"
echo "=== 4. DAEMON INTERACTION          ==="
echo "======================================"
echo "-> Testing dut-control communication..."
if ! dut-control -p "${PORT}" serialname; then
  echo "[FAIL] dut-control failed to communicate with servod"
  exit 1
fi
echo "[PASS] dut-control successfully communicated with servod"

echo "-> Testing dut-power communication..."
if ! dut-power -p "${PORT}" -t 5; then
  echo "[FAIL] dut-power failed to execute correctly"
  exit 1
fi
echo "[PASS] dut-power executed successfully"

echo ""
echo "======================================"
echo "=== 5. TEARDOWN & LOG COLLECTION   ==="
echo "======================================"
echo "Stopping servod..."
stop servod "PORT=${PORT}"

echo ""
echo "--- TAIL OF /var/log/servod_${PORT}/latest.DEBUG ---"
if [ -f "/var/log/servod_${PORT}/latest.DEBUG" ]; then
  tail -n 20 "/var/log/servod_${PORT}/latest.DEBUG"
else
  echo "[WARN] Log file not found at /var/log/servod_${PORT}/latest.DEBUG"
fi

echo "======================================"
echo "=== TEST SCRIPT COMPLETE ==="
echo "======================================"
