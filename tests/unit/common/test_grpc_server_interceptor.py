# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from unittest.mock import MagicMock
from unittest.mock import patch

import grpc
import pytest

from servo.common import grpc_server_interceptor
from servo.common.exceptions import HwDriverError
from servo.drv.pty_driver import PtyError


class TestExceptionTruncatingInterceptor:
    @pytest.fixture
    def interceptor(self):
        return grpc_server_interceptor.ExceptionTruncatingInterceptor()

    @pytest.fixture
    def mock_context(self):
        context = MagicMock(spec=grpc.ServicerContext)
        context.abort.side_effect = grpc.RpcError("Aborted")
        return context

    def test_intercept_unary_unary_success(self, interceptor, mock_context):
        mock_handler = MagicMock()
        mock_handler.request_streaming = False
        mock_handler.response_streaming = False
        mock_handler.unary_unary.return_value = "success"

        continuation = MagicMock(return_value=mock_handler)
        handler_call_details = MagicMock()

        intercepted_handler = interceptor.intercept_service(
            continuation, handler_call_details
        )

        assert intercepted_handler is not None

        # Call the wrapper
        res = intercepted_handler.unary_unary("request", mock_context)
        assert res == "success"
        mock_handler.unary_unary.assert_called_once_with("request", mock_context)

    @patch("servo.common.grpc_server_interceptor.logging.error")
    def test_intercept_unary_unary_hw_driver_error(
        self, mock_log_error, interceptor, mock_context
    ):
        # Test with a known HwDriverError
        mock_handler = MagicMock()
        mock_handler.request_streaming = False
        mock_handler.response_streaming = False

        # Simulate driver raising HwDriverError
        mock_handler.unary_unary.side_effect = HwDriverError("Hardware failed")

        continuation = MagicMock(return_value=mock_handler)
        handler_call_details = MagicMock()

        intercepted_handler = interceptor.intercept_service(
            continuation, handler_call_details
        )

        with pytest.raises(grpc.RpcError):
            intercepted_handler.unary_unary("request", mock_context)

        # Verify context.abort was called
        mock_context.abort.assert_called_once()
        args = mock_context.abort.call_args[0]
        assert args[0] == grpc.StatusCode.UNKNOWN
        # Details should contain the error message but NOT the traceback
        assert "Hardware failed" in args[1]
        assert "Traceback" not in args[1]

        # Verify it was logged
        mock_log_error.assert_called_once()
        assert "Hardware failed" in mock_log_error.call_args[0][0]
        assert "Traceback" not in mock_log_error.call_args[0][0]

    @patch("servo.common.grpc_server_interceptor.logging.error")
    def test_intercept_unary_unary_wrapped_pty_error(
        self, mock_log_error, interceptor, mock_context
    ):
        # Test with a PtyError wrapped in another exception (like DriverImplError)
        mock_handler = MagicMock()
        mock_handler.request_streaming = False
        mock_handler.response_streaming = False

        # Simulate what driver_impl.py does: catch PtyError and raise DriverImplError from it
        try:
            try:
                raise PtyError("PTY timeout")
            except PtyError as e:
                from servo.data.impl.driver_impl import DriverImplError

                raise DriverImplError("Failed to call driver") from e
        except Exception as chained_exception:
            mock_handler.unary_unary.side_effect = chained_exception

        continuation = MagicMock(return_value=mock_handler)
        handler_call_details = MagicMock()

        intercepted_handler = interceptor.intercept_service(
            continuation, handler_call_details
        )

        with pytest.raises(grpc.RpcError):
            intercepted_handler.unary_unary("request", mock_context)

        mock_context.abort.assert_called_once()
        args = mock_context.abort.call_args[0]
        assert args[0] == grpc.StatusCode.UNKNOWN
        # Details should contain the error message but NOT the traceback
        assert "Failed to call driver" in args[1]
        assert "Traceback" not in args[1]

        mock_log_error.assert_called_once()
        assert "Failed to call driver" in mock_log_error.call_args[0][0]
        assert "Traceback" not in mock_log_error.call_args[0][0]

    @patch("servo.common.grpc_server_interceptor.logging.error")
    @patch("servo.common.grpc_server_interceptor.traceback.format_exc")
    def test_intercept_unary_unary_unexpected_error(
        self, mock_format_exc, mock_log_error, interceptor, mock_context
    ):
        # Test with an unexpected exception (e.g. ValueError) which should have traceback
        mock_handler = MagicMock()
        mock_handler.request_streaming = False
        mock_handler.response_streaming = False
        mock_handler.unary_unary.side_effect = ValueError("Unexpected value")
        mock_format_exc.return_value = "Fake Traceback\n  File ..."

        continuation = MagicMock(return_value=mock_handler)
        handler_call_details = MagicMock()

        intercepted_handler = interceptor.intercept_service(
            continuation, handler_call_details
        )

        with pytest.raises(grpc.RpcError):
            intercepted_handler.unary_unary("request", mock_context)

        mock_context.abort.assert_called_once()
        args = mock_context.abort.call_args[0]
        assert args[0] == grpc.StatusCode.UNKNOWN
        # Details SHOULD contain the traceback
        assert "Unexpected value" in args[1]
        assert "Traceback" in args[1]
        assert "Fake Traceback" in args[1]

        mock_log_error.assert_called_once()
        assert "Unexpected value" in mock_log_error.call_args[0][0]
        assert "Traceback" in mock_log_error.call_args[0][0]
