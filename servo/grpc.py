# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# pylint: skip-file

"""Build servo gRPC interfaces."""

import os

from grpc_tools import protoc
import pkg_resources


build_directory = os.path.dirname(os.path.realpath(__file__))
output_directory = os.path.dirname(os.path.realpath(__file__)) + "/proto"
package_directory = f"{build_directory}"
bt_test_interfaces_directory = f"{package_directory}"
proto_directory = f"{build_directory}/common/proto"


def build():
    os.environ["PATH"] = build_directory + ":" + os.environ["PATH"]

    proto_include = pkg_resources.resource_filename("grpc_tools", "_proto")

    files = [
        f"{proto_directory}/{f}"
        for f in os.listdir(proto_directory)
        if f.endswith(".proto")
    ]
    print(files)
    protoc.main(
        [
            "grpc_tools.protoc",
            f"-I{bt_test_interfaces_directory}",
            f"-I{proto_include}",
            f"--python_out={build_directory}",
            f"--custom_grpc_out={build_directory}",
        ]
        + files
    )


if __name__ == "__main__":
    build()
