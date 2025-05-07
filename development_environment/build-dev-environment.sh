#!/bin/bash
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# Allow vscode IDE to open windows on the host machine x windows.

function download_file_from_git() {
    curl "https://chromium.googlesource.com/chromiumos/third_party/hdctools/+/refs/heads/main/development_environment/${1}?format=TEXT" | base64 -d > "${1}"
}

download_file_from_git "start-dev-environment.sh"
# Install a script to start the container that has the servod build environment.
sudo install start-dev-environment.sh /usr/local/bin
