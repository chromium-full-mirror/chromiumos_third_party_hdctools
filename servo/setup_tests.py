# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Setup script for servod tests."""

from setuptools import setup


setup(
    name="servod_tests",
    version="0.1",
    package_dir={"servo": "./servo"},
    packages=[
        "servo.tests.e2e",
        "servo.tests.fixtures",
        "servo.tests.unit",
        "servo.tests.data",
    ],
    url="http://www.chromium.org",
    maintainer="chromium os",
    maintainer_email="chromium-os-dev@chromium.org",
    license="Chromium",
    description="Server to communicate and control servo debug board.",
    long_description="Server to communicate and control servo debug board.",
)
