# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import grpc


grpc_channel = {}


class GrpcClient:
    @staticmethod
    def create_grpc_channel(server, port):
        """
        Create grpc channel if it is not created before

        return:
            grpc_channel
        """
        global grpc_channel
        grpc_key = "{}_{}".format(server, port)
        if grpc_key in grpc_channel:
            return grpc_channel[grpc_key]
        grpc_channel[grpc_key] = grpc.insecure_channel("{}:{}".format(server, port))
        return grpc_channel[grpc_key]
