# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# pylint: skip-file

"""Build servo gRPC interfaces."""

import os
import sys

from grpc_tools import protoc


def build():
    build_directory = os.path.dirname(os.path.realpath(__file__))
    proto_directory = os.path.join(build_directory, "common", "proto")

    os.environ["PATH"] = build_directory + ":" + os.environ["PATH"]

    # Calculate grpc_tools proto include path manually
    import grpc_tools

    grpc_tools_dir = os.path.dirname(grpc_tools.__file__)
    proto_include = os.path.join(grpc_tools_dir, "_proto")

    files = [
        os.path.join(proto_directory, f)
        for f in os.listdir(proto_directory)
        if f.endswith(".proto")
    ]
    print(files)
    protoc.main(
        [
            "grpc_tools.protoc",
            f"-I{build_directory}",
            f"-I{proto_include}",
            f"--python_out={build_directory}",
            f"--custom_grpc_out={build_directory}",
        ]
        + files
    )


if __name__ == "__main__":  # pragma: no cover
    build()
