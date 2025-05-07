#!/bin/bash

# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

set -x

dut-control -p "${PORT}" "log_msg:Turning down servod."

for CMD in iptables-legacy ip6tables-legacy ; do
    $CMD -D INPUT -p tcp --dport "${PORT}" -j ACCEPT || true
done
