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
cp start-servod.py \
    stop-servod.py \
    servod-ps.py \
    dut-control.py \
    servodtool.py \
    servo_updater.py \
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

echo "Package: servod" > servod/DEBIAN/control
echo "Version: ${date}+${short_hash}" >> servod/DEBIAN/control
echo "Maintainer: ChromeOS Developers" >> servod/DEBIAN/control
echo "Architecture: all" >> servod/DEBIAN/control
echo "Description: Script that allow easy start/stop of servod" >> servod/DEBIAN/control
echo "Depends: python3, docker-ce, docker-ce-cli, containerd.io" >> servod/DEBIAN/control

dpkg-deb --build servod
rm -rf servod
