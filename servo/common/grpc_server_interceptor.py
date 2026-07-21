# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import traceback

import grpc

from servo.common.exceptions import HwDriverError


def _is_hw_driver_error(exc):
    """Check if the exception or any exception in its cause chain is HwDriverError."""
    curr = exc
    seen = set()
    while curr is not None and curr not in seen:
        seen.add(curr)
        if isinstance(curr, HwDriverError):
            return True
        curr = getattr(curr, "__cause__", None) or getattr(curr, "__context__", None)
    return False


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
                if _is_hw_driver_error(e):
                    # For known errors, we don't need the full traceback.
                    details_msg = "Exception calling application: %s" % str(e)
                    logging.error(details_msg)
                else:
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
