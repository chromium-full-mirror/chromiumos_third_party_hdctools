#!/bin/bash
# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

set -eo pipefail

if [ -n "${SERVOD_BOOTSTRAP_DEBUG}" ]; then
  set -x
fi

pushd "$(dirname "$(readlink -f "$0")")" > /dev/null
checksum=$(tar cfP - ../development_environment/ | md5sum)
script_name=$(basename "$0")
image_exists=$(docker images -q servod-bootstrap:latest 2> /dev/null)

if [ -z "${image_exists}" ] ||
   [ ! -f checksum ] ||
   [ "$(cat checksum)" != "${checksum}" ]; then
    export DOCKER_BUILDKIT=1
    docker build -f Dockerfile.bootstrap -t servod-bootstrap ../development_environment
    echo "${checksum}" > checksum
fi
popd > /dev/null

# If bootstrap is no more, revert commit done for b:400921593
if [ -f "${HOME}/.servodrc" ]; then
  SERVODRC="${HOME}/.servodrc"
fi

docker run --rm -e SERVODRC="${SERVODRC}" \
    -v /var/run/docker.sock:/var/run/docker.sock:rw \
    -v /tmp:/tmp:rw servod-bootstrap "./${script_name}.py" "$@"
exit $?
