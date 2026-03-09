# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import json
from typing import Any, Dict

import grpc


grpc_channel: Dict[str, grpc.Channel] = {}


class GrpcClient:
    @staticmethod
    def create_grpc_channel(server: str, port: int) -> grpc.Channel:
        """
        Create grpc channel if it is not created before

        return:
            grpc_channel
        """
        global grpc_channel
        grpc_key = "{}_{}".format(server, port)
        if grpc_key in grpc_channel:
            return grpc_channel[grpc_key]

        # Define gRPC options for keepalive and retry
        # Keepalive helps detect dead connections faster.
        # Retry policy handles transient network or process issues.
        options: list[tuple[str, Any]] = [
            ("grpc.keepalive_time_ms", 10000),
            ("grpc.keepalive_timeout_ms", 5000),
            ("grpc.keepalive_permit_without_calls", True),
            ("grpc.http2.max_pings_without_data", 0),
            ("grpc.http2.min_time_between_pings_ms", 10000),
            ("grpc.max_metadata_size", 64 * 1024),
        ]

        service_config = {
            "methodConfig": [
                {
                    "name": [{}],
                    "retryPolicy": {
                        "maxAttempts": 5,
                        "initialBackoff": "0.1s",
                        "maxBackoff": "10s",
                        "backoffMultiplier": 2,
                        "retryableStatusCodes": [
                            "UNAVAILABLE",
                        ],
                    },
                }
            ]
        }
        options.append(("grpc.service_config", json.dumps(service_config)))

        grpc_channel[grpc_key] = grpc.insecure_channel(
            "{}:{}".format(server, port), options=options
        )
        return grpc_channel[grpc_key]
