#!/bin/bash
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

echo "=========================================================="
echo "    SERVOD LOCAL AGENT BOOTSTRAPPER                       "
echo "=========================================================="

CLOUDTOP_HOST=$1

if [ -z "$CLOUDTOP_HOST" ]; then
    echo "Usage: ./bootstrap_agent.sh <YOUR_CLOUDTOP_HOSTNAME> [HDCTOOLS_PATH]"
    echo "Example: ./bootstrap_agent.sh username.c.googlers.com"
    exit 1
fi

HDCTOOLS_PATH=$2

if [ -z "$HDCTOOLS_PATH" ]; then
    read -r -p "Enter the absolute path to your hdctools checkout on $CLOUDTOP_HOST [~/chromiumos/src/third_party/hdctools]: " USER_INPUT
    HDCTOOLS_PATH=${USER_INPUT:-"~/chromiumos/src/third_party/hdctools"}
fi

# Authenticate once outside the loop
gcloud config unset context_aware/certificate_config_file_path || true
echo "[3/4] Checking Docker Artifact Registry Auth..."
if gcloud auth print-access-token &> /dev/null; then
    echo "  -> gcloud is authed."
else
    echo "  -> gcloud is NOT authed. Running login..."
    gcloud auth login
fi
gcloud auth configure-docker us-docker.pkg.dev --quiet

while true; do
    echo "=========================================================="
    echo "[1/4] Establishing SSH Tunnel to $CLOUDTOP_HOST..."
    # Forcefully kill any existing tunnel on the port to ensure a clean connection
    if pgrep -f "ssh .* -L 5002:127.0.0.1:5002" > /dev/null; then
        echo "  -> Found existing tunnel. Stopping it..."
        pkill -f "ssh .* -L 5002:127.0.0.1:5002"
        sleep 1
    fi

    # Added robust SSH keepalive and exit options
    if ssh -o ServerAliveInterval=60 -o ServerAliveCountMax=120 -o TCPKeepAlive=yes -o ExitOnForwardFailure=yes -fN -L 5002:127.0.0.1:5002 "$CLOUDTOP_HOST"; then
        echo "  -> Tunnel established on port 5002."
    else
        echo "  -> FAILED to establish tunnel. Are your keys configured?"
        exit 1
    fi

    echo "[2/4] Fetching latest local_agent.py..."
    scp -q -o StrictHostKeyChecking=no "$CLOUDTOP_HOST:$HDCTOOLS_PATH/tests/hardware/orchestrator/local_agent.py" ./local_agent.py
    chmod +x ./local_agent.py

    echo "[4/4] Starting Local Agent..."
    echo "=========================================================="
    ./local_agent.py
    AGENT_EXIT_CODE=$?

    if [ $AGENT_EXIT_CODE -eq 2 ]; then
        echo ""
        echo "=========================================================="
        echo "Agent lost connection to orchestrator. Restarting tunnel..."
        echo "=========================================================="
        sleep 2
    else
        echo "Agent exited (Code: $AGENT_EXIT_CODE). Stopping."
        break
    fi
done
