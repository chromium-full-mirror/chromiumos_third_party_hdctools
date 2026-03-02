#!/bin/bash
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

echo "=========================================================="
echo "    SERVOD LOCAL AGENT BOOTSTRAPPER                       "
echo "=========================================================="

CLOUDTOP_HOST=$1

if [ -z "$CLOUDTOP_HOST" ]; then
    echo "Usage: ./bootstrap_agent.sh <YOUR_CLOUDTOP_HOSTNAME>"
    echo "Example: ./bootstrap_agent.sh haddowk.c.googlers.com"
    exit 1
fi

echo "[1/4] Establishing SSH Tunnel to $CLOUDTOP_HOST..."
# Check if tunnel is already up
if pgrep -f "ssh -fN -L 5002:localhost:5000" > /dev/null; then
    echo "  -> Tunnel already active."
else
    ssh -fN -L 5002:localhost:5000 "$CLOUDTOP_HOST"
    if [ $? -eq 0 ]; then
        echo "  -> Tunnel established on port 5002."
    else
        echo "  -> FAILED to establish tunnel. Are your keys configured?"
        exit 1
    fi
fi

echo "[2/4] Fetching latest local_agent.py..."
scp -q -o StrictHostKeyChecking=no "$CLOUDTOP_HOST:/usr/local/google/home/haddowk/chromiumos2/src/third_party/hdctools/servo/tests/hardware/orchestrator/local_agent.py" ./local_agent.py
chmod +x ./local_agent.py

echo "[3/4] Checking Docker Artifact Registry Auth..."
if gcloud auth print-access-token &> /dev/null; then
    echo "  -> gcloud is authed."
else
    echo "  -> gcloud is NOT authed. Running login..."
    gcloud auth login
fi
gcloud auth configure-docker us-docker.pkg.dev --quiet

echo "[4/4] Starting Local Agent..."
echo "=========================================================="
./local_agent.py
