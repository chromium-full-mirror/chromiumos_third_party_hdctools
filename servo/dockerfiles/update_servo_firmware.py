# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import subprocess
import sys


if __name__ == "__main__":
    # Start udev service.
    try:
        subprocess.check_call(["service", "udev", "start"])
    except subprocess.CalledProcessError as e:
        logging.exception("Fail to start udev service.")
        raise e

    # Invoke servo_updater.
    try:
        servo_update_command = ["servo_updater"] + sys.argv[1:]
        logging.debug(
            "Updating firmware using: {}".format(" ".join(servo_update_command))
        )
        subprocess.check_call(["servo_updater"] + sys.argv[1:])
    except subprocess.CalledProcessError as e:
        logging.exception("Fail to update firmware.")
        logging.info("Update firmware fails if servod is running.")
        raise e
