# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Build the Servod keyboard emulator code into an distribution package."""

from setuptools import setup


setup(
    name="usbkm232",
    version="0.1",
    package_dir={"usbkm232": ".", "": "../build"},
    py_modules=[
        "usbkm232.ctrld",
        "usbkm232.ctrlu",
        "usbkm232.enter",
        "usbkm232.space",
        "usbkm232.tab",
    ],
    packages=["usbkm232"],
    url="http://www.chromium.org",
    maintainer="chromium os",
    maintainer_email="chromium-os-dev@chromium.org",
    license="Chromium",
    description="Communicate and control usbkm232 USB keyboard device.",
    long_description="Communicate and control usbkm232 USB keyboard device.",
    entry_points={
        "console_scripts": [
            "usbkm232-ctrld = usbkm232.ctrld:main",
            "usbkm232-ctrlu = usbkm232.ctrlu:main",
            "usbkm232-enter = usbkm232.enter:main",
            "usbkm232-space = usbkm232.space:main",
            "usbkm232-tab = usbkm232.tab:main",
            "usbkm232-test = usbkm232.usbkm232:main",
        ],
    },
)
