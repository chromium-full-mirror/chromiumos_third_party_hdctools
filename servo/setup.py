# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Build the Servod python code into an distribution package."""

import importlib
import os
import subprocess
import sys

from setuptools import setup
from setuptools.command import build_py

import servo.sversion_util as svu


__version__ = svu.setuptools_version()


def generate_proto(source):
    """Invokes the Protocol Compiler to generate a _pb2.py from the given
    .proto file.  Does nothing if the output already exists and is newer than
    the input."""

    output = source.replace(".proto", "_pb2.py")

    if not os.path.exists(output) or (
        os.path.exists(source) and os.path.getmtime(source) > os.path.getmtime(output)
    ):
        print(f"Generating {output}...")

        if not os.path.exists(source):
            sys.stderr.write(f"Can't find required file: {source}\n")
            sys.exit(-1)

        protoc_command = [
            "python3",
            "-m",
            "grpc_tools.protoc",
            "-I=.",
            "--python_out=.",
            source,
        ]
        if subprocess.call(protoc_command) != 0:
            sys.exit(-1)


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

    def build_protos(self):
        """Build protos."""
        proto_src = ["proto/servo_dev.proto"]
        for file in proto_src:
            generate_proto(file)

    def run(self):
        """Build INA maps and protos."""
        self.build_ina_maps()
        self.build_protos()

        build_py.build_py.run(self)


setup(
    name="servo",
    version=__version__,
    package_dir={"": "../build", "servo": "../servo"},
    py_modules=["servo.servod", "servo.dut_control"],
    packages=[
        "servo",
        "servo.data",
        "servo.proto",
        "servo.drv",
        "servo.interface",
        "servo.tools",
        "servo.utils",
        "servo.utils.linux",
        "servo.tests.e2e",
        "servo.tests.fixtures",
        "servo.tests.unit",
        "servo.tests.data",
        "servo.scripts",
    ],
    package_data={
        "servo": [
            "data/*.xml",
            "data/*.scenario",
            "data/*.board",
            "proto/*.textproto",
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
            "servoflex_test_v2 = servo.scripts.servoflex_test_v2:main",
        ],
    },
)
