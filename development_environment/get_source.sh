#!/bin/bash
# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

git clone https://chromium.googlesource.com/chromiumos/third_party/hdctools
git clone https://chromium.googlesource.com/chromiumos/platform/ec


function setup_git() {
    cd "${1}"
    git config --global user.email "${2}"
    git config --global user.name "${3}"
    git config --local remote.origin.review https://chromium-review.googlesource.com
    f=`git rev-parse --git-dir`/hooks/commit-msg ; mkdir -p $(dirname $f)
    curl -Lo $f https://gerrit-review.googlesource.com/tools/hooks/commit-msg
    chmod +x $f
}

read -p "Enter Your Email (chromium.org if you have otherwise google.com): "  email
read -p "Enter your first and last name for Git to use in reviews "  name

for repo in [ "hdctools" "ec" ]; do
    setup_git ${repo} "${email}" "${name}"
done

# Let the user know to set up git credentials
echo "In a browser go to https://www.googlesource.com/new-password and paste"
echo "the generated code into this shell."
