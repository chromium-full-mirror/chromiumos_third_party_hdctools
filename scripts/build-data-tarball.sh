#!/bin/bash
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Builds the servod_data service as a standalone tarball.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT"

# Set the default bucket URL. Can be overridden by SERVOD_DATA_BUCKET.
# If set to "None", OTA updates are disabled.
DEFAULT_BUCKET="https://storage.googleapis.com/servod_data/staging"
BUCKET_URL="${SERVOD_DATA_BUCKET:-$DEFAULT_BUCKET}"

if [ "$BUCKET_URL" == "None" ]; then
    echo "OTA updates are disabled (SERVOD_DATA_BUCKET=None). Skipping build."
    exit 0
fi

# Check for --upload flag
UPLOAD=false
if [[ "$*" == *"--upload"* ]]; then
    UPLOAD=true
fi

# Presubmit check: Disable upload if we have commits not in origin/main
if git rev-parse origin/main >/dev/null 2>&1; then
    if [ -n "$(git rev-list origin/main..HEAD)" ]; then
        echo "Detected unmerged commits (Gerrit presubmit). Disabling OTA upload to prevent 403 Access Denied."
        UPLOAD=false
    fi
fi

echo "Building for bucket: $BUCKET_URL"

echo "Setting up temporary virtual environment..."
VENV_DIR=$(mktemp -d)
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

echo "Generating protos..."
pip install grpcio-tools > /dev/null
python servo/grpc.py

echo "Generating version file..."
./getversion.sh > servo/sversion.py

echo "Staging tarball directory..."
TMP_DIR=$(mktemp -d)
STAGING_DIR="$TMP_DIR/servod_data"
mkdir -p "$STAGING_DIR"

echo "Downloading standard pure-python dependencies..."
# Install dependencies into the staging directory FIRST.
# We use --no-deps to avoid pulling in external packages.
pip install --target "$STAGING_DIR" --no-deps --require-hashes -r scripts/data_requirements.txt > /dev/null

echo "Copying local source code..."
# Copy local source code AFTER dependencies to ensure it takes precedence
# and is not overwritten by registry packages.
# For the data service, we only need common, data, tools, and utils.
# We explicitly exclude core, dockerfiles, scripts, and test_plans to save space.
mkdir -p "$STAGING_DIR/servo"
cp -rL servo/__init__.py "$STAGING_DIR/servo/"
cp -rL servo/common "$STAGING_DIR/servo/"
cp -rL servo/data "$STAGING_DIR/servo/"
cp -rL servo/drv "$STAGING_DIR/servo/"
cp -rL servo/tools "$STAGING_DIR/servo/"
cp -rL servo/utils "$STAGING_DIR/servo/"
cp -rL servo/sversion.py "$STAGING_DIR/servo/"

cp -rL ec3po "$STAGING_DIR/"
cp -rL usbkm232 "$STAGING_DIR/"
cp -rL servo_updater "$STAGING_DIR/"

echo "Generating INA controls inside staging directory..."
python "$STAGING_DIR/servo/data/generate_ina_controls.py" --input "$STAGING_DIR/servo/data"

echo "Building servod_data.tar.gz..."
tar -czf servod_data.tar.gz -C "$TMP_DIR" servod_data

# Extract the hash from the generated version file
HASH=$(grep "'ghash':" servo/sversion.py | cut -d"'" -f4)
MIN_API_VERSION=$(python3 -c "import sys; import os; sys.path.insert(0, os.getcwd()); import servo.common.api_version; print(servo.common.api_version.CORE_API_VERSION)")
echo "${HASH}:${MIN_API_VERSION}" > servod_data.version

rm -rf "$TMP_DIR"
echo "Successfully built servod_data.tar.gz and servod_data.version"

if [ "$UPLOAD" = true ]; then
    echo "Uploading to $BUCKET_URL..."
    # Convert https URL to gs:// URL for gsutil if needed
    GS_PATH=${BUCKET_URL/https:\/\/storage.googleapis.com\//gs:\/\/}
    gsutil cp servod_data.tar.gz "$GS_PATH/"
    gsutil cp servod_data.version "$GS_PATH/"
    echo "Upload complete."
fi

echo "You can extract it and run it via: PYTHONPATH=./servod_data python3 -m servo.data.grpc_server.grpc_server_setup --port=9999"
