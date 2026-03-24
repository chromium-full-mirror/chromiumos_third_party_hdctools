# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Build the Servod python code into an distribution package."""

import importlib
import os
import sys

from setuptools import setup
from setuptools.command import build_py


def generate_proto(proto_dir, source):
    """Invokes the Protocol Compiler to generate stubs from the given .proto file."""
    # pylint: disable=import-outside-toplevel,import-error
    import grpc_tools
    import grpc_tools.protoc

    # We want the output in the same directory as the source for the servo package
    # but we must ensure paths are absolute or relative to the setup.py location.

    protoc_command = [
        "grpc_tools.protoc",
        f"-I{os.path.dirname(proto_dir)}",
        f"-I{proto_dir}",
        # Add grpc_tools include path
        f"-I{os.path.join(os.path.dirname(grpc_tools.__file__), '_proto')}",
        f"--python_out={os.path.dirname(proto_dir)}",
        f"--grpc_python_out={os.path.dirname(proto_dir)}",
        os.path.join(proto_dir, source),
    ]

    if grpc_tools.protoc.main(protoc_command) != 0:
        sys.stderr.write(f"Error: {protoc_command} failed\n")
        sys.exit(-1)


class ServoBuildPy(build_py.build_py):
    """Custom build_py class for servod to do setup"""

    def build_ina_maps(self):
        """Generate .xml servod configuration files from the servo/data/*.py"""
        data_dir = self.get_package_dir("servo.data")
        module_name = "generate_ina_controls"
        spec = importlib.util.spec_from_file_location(
            module_name, os.path.join(data_dir, f"{module_name}.py")
        )
        module = importlib.util.spec_from_file_location(
            module_name, os.path.join(data_dir, f"{module_name}.py")
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.GenerateINAControls(data_dir)

    def build_protos(self):
        """Build all protos in common/proto."""
        proto_dir = os.path.join(os.path.dirname(__file__), "common", "proto")
        if not os.path.exists(proto_dir):
            return

        for f in os.listdir(proto_dir):
            if f.endswith(".proto"):
                print(f"Generating stubs for {f}...")
                generate_proto(proto_dir, f)

    def run(self):
        """Build INA maps and protos."""
        self.build_protos()
        self.build_ina_maps()
        build_py.build_py.run(self)


setup(
    name="servo",
    version="0.1",
    package_dir={"": "../build", "servo": "."},
    py_modules=["servo.core.servod", "servo.core.dut_control"],
    packages=[
        "servo",
        "servo.core",
        "servo.core.grpc_server",
        "servo.data",
        "servo.data.config",
        "servo.data.grpc_server",
        "servo.data.impl",
        "servo.drv",
        "servo.common.interface",
        "servo.tools",
        "servo.utils",
        "servo.utils.linux",
        "servo.core.grpc_server.impl",
        "servo.scripts",
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
            "common/proto/*.proto",
            "common/proto/*.textproto",
        ],
    },
    cmdclass={"build_py": ServoBuildPy},
    url="http://www.chromium.org",
    maintainer="chromium os",
    maintainer_email="chromium-os-dev@chromium.org",
    license="Chromium",
    description="Server to communicate and control servo debug board.",
    long_description="Server to communicate and control servo debug board.",
    entry_points={
        "console_scripts": [
            "servod = servo.core.servod:main",
            "servod-fission = servo.core.servod:main",
            "dut-control = servo.core.dut_control:main",
            "dut-power = measurement_tools.dut_power:main",
            "servodutil = servo.core.servodtool:servodutil",
            "servodtool = servo.core.servodtool:main",
            "servoflex_test_v2 = servo.scripts.servoflex_test_v2:main",
        ],
    },
)
