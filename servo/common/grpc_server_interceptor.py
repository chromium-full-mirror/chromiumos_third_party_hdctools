# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import traceback

import grpc


class ExceptionTruncatingInterceptor(grpc.ServerInterceptor):
    def intercept_service(self, continuation, handler_call_details):
        handler = continuation(handler_call_details)
        if handler is None:
            return handler

        if getattr(handler, "request_streaming", False) or getattr(
            handler, "response_streaming", False
        ):
            return handler

        def wrapper(request, context):
            try:
                return handler.unary_unary(request, context)
            except Exception as e:
                error_msg = traceback.format_exc()
                if len(error_msg) > 4000:
                    error_msg = error_msg[:4000] + "... [truncated traceback]"

                # Prepend the known prefix `Exception calling application: ` so that
                # servo_server.py's get/set handlers successfully slice it off and
                # raise the underlying error message cleanly to the caller.
                details_msg = (
                    "Exception calling application: "
                    + str(e)[:200]
                    + "\nTraceback:\n"
                    + error_msg
                )
                logging.error(details_msg)
                context.abort(grpc.StatusCode.UNKNOWN, details_msg)

        return grpc.unary_unary_rpc_method_handler(
            wrapper,
            request_deserializer=handler.request_deserializer,
            response_serializer=handler.response_serializer,
        )
