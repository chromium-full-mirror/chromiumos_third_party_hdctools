#!/bin/bash
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

export DOCKER_BUILDKIT=1
IMAGE="servod:dev"
set -x
SOURCE="${BASH_SOURCE[0]}"
while [ -L "${SOURCE}" ]; do # resolve $SOURCE until the file is no longer a symlink
  DIR=$( cd -P "$( dirname "${SOURCE}" )" >/dev/null 2>&1 && pwd )
  SOURCE=$(readlink "${SOURCE}")
done
DIR=$( cd -P "${DIR:-.}/$( dirname "${SOURCE}" )" >/dev/null 2>&1 && pwd )

PROJECT_ID="chromeos-hw-tools"
BUILDER_BASE_REMOTE="us-docker.pkg.dev/${PROJECT_ID}/servod/servod-builder-base:latest"
BASE_REMOTE="us-docker.pkg.dev/${PROJECT_ID}/servod/servod-base:latest"

# 1. Attempt to pull nightly bases for faster local caching
docker pull "${BUILDER_BASE_REMOTE}" || true
docker pull "${BASE_REMOTE}" || true

# 2. Build/Verify bases locally
docker build -t servod-builder-base:local --target hdctools-builder-base \
    --cache-from "${BUILDER_BASE_REMOTE}" \
    -f "${DIR}"/../servo/dockerfiles/Dockerfile.base "${DIR}"/..

docker build -t servod-base:local --target base \
    --cache-from "${BASE_REMOTE}" \
    -f "${DIR}"/../servo/dockerfiles/Dockerfile.base "${DIR}"/..

if [ "$1" == "multi" ]
then
    docker buildx create \
	    --use \
	    --name insecure-builder \
	    --buildkitd-flags '--allow-insecure-entitlement network.host --allow-insecure-entitlement security.insecure' | true
    docker buildx build \
	    --platform=linux/arm64,linux/amd64 \
	    -t "${IMAGE}" \
	    -o type=image \
        --build-arg BUILDER_BASE_IMG=servod-builder-base:local \
        --build-arg BASE_IMG=servod-base:local \
	    -f "${DIR}"/../servo/dockerfiles/Dockerfile "${DIR}"/..
else
     docker build -t "${IMAGE}" \
        --build-arg BUILDER_BASE_IMG=servod-builder-base:local \
        --build-arg BASE_IMG=servod-base:local \
        -f "${DIR}"/../servo/dockerfiles/Dockerfile "${DIR}"/..
fi
