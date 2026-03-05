#!/bin/bash
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# A multi-DUT test script for bare-metal verification of concurrent servod instances.

CSV_FILE=$1

if [ -z "$CSV_FILE" ] || [ ! -f "$CSV_FILE" ]; then
    echo "Usage: $0 <duts.csv>"
    echo "CSV Format: board,model,serial"
    exit 1
fi

echo "======================================"
echo "=== 1. MULTI-DUT ENVIRONMENT SETUP ==="
echo "======================================"

PORT=9999
# Arrays to keep track of our instances
declare -a PORTS
declare -A PORT_MAP

while IFS=',' read -r board model serial || [ -n "$board" ]; do
    # Skip empty lines, whitespace, or a header row
    board=$(echo "$board" | xargs)
    model=$(echo "$model" | xargs)
    serial=$(echo "$serial" | xargs)

    [ -z "$board" ] && continue
    [ "$board" == "board" ] && continue

    echo "Queueing: Board=$board, Model=$model, Serial=$serial on PORT=$PORT"
    PORTS+=("$PORT")
    PORT_MAP[$PORT]="$board,$model,$serial"
    PORT=$((PORT - 1))
done < "$CSV_FILE"

if [ ${#PORTS[@]} -eq 0 ]; then
    echo "[FAIL] No valid DUTs found in $CSV_FILE"
    exit 1
fi

echo ""
echo "======================================"
echo "=== 2. CONCURRENT DAEMON LIFECYCLE ==="
echo "======================================"

for p in "${PORTS[@]}"; do
    IFS=',' read -r board model serial <<< "${PORT_MAP[$p]}"
    START_ARGS="PORT=$p BOARD=$board SERIAL=$serial"
    [ -n "$model" ] && START_ARGS="${START_ARGS} MODEL=$model"

    echo "Starting servod via Upstart: ${START_ARGS}"
    # shellcheck disable=SC2086
    if ! start servod ${START_ARGS}; then
        echo "[FAIL] Failed to start servod on port $p"
    fi
done

echo "Waiting 15 seconds for all instances to initialize with real hardware..."
sleep 15

ALL_RUNNING=true
for p in "${PORTS[@]}"; do
    if status servod "PORT=$p" | grep -q "start/running"; then
        echo "[PASS] Servod on port $p is running."
    else
        echo "[FAIL] Servod on port $p is NOT running."
        ALL_RUNNING=false
    fi
done

if [ "$ALL_RUNNING" = false ]; then
    echo "[FAIL] One or more servod instances failed to start."
    # We won't exit immediately so we can at least try to tear down what did start
fi

echo ""
echo "======================================"
echo "=== 3. CROSS-TALK & RPC VALIDATION ==="
echo "======================================"

FAILED_TESTS=0

for p in "${PORTS[@]}"; do
    IFS=',' read -r board model serial <<< "${PORT_MAP[$p]}"
    echo "-> Testing communication & isolation for port $p (Expected Serial: $serial)..."

    # 3.1: Check Cross-talk / Isolation
    read_serial=$(dut-control -p "$p" serialname 2>/dev/null | awk -F':' '{print $2}')
    if [ "$read_serial" == "$serial" ]; then
        echo "  [PASS] Port $p mapped correctly to $serial"
    else
        echo "  [FAIL] Cross-talk or bind failure! Port $p expected $serial, got '$read_serial'"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi

    # 3.2: Test Telemetry Collection
    if dut-power -p "$p" -t 2 >/dev/null 2>&1; then
        echo "  [PASS] dut-power executed successfully on port $p"
    else
        echo "  [FAIL] dut-power failed on port $p"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
done

echo ""
echo "======================================"
echo "=== 4. TEARDOWN & LOG COLLECTION   ==="
echo "======================================"

for p in "${PORTS[@]}"; do
    echo "Stopping servod on port $p..."
    stop servod "PORT=$p"

    LOG_PATH="/var/log/servod_$p/latest.DEBUG"
    if [ -f "$LOG_PATH" ]; then
        echo "  [INFO] Log generated at $LOG_PATH"
    else
        echo "  [WARN] Log file not found at $LOG_PATH"
    fi
done

echo "======================================"
if [ $FAILED_TESTS -eq 0 ]; then
    echo "=== MULTI-DUT TEST COMPLETE: SUCCESS ==="
else
    echo "=== MULTI-DUT TEST COMPLETE: FAILED ($FAILED_TESTS errors) ==="
    exit 1
fi
