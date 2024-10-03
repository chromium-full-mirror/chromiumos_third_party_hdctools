# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Build the Servod ec3po interface python code into an distribution package."""

from setuptools import setup


setup(
    name="ec3po",
    version="0.1",
    maintainer="chromium os",
    maintainer_email="chromium-os-dev@chromium.org",
    license="Chromium",
    url="http://www.chromium.org",
    package_dir={"ec3po": "."},
    packages=["ec3po"],
    py_modules=["ec3po.console", "ec3po.interpreter"],
    description="EC console interpreter.",
)
