#!/usr/bin/env python3
# Copyright 2011 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Based on suggestions in http://guide.python-distribute.org/creation.html
# ...with a mix of bits from pymox.

import importlib
import os

from setuptools import setup
from setuptools.command import build_py

import servo.sversion_util as svu


__version__ = svu.setuptools_version()


class servo_build_py(build_py.build_py):
    """Custom build_py class for servod to do setup"""

    # The only reason we include the servo.data package is to build INA
    # XML configuration files from simplified .py files. So we pop it
    # out to avoid building the python files.
    # See generate_ina_controls.py & servo/data/README.md for more
    # information.

    def build_ina_maps(self):
        """Generate .xml servod configuration files from the servo/data/*.py"""
        # get package_data files
        # run generate_ina_controls.py over all the files,
        # giving the file an output directory?
        data_dir = self.get_package_dir(self.packages.pop(1))
        module_name = "generate_ina_controls"
        spec = importlib.util.spec_from_file_location(
            module_name, "%s/%s.py" % (data_dir, module_name)
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.GenerateINAControls(data_dir)

    def run(self):
        """Build INA maps."""
        self.build_ina_maps()
        build_py.build_py.run(self)


if "PACKAGE" in os.environ and os.environ["PACKAGE"] == "servo":
    setup(
        name="servo",
        version=__version__,
        package_dir={"": "build"},
        py_modules=["servo.servod", "servo.dut_control"],
        packages=[
            "servo",
            "servo.data",
            "servo.data.config",
            "servo.data.grpc_server",
            "servo.data.impl",
            "servo.data.drv",
            "servo.common.interface",
            "servo.tools",
            "servo.utils",
            "servo.utils.linux",
            "servo.tests",
            "servo.grpc_server",
            "servo.grpc_server.impl",
            "servo.tests.e2e",
            "servo.tests.fixtures",
            "servo.tests.unit",
            "servo.tests.data",
            "servo.common",
            "servo.common.config",
            "servo.common.proto",
            "servo.common.utils",
        ],
        package_data={
            "servo": [
                "data/*.xml",
                "data/*.scenario",
                "data/*.board",
                "common/proto/*.textproto",
                "common/proto/*.proto",
            ],
        },
        cmdclass={"build_py": servo_build_py},
        url="http://www.chromium.org",
        maintainer="chromium os",
        maintainer_email="chromium-os-dev@chromium.org",
        license="Chromium",
        description="Server to communicate and control servo debug board.",
        long_description="Server to communicate and control servo debug board.",
        entry_points={
            "console_scripts": [
                "servod = servo.servod:main",
                "dut-control = servo.dut_control:main",
                "dut-power = servo.dut_power:main",
                "servodutil = servo.servodtool:servodutil",
                "servodtool = servo.servodtool:main",
            ],
        },
    )

if "PACKAGE" in os.environ and os.environ["PACKAGE"] == "usbkm232":
    setup(
        name="usbkm232",
        version=__version__,
        package_dir={"": "build"},
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

if "PACKAGE" in os.environ and os.environ["PACKAGE"] == "ec3po":
    setup(
        name="ec3po",
        version="1.0.0rc1",
        maintainer="chromium os",
        maintainer_email="chromium-os-dev@chromium.org",
        license="Chromium",
        url="http://www.chromium.org",
        packages=["ec3po"],
        py_modules=["ec3po.console", "ec3po.interpreter"],
        description="EC console interpreter.",
    )

if "PACKAGE" in os.environ and os.environ["PACKAGE"] == "servo_updater":
    setup(
        name="servo_updater",
        version=__version__,
        maintainer="chromium os",
        maintainer_email="chromium-os-dev@chromium.org",
        license="Chromium",
        url="https://www.chromium.org/chromium-os/ec-development",
        install_requires=["servo"],
        packages=["servo_updater", "servo_updater.ecusb"],
        entry_points={
            "console_scripts": ["servo_updater=servo_updater.servo_updater:main"],
        },
        data_files=[
            (
                "share/servo_updater/configs",
                [
                    "servo_updater/c2d2.json",
                    "servo_updater/servo_v4.json",
                    "servo_updater/servo_v4p1.json",
                    "servo_updater/servo_micro.json",
                    "servo_updater/sweetberry.json",
                ],
            )
        ],
        description="Servo usb updater.",
    )

if "PACKAGE" in os.environ and os.environ["PACKAGE"] == "data_grpc_server":
    setup(
        name="data_grpc_server",
        version=__version__,
        maintainer="chromium os",
        maintainer_email="chromium-os-dev@chromium.org",
        license="Chromium",
        url="https://www.chromium.org/chromium-os/ec-development",
        install_requires=[""],
        packages=[""],
        entry_points={
            "console_scripts": [
                "servo_updater=data.grpc_server.grpc_server_setup:main"
            ],
        },
        description="data gRPC server setup.",
    )

if "PACKAGE" in os.environ and os.environ["PACKAGE"] == "data_grpc_server":
    setup(
        name="data_grpc_server",
        version=__version__,
        maintainer="chromium os",
        maintainer_email="chromium-os-dev@chromium.org",
        license="Chromium",
        url="https://www.chromium.org/chromium-os/ec-development",
        install_requires=[""],
        packages=[""],
        entry_points={
            "console_scripts": [
                "servo_updater=data.grpc_server.grpc_server_setup:main"
            ],
        },
        description="data gRPC server setup.",
    )
