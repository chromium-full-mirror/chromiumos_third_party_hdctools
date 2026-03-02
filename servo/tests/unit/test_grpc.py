# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import os
import unittest.mock

from servo import grpc


@unittest.mock.patch("servo.grpc.protoc.main")
@unittest.mock.patch("servo.grpc.pkg_resources.resource_filename")
@unittest.mock.patch("servo.grpc.os.listdir")
@unittest.mock.patch.dict(os.environ, {"PATH": "/usr/bin"}, clear=True)
def test_build(mock_listdir, mock_resource_filename, mock_protoc_main):
    # Setup mocks
    mock_resource_filename.return_value = "/fake/proto/include"
    mock_listdir.return_value = ["test1.proto", "test2.proto", "not_a_proto.txt"]

    # Call build
    grpc.build()

    # Check that the environment variable PATH was updated properly
    assert "/usr/bin" in os.environ["PATH"]
    assert grpc.build_directory in os.environ["PATH"]

    # Check that resource_filename was called
    mock_resource_filename.assert_called_once_with("grpc_tools", "_proto")

    # Check that listdir was called
    mock_listdir.assert_called_once_with(grpc.proto_directory)

    # Check that protoc.main was called with the correct arguments
    mock_protoc_main.assert_called_once()
    args = mock_protoc_main.call_args[0][0]

    assert args[0] == "grpc_tools.protoc"
    assert f"-I{grpc.bt_test_interfaces_directory}" in args
    assert "-I/fake/proto/include" in args
    assert f"--python_out={grpc.build_directory}" in args
    assert f"--custom_grpc_out={grpc.build_directory}" in args

    # The .proto files should be correctly appended
    assert f"{grpc.proto_directory}/test1.proto" in args
    assert f"{grpc.proto_directory}/test2.proto" in args
    assert f"{grpc.proto_directory}/not_a_proto.txt" not in args
