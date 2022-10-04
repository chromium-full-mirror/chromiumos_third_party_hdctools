#!/bin/bash
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# Install a script to start the container that has the servod build environment.
sudo install start_dev_environment.sh /usr/local/bin
sudo install start_dev_webserver.sh /usr/local/bin
# Allow vscode IDE to open windows on the host machine x windows.
xhost +
function download_file_from_git() {
    curl https://chromium.googlesource.com/chromiumos/third_party/hdctools/+/refs/heads/main/development_environment/${1}?format=TEXT | base64 -d > ${1} 
}
for s in "add_docker_settings.py" \
         "start_dev_environment.sh" \
         "start_dev_webserver.sh" \
         "requirements.txt" \
         "nginx.conf" \
         "local-docker-registry" \
         "local-docker-proxy" \
         "Dockerfile.webserver" \
         "Dockerfile" \
         "entry.sh" \
         "get_source.sh" \
         "start_servod.py" \
         "build_servod.sh" ; do
    download_file_from_git ${s}
done
# Allow docker to communicate with your local registry over http vs https, installing
# a certificate on your local machine is pretty heavyweight and uncessesary for
# communication on a single machine (IMO)
sudo service docker stop
sudo python3 add_docker_settings.py $(hostname -i | awk -F ' ' '{print $1}'):5000
sudo cat /etc/docker/daemon.json
sudo service docker start
function install_service() {
    sudo cp "${1}" /etc/init.d
    sudo chmod 755 /etc/init.d/"${1}"
    sudo systemctl daemon-reload
    sudo systemctl stop "${1}".service || true
    sudo systemctl enable "${1}".service
    sudo systemctl start "${1}".service
}
# Install a systemd configuration so every time to boot your device a
# local docker registry and docker network proxy is started.
for s in "local-docker-proxy" "local-docker-registry" ; do
    install_service ${s}
done
# The cros_sdk logic that starts containerized servod expects to be on a moblab
# so it needs this network to exist.
docker network create default_moblab || true

docker build -t 127.0.1.1:5000/hdctoolsdev --build-arg USER=$USER --build-arg  USERID=$(id -u) .
docker push 127.0.1.1:5000/hdctoolsdev
docker build -t 127.0.1.1:5000/devwebserver -f Dockerfile.webserver .
docker push 127.0.1.1:5000/devwebserver
