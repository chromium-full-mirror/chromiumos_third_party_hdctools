#!/bin/bash
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


set -x
set -e

date=$(date +"%y.%m.%d%H%M")
short_hash=$(git rev-parse --short HEAD || echo "localbuild")

mkdir -p servod/usr/local/servod/development_environment
mkdir -p servod/usr/local/servod/scripts
mkdir -p servod/usr/local/bin
mkdir servod/DEBIAN

cd development_environment/
cp start_servod.py \
    stop_servod.py \
    servod_ps.py \
    dut_control.py \
    servodtool.py \
    run_command.py \
    run_instead.py \
    ../servod/usr/local/servod/development_environment/
cd -

cd scripts
cp bootstrap.sh \
  Dockerfile.bootstrap \
  ../servod/usr/local/servod/scripts/
cd -

cd servod/usr/local/bin/
ln -s /usr/local/servod/scripts/bootstrap.sh \
    ./start-servod
ln -s /usr/local/servod/scripts/bootstrap.sh \
    ./stop-servod
ln -s /usr/local/servod/scripts/bootstrap.sh \
    ./servod-ps
ln -s /usr/local/servod/scripts/bootstrap.sh \
    ./dut-control
ln -s /usr/local/servod/scripts/bootstrap.sh \
    ./servodtool
ln -s /usr/local/servod/scripts/bootstrap.sh \
    ./servo_updater
cd -

{
    echo "Package: servod"
    echo "Version: ${date}+${short_hash}"
    echo "Maintainer: ChromeOS Developers"
    echo "Architecture: all"
    echo "Description: Script that allow easy start/stop of servod"
    echo "Depends: python3, docker-ce, docker-ce-cli, containerd.io"
} > servod/DEBIAN/control

dpkg-deb --build servod
rm -rf servod
