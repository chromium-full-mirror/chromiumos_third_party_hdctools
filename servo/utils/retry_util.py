# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Retry utilities for hardware communication."""

import logging
from typing import Callable, Tuple, Type, Union

import backoff
import usb.core


# Common hardware exceptions that are usually transient and worth retrying.
HARDWARE_EXCEPTIONS = (
    usb.core.USBError,
    BrokenPipeError,
    ConnectionError,
    TimeoutError,
    OSError,
)


def retry_hardware(
    exceptions: Union[
        Type[Exception], Tuple[Type[Exception], ...]
    ] = HARDWARE_EXCEPTIONS,
    max_tries: int = 3,
    max_time: int = 10,
    jitter: bool = True,
    logger_name: str = "retry_hardware",
    **kwargs
) -> Callable:
    """Decorator for retrying hardware operations with exponential backoff.

    Args:
        exceptions: Exception or tuple of exceptions to catch and retry.
        max_tries: Maximum number of attempts.
        max_time: Maximum total time in seconds to spend retrying.
        jitter: Whether to add random jitter to wait times.
        logger_name: Name of the logger to use for retry messages.

    Returns:
        Decorated function.
    """
    logger = logging.getLogger(logger_name)

    return backoff.on_exception(
        backoff.expo,
        exceptions,
        max_tries=max_tries,
        max_time=max_time,
        jitter=backoff.random_jitter if jitter else None,
        logger=logger,
        **kwargs,
    )


def retry_on_none(
    max_tries: int = 5, max_time: int = 10, logger_name: str = "retry_on_none", **kwargs
) -> Callable:
    """Decorator for retrying functions that return None on transient failure.

    Args:
        max_tries: Maximum number of attempts.
        max_time: Maximum total time in seconds to spend retrying.
        logger_name: Name of the logger to use for retry messages.

    Returns:
        Decorated function.
    """
    logger = logging.getLogger(logger_name)

    return backoff.on_predicate(
        backoff.expo,
        predicate=lambda x: x is None,
        max_tries=max_tries,
        max_time=max_time,
        logger=logger,
        **kwargs,
    )
