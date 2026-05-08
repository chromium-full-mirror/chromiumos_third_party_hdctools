#!/bin/bash
# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

set -eo pipefail

if [ -n "${SERVOD_BOOTSTRAP_DEBUG}" ]; then
  set -x
fi

# Check that Googlers installed docker and setup sudoless.

# Check to see glinux machines have correct environment.
if [ -f "/usr/bin/glinux-updater" ]; then
  if ! systemctl is-active docker --quiet; then
    echo "Docker is not running see go/servod for install instructions."
    exit 1
  fi
  if ! groups "${USER}" | grep -qw docker; then
    echo "${USER} is not in the group docker see go/installdocker#sudoless-docker."
    echo "remember to reboot after following the instructions."
    exit 1
  fi
fi

pushd "$(dirname "$(readlink -f "$0")")" > /dev/null
checksum=$(tar cfP - ../development_environment/ | md5sum)
script_name=$(basename "$0")
# Replace all hyphens with underscores
script_name="${script_name//-/_}"
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

if [ -t 0 ] && [ -t 1 ]; then
  TTY_FLAG="-t"
else
  TTY_FLAG=""
fi

docker run -i ${TTY_FLAG} --rm -e SERVODRC="${SERVODRC}" -e HOST_PWD="${PWD}" \
    -v /var/run/docker.sock:/var/run/docker.sock:rw \
    -v /tmp:/tmp:rw servod-bootstrap "./${script_name}.py" "$@"
exit $?
