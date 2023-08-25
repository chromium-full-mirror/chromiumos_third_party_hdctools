#!/bin/bash
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

sudo chmod 666 /var/run/docker.sock
bash --rcfile /usr/local/bin/bashrc
