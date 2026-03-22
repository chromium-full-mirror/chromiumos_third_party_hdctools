# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Validates a servod OTA payload by pinging the data gRPC server."""

import argparse
import logging
import sys

import grpc

from servo.common.proto import system_config_grpc
from servo.common.proto import system_config_pb2


def main():
    parser = argparse.ArgumentParser(description="Validate servod OTA payload.")
    parser.add_argument(
        "--port", type=int, required=True, help="Port of the canary data gRPC server."
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    channel = grpc.insecure_channel(f"localhost:{args.port}")
    stub = system_config_grpc.SystemConfigStub(channel)

    try:
        # Perform a simple RPC call to ensure the server is alive and functioning.
        # Calling GetAvailableModels with a fake board is safe and side-effect free.
        request = system_config_pb2.AvailableModelsRequest(board="brya")
        stub.GetAvailableModels(request, timeout=5)
        logging.info("Successfully validated OTA payload on port %d.", args.port)
        sys.exit(0)
    except grpc.RpcError as e:
        logging.error("Failed to validate OTA payload: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
