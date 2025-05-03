#!/bin/bash
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

IMAGE=us-docker.pkg.dev/chromeos-hw-tools/servod/dev_env:latest

function download_file_from_git() {
    curl "https://chromium.googlesource.com/chromiumos/third_party/hdctools/+/refs/heads/main/development_environment/${1}?format=TEXT" | base64 -d > "${1}"
}

tmpdir=$(mktemp -d)
cd "${tmpdir}" || exit

download_file_from_git "Dockerfile.local"

docker pull "${IMAGE}"
docker build -t hdctoolsdev:latest \
    --build-arg USER="${USER}" \
    --build-arg  USERID="$(id -u)" \
    -f "${tmpdir}"/Dockerfile.local "${tmpdir}"

cd - || exit
rm -rf "${tmpdir}"

docker run --rm --net host \
    --env DISPLAY=unix"${DISPLAY}" --privileged \
    --volume /tmp/.X11-unix:/tmp/.X11-unix  --shm-size=5g --user "${USER}" \
    --ulimit nofile=200000:200000 -e USER="${USER}" \
    -v "${HOME}":/home/"${USER}" \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v "$(pwd)":/hdctools_source -it -t hdctoolsdev:latest
