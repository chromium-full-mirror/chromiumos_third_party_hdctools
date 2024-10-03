# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Build the Servo firmware updater python code into an distribution package."""

from setuptools import setup


setup(
    name="servo_updater",
    version="0.1",
    maintainer="chromium os",
    maintainer_email="chromium-os-dev@chromium.org",
    license="Chromium",
    url="https://www.chromium.org/chromium-os/ec-development",
    install_requires=["servo"],
    package_dir={"servo_updater": "."},
    packages=["servo_updater", "servo_updater.ecusb"],
    entry_points={
        "console_scripts": ["servo_updater=servo_updater.servo_updater:main"],
    },
    data_files=[
        (
            "share/servo_updater/configs",
            [
                "c2d2.json",
                "servo_v4.json",
                "servo_v4p1.json",
                "servo_micro.json",
                "sweetberry.json",
            ],
        )
    ],
    description="Servo usb updater.",
)
