#!/usr/bin/env python3
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from datetime import datetime
import os
import tempfile


def update_checker_file(command, channel):
    return os.path.join(
        tempfile.gettempdir(),
        os.path.basename(command) + "_timestamp",
        channel,
    )


def needs_update_check(docker_client, image_name, command, channel):
    """Determine whether to update the docker image for this channel."""
    # If the update check file doesn't exist yet, download the docker image.
    update_filename = update_checker_file(command, channel)
    if not os.path.exists(update_filename):
        return True

    # If the image got deleted, we'll download it again.
    if not docker_client.images.list(filters={"reference": image_name}):
        return True

    try:
        with open(update_filename, "r", encoding="utf-8") as file:
            date = file.read().strip()
            current_date = datetime.now().strftime("%Y-%m-%d")
            if date == current_date:
                return False
    except OSError:
        pass
    return True


def update_check_timestamp(command, channel):
    """Note the time when we last updated the docker image."""
    update_check_dir = os.path.dirname(update_checker_file(command, channel))
    os.makedirs(update_check_dir, exist_ok=True)
    update_filename = update_checker_file(command, channel)
    with open(update_filename, "w", encoding="utf-8") as file:
        current_date = datetime.now().strftime("%Y-%m-%d")
        file.write(current_date)
