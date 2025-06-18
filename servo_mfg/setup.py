# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Build the Servo firmware manufacturing code python code
into an distribution package.
"""

from setuptools import setup


setup(
    name="servo_mfg",
    version="0.1",
    py_modules=["servo_mfg"],
    package_dir={"servo_mfg": "."},
    packages=["servo_mfg"],
    package_data={
        "servo_mfg": [
            "binfiles/*.hex",
            "binfiles/*.cfg",
            "binfiles/*.ini",
            "binfiles/*.bin",
            "*.sh",
        ],
    },
    url="http://www.chromium.org",
    maintainer="chromium os",
    maintainer_email="chromium-os-dev@chromium.org",
    license="Chromium",
    description="Tools to program and validate servo devices.",
    entry_points={
        "console_scripts": [
            "mfg_servo_micro = servo_mfg.mfg_servo_micro:main",
            "servo_mfg = servo_mfg.main:main",
        ],
    },
)
