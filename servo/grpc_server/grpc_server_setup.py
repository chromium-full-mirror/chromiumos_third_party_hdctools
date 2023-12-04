# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
from concurrent import futures

import grpc

from servo.common.proto import servo_dev_grpc
from servo.grpc_server.impl import servo_impl


def run_grpc_server(servod):
    """
    Start a gRPC server for the core services.
    This function sets up and starts a gRPC server to handle remote procedure calls (
    RPCs) for the core service.
    The server listens on port 50052 and uses an insecure channel for communication.

    Args:
        servod (Servod) instance used to do several operations on servod core.
    """
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    servo = servo_impl.ServoImpl(servod)
    servo_dev_grpc.add_ServoServiceServicer_to_server(servo, server)
    server.add_insecure_port("[::]:50052")
    server.start()
    print("Core Server started....")
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == "__main__":
    run_grpc_server(None)
