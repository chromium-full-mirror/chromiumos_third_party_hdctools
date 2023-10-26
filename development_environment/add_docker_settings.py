#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import json
import sys

INSECURE_REG_KEY = "insecure-registries"


def add_insecure_registry(new_ip_address):

    settings = {INSECURE_REG_KEY: [new_ip_address]}
    try:
        with open("/etc/docker/daemon.json", "r") as settings_file:
            file_contents = settings_file.read()
            if file_contents:
                settings = json.loads(file_contents)
                if INSECURE_REG_KEY in settings:
                    if new_ip_address not in settings[INSECURE_REG_KEY]:
                        settings[INSECURE_REG_KEY].append(new_ip_address)
                else:
                    settings[INSECURE_REG_KEY] = [new_ip_address]
    except FileNotFoundError:
        pass

    with open("/etc/docker/daemon.json", "w") as settings_file:
        settings_file.write(json.dumps(settings, sort_keys=True, indent=4))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        add_insecure_registry(sys.argv[1])
