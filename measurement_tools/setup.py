# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from setuptools import setup
from setuptools.command import build_py


class BuildPy(build_py.build_py):
    def run(self):
        build_py.build_py.run(self)


setup(
    name="measurement_tools",
    version="0.1",
    package_dir={"measurement_tools": ".", "measurement_tools.utils": "./utils"},
    py_modules=[
        "measurement_tools.__init__",
        "measurement_tools.dut_power_data",
        "measurement_tools.dut_power",
        "measurement_tools.http_server",
        "measurement_tools.measure_power",
        "measurement_tools.servo_parsing",
        "measurement_tools.utils.__init__",
        "measurement_tools.utils.stats_manager",
        "measurement_tools.utils.timelined_stats_manager",
    ],
    scripts=[],
    entry_points={
        "console_scripts": [
            "dut-power = measurement_tools.dut_power:main",
        ],
    },
    cmdclass={"build_py": BuildPy},
)
