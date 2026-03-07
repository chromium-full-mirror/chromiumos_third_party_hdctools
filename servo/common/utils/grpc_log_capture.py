# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A thread-local logging handler to capture logs during a gRPC call."""

import contextvars
import logging


# A context variable to hold the list of log records for the current
# async task / thread.
_log_capture_buffer = contextvars.ContextVar("log_capture_buffer", default=None)


class GrpcLogCaptureHandler(logging.Handler):
    """A logging handler that appends log messages to a context-local list."""

    def __init__(self, level=logging.INFO):
        super().__init__(level)
        self.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )

    def emit(self, record):
        buf = _log_capture_buffer.get()
        if buf is not None:
            msg = self.format(record)
            buf.append(msg)


class LogCaptureContext:
    """A context manager to start and stop capturing logs for current context."""

    def __init__(self, root_logger=None):
        self._root_logger = root_logger or logging.getLogger()
        self._handler = None
        self._token = None

    def __enter__(self):
        # Create a new list for this context
        buf = []
        self._token = _log_capture_buffer.set(buf)
        return buf

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._token:
            _log_capture_buffer.reset(self._token)
        return False


def setup_global_capture(level=logging.INFO):
    """Attach the capture handler to the root logger."""
    root = logging.getLogger()
    # Check if we already added it
    if not any(isinstance(h, GrpcLogCaptureHandler) for h in root.handlers):
        root.addHandler(GrpcLogCaptureHandler(level))
