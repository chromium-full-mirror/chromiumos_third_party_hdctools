# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Build the Servo firmware manufacturing code python code
   into an distribution package.
"""

from setuptools import setup

import servo.sversion_util as svu


__version__ = svu.setuptools_version()

setup(
    name="servo_mfg",
    version=__version__,
    py_modules=["servo_mfg"],
    package_dir={"servo_mfg": "../servo_mfg"},
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
            "mfg_servo_v4 = servo_mfg.mfg_servo_v4:flash_v4",
            "mfg_servo_v4_1 = servo_mfg.mfg_servo_v4:flash_v4point1",
            "mfg_servo_micro = servo_mfg.mfg_servo_micro:main",
            "mfg_c2d2 = servo_mfg.mfg_c2d2:main",
            "servo_mfg = servo_mfg.main:main",
        ],
    },
)
