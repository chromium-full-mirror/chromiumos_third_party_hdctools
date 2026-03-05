# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import os
import unittest.mock

from servo import grpc


@unittest.mock.patch("servo.grpc.protoc.main")
@unittest.mock.patch("grpc_tools.__file__", "/fake/grpc_tools/__init__.py")
@unittest.mock.patch("servo.grpc.os.listdir")
@unittest.mock.patch.dict(os.environ, {"PATH": "/usr/bin"}, clear=True)
def test_build(mock_listdir, mock_protoc_main):
    # Compute the expected directories based on the servo package location
    expected_build_dir = os.path.dirname(os.path.realpath(grpc.__file__))
    expected_proto_dir = os.path.join(expected_build_dir, "common", "proto")

    # Setup mocks
    mock_listdir.return_value = ["test1.proto", "test2.proto", "not_a_proto.txt"]

    # Call build
    grpc.build()

    # Check that the environment variable PATH was updated properly
    assert "/usr/bin" in os.environ["PATH"]
    assert expected_build_dir in os.environ["PATH"]

    # Check that listdir was called
    mock_listdir.assert_called_once_with(expected_proto_dir)

    # Check that protoc.main was called with the correct arguments
    mock_protoc_main.assert_called_once()
    args = mock_protoc_main.call_args[0][0]

    assert args[0] == "grpc_tools.protoc"
    assert f"-I{expected_build_dir}" in args
    assert "-I/fake/grpc_tools/_proto" in args
    assert f"--python_out={expected_build_dir}" in args
    assert f"--custom_grpc_out={expected_build_dir}" in args

    # The .proto files should be correctly appended
    assert os.path.join(expected_proto_dir, "test1.proto") in args
    assert os.path.join(expected_proto_dir, "test2.proto") in args
    assert os.path.join(expected_proto_dir, "not_a_proto.txt") not in args
