# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Base interface implementing the common API."""

import logging
from typing import Any, Optional, Self, Type


class Interface:
    """Base servo interface interface."""

    def __init__(self, logger_name: Optional[str] = None) -> None:
        if logger_name is None:
            logger_name = type(self).__name__
        self._logger = logging.getLogger(logger_name)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[Any],
    ) -> None:
        self.close()

    @staticmethod
    def build(**kwargs: Any) -> Self:
        """Factory method to implement the interface."""
        raise NotImplementedError("Interfaces have to define a factory method.")

    @staticmethod
    def name() -> str:
        raise NotImplementedError(
            "Interfaces have to define a name under which they can be found."
        )

    def reinitialize(self) -> None:
        """Base reinitialization logic is a noop. Implement in child if needed."""

    def close(self) -> None:
        """Default closer is a noop if nothing has to be done."""
