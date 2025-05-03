#!/bin/bash
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

set -e

git clone https://chromium.googlesource.com/chromiumos/third_party/hdctools

function setup_git() {
    cd "${1}"
    git config --global user.email "${2}"
    git config --global user.name "${3}"
    git config --local remote.origin.review https://chromium-review.googlesource.com
    f=$(git rev-parse --git-dir)/hooks/commit-msg ; mkdir -p "$(dirname "${f}")"
    curl -Lo "${f}" https://gerrit-review.googlesource.com/tools/hooks/commit-msg
    chmod +x "${f}"
}

read -rp "Enter Your Email (chromium.org if you have otherwise google.com): "  email
read -rp "Enter your first and last name for Git to use in reviews "  name

for repo in [ "hdctools" ]; do
    setup_git "${repo}" "${email}" "${name}"
done

# Setup pre-commit
cd hdctools
pre-commit install

# Let the user know to set up git credentials
printf "\n\n\e[6;33mIn a browser go to\e[0m\e[33m https://www.googlesource.com/new-password\e[6;33m and paste\e[0m"
printf "\e[6;33m the generated code into this shell.\n\n\e[0m"
