#!/bin/bash
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This script is meant to be run directly on the labstation/DUT.
# It sets up the environment and starts the local_agent.py daemon.

set -e

# --- Configurations ---
if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <cloudtop_host> <hdctools_path> [port]"
    echo "Example: $0 myhost.c.googlers.com /usr/local/google/home/user/hdctools"
    exit 1
fi

CLOUDTOP_HOST="$1"
HDCTOOLS_PATH="$2"
CLOUDTOP_PORT="${3:-22}"

AGENT_DIR="${HOME}/servod_orchestrator"
CONTROL_SOCK="/tmp/orchestrator_ssh_mux.sock"

# --- Bootstrap ---
echo "=========================================================="
echo "    Servod Hardware Test - Local Agent Bootstrap"
echo "=========================================================="

echo "[0/4] Cleaning up stale local processes and sockets..."
# Kill any existing agent or tunnel using port 5002
if lsof -ti:5002 >/dev/null 2>&1; then
    echo "  -> Port 5002 is in use. Terminating existing process..."
    lsof -ti:5002 | xargs kill -9 2>/dev/null || true
fi

# Remove stale multiplexing socket
rm -f "$CONTROL_SOCK"

mkdir -p "$AGENT_DIR"
cd "$AGENT_DIR"

echo "[1/4] Starting multiplexed SSH connection to Cloudtop..."
# Start a primary SSH connection in the background (removed -q to see errors)
if ssh -M -o "ControlPath=$CONTROL_SOCK" -o "ControlPersist=10m" -f -N "$CLOUDTOP_HOST" -p "$CLOUDTOP_PORT"; then
    echo "  -> Primary tunnel established."
else
    echo "  -> FAILED to establish primary connection."
    exit 1
fi

# Ensure the socket is cleaned up on exit
trap 'ssh -O exit -o "ControlPath=$CONTROL_SOCK" "$CLOUDTOP_HOST" 2>/dev/null || true' EXIT

echo "[2/4] Fetching latest local_agent.py and scripts via multiplexed connection..."
scp -o "ControlPath=$CONTROL_SOCK" -q -o StrictHostKeyChecking=no "$CLOUDTOP_HOST:$HDCTOOLS_PATH/tests/hardware/orchestrator/local_agent.py" ./local_agent.py
chmod +x ./local_agent.py

# Sync multiple paths in one SCP command if possible, or sequentially reusing the socket
scp -o "ControlPath=$CONTROL_SOCK" -q -r -o StrictHostKeyChecking=no \
    "$CLOUDTOP_HOST:$HDCTOOLS_PATH/scripts" \
    "$CLOUDTOP_HOST:$HDCTOOLS_PATH/development_environment" ./ 2>/dev/null || true

echo "[3/4] Establishing secure local tunnel (port 5002) via multiplexed connection..."
# Use the existing multiplexed connection to forward the port
# We use -L because the agent (on the DUT) connects to the orchestrator (on Cloudtop)
if ssh -o "ControlPath=$CONTROL_SOCK" -O forward -L 5002:localhost:5002 "$CLOUDTOP_HOST" -p "$CLOUDTOP_PORT" 2>/dev/null; then
    echo "  -> Port 5002 forwarded successfully."
else
    echo "ERROR: Failed to establish local tunnel. Cloudtop might be unreachable or port 5002 is in use."
    exit 1
fi

echo "[4/4] Starting Local Agent..."
echo "=========================================================="
# Run the agent in the foreground. If it exits, the script exits and the trap kills the tunnel.
./local_agent.py --orchestrator_url "http://localhost:5002"
