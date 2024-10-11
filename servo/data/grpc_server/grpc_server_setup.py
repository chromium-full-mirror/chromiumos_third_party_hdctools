# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


from concurrent import futures
import logging
import sys
import time

import grpc

from servo.common.proto import driver_grpc
from servo.common.proto import system_config_grpc
from servo.data.impl import driver_impl
from servo.data.impl import system_config_impl


DEBUG_FMT_STRING = (
    "%(asctime)s - %(name)s - %(levelname)s - "
    "%(filename)s:%(lineno)d:%(funcName)s - %(message)s"
)

def grpc_server_start():
    """
    Start a gRPC server for the data services.
    This function sets up and starts a gRPC server to handle remote procedure calls (
    RPCs) for the data service.
    The server listens on port 50051 and uses an insecure channel for communication.
    """
    logging.basicConfig(level=logging.INFO, format=DEBUG_FMT_STRING)

    # Create a gRPC server with a thread pool executor allowing up to 10 concurrent
    # workers
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    # Add the SystemConfigServicer implementation to the gRPC server
    system_config_grpc.add_SystemConfigServicer_to_server(
        system_config_impl.SystemConfigImpl(), server)

    # Add the DriverServicer implementation to the gRPC server
    driver_grpc.add_DriverServiceServicer_to_server(
        driver_impl.DriverImpl(), server)

    # Bind the server on port 50051
    server.add_insecure_port("[::]:50051")

    # Start the gRPC server
    server.start()

    # Print a message to indicate that the server has started
    print("Server started")

    try:
        while True:
            time.sleep(86400)  # Sleep indefinitely (to keep the server running)
    except KeyboardInterrupt:
        # Gracefully stop the server when a keyboard interrupt (Ctrl+C) is received
        server.stop(0)
        sys.exit(1)


if __name__ == "__main__":
    grpc_server_start()
