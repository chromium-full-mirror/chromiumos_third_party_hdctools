#!/bin/bash
# Copyright 2023 The ChromiumOS Authors
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

# Build/Verify bases locally without relying on remote registry access
docker build -t servod-builder-base:local --target hdctools-builder-base \
    -f "${DIR}"/../dockerfiles/Dockerfile.base "${DIR}"/..

docker build -t servod-base:local --target base \
    -f "${DIR}"/../dockerfiles/Dockerfile.base "${DIR}"/..

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
	    -f "${DIR}"/../dockerfiles/Dockerfile "${DIR}"/..
else
     docker build --no-cache -t "${IMAGE}" \
        --build-arg BUILDER_BASE_IMG=servod-builder-base:local \
        --build-arg BASE_IMG=servod-base:local \
        -f "${DIR}"/../dockerfiles/Dockerfile "${DIR}"/..
fi
