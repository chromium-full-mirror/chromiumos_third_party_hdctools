#!/bin/bash
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

mkdir -p ${HOME}/webserver_file_cache
docker pull 127.0.1.1:5000/devwebserver
docker run -d --rm \
    --name devwebserver --hostname devwebserver \
    -v ${HOME}/webserver_file_cache:/file_cache \
    -p 80:8081 \
    127.0.1.1:5000/devwebserver
