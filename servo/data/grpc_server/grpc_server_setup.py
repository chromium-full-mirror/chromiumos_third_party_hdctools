# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


import argparse
from concurrent import futures
import logging
import sys
import time

import grpc

from servo.common.proto import driver_grpc
from servo.common.proto import system_config_grpc
from servo.common.utils import servo_logging
from servo.common.utils.grpc_log_capture import setup_global_capture
from servo.data.impl import driver_impl
from servo.data.impl import system_config_impl


# If user does not specify a log directory, use this one.
DEFAULT_LOG_DIR = "/var/log"


def serve():
    """
    Start a gRPC server for the data services.
    This function sets up and starts a gRPC server to handle remote procedure calls (
    RPCs) for the data service.
    The server listens on port 50051 and uses an insecure channel for communication.
    """
    default_handler = logging.StreamHandler()
    default_handler.setLevel(logging.INFO)
    default_handler.formatter = servo_logging.ShortUTCFormatter(
        fmt=servo_logging.SHORT_DEBUG_FMT_STRING
    )
    logging.basicConfig(level=logging.INFO, handlers=[default_handler])

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--grpc-core-host",
        type=str,
        required=True,
        help="gRPC Core service host to connect to",
    )
    parser.add_argument(
        "--grpc-core-port",
        type=int,
        required=True,
        help="gRPC Core service port to connect to",
    )
    parser.add_argument(
        "--grpc-data-port",
        type=int,
        required=True,
        help="gRPC port that Data service will listen on",
    )
    parser.add_argument(
        "--logs",
        type=str,
        help="Directory where logs will be stored",
        dest="logs_dir",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Turn on debug logging for stderr",
    )

    args = parser.parse_args()

    logs_dir = args.logs_dir
    if logs_dir is None:
        port_str = str(args.grpc_data_port)
        base_port = port_str[1:] if port_str.startswith("2") else port_str
        logs_dir = f"{DEFAULT_LOG_DIR}/servod_{base_port}"

    servo_logging.setup(
        logdir=logs_dir,
        module="data",
        port=args.grpc_data_port,
        debug_stderr=args.debug,
        backup_count=1,
    )
    setup_global_capture()

    # Create a gRPC server with a thread pool executor allowing up to 10 concurrent
    # workers
    options = [
        ("grpc.keepalive_permit_without_calls", True),
        ("grpc.http2.min_recv_ping_interval_without_data_ms", 5000),
        ("grpc.http2.max_ping_strikes", 0),
        ("grpc.max_metadata_size", 64 * 1024),
    ]
    from servo.common import grpc_server_interceptor

    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=options,
        interceptors=(grpc_server_interceptor.ExceptionTruncatingInterceptor(),),
    )

    # Add the SystemConfigServicer implementation to the gRPC server
    system_config_grpc.add_SystemConfigServicer_to_server(
        system_config_impl.SystemConfigImpl(), server
    )

    # Add the DriverServicer implementation to the gRPC server
    grpc_core = (args.grpc_core_host, args.grpc_core_port)
    grpc_data = ("localhost", args.grpc_data_port)
    service = driver_impl.DriverImpl(grpc_core, grpc_data)
    driver_grpc.add_DriverServiceServicer_to_server(service, server)

    # Bind the server on port 50051
    server.add_insecure_port("0.0.0.0:{}".format(args.grpc_data_port))

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
    serve()
