#!/bin/bash
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
IMAGE=us-docker.pkg.dev/chromeos-hw-tools-dev/servod/dev_env:latest
docker pull -q ${IMAGE}
docker build -q -t 127.0.1.1:5000/hdctoolsdev \
    --build-arg USER=$USER \
    --build-arg  USERID=$(id -u) \
    -f Dockerfile.local .
docker run --rm --net host \
    --env DISPLAY=unix$DISPLAY --privileged \
    --volume /tmp/.X11-unix:/tmp/.X11-unix  --shm-size=5g --user $USER \
    --ulimit nofile=200000:200000 -e USER=$USER -v $HOME:/home/$USER \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v $(pwd):/hdctools_source -it -t 127.0.1.1:5000/hdctoolsdev:latest
