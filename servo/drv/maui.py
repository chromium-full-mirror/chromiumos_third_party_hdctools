# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for board config controls of type=maui."""
import logging

from servo.drv import pty_driver
from servo.drv import uart


class MauiError(uart.uartError):
    """Error class for Maui class."""


class maui(uart.uart):
    """Object to access type=maui controls."""

    def __init__(self, grpc_core_addr, grpc_data_addr, interface, params):
        super().__init__(grpc_core_addr, grpc_data_addr, interface, params)
        self._logger = logging.getLogger("Maui")
        self._uart_cmd = self._params.get("uart_cmd")
        self._regex = self._params.get("regex")
        self._timeout = float(self._params.get("timeout", 10.0))
        self._prompt_found = False
        self._logger.info("Maui driver in use")

    def _issue_cmd_get_results(self, cmds, regex_list, timeout=None):
        # The first time we issue a command, send a CR to wake up the prompt
        if not self._prompt_found:
            self._prompt_found = True
            self._logger.debug("First command, attempting to wake up prompt...")
            try:
                super()._issue_cmd_get_results("\n\n\n", [r"maui\$ "], timeout=5)
                self._logger.debug("Found initial prompt.")
            except (uart.uartError, pty_driver.PtyError) as e:
                self._logger.warning(f"Error while waiting for initial prompt: {e}")
                # Continue anyway, maybe the next command will work

        return super()._issue_cmd_get_results(cmds, regex_list, timeout=timeout)

    def _Get_text(self):
        """Get text from the device."""
        if not self._uart_cmd:
            raise MauiError("uart_cmd not defined in params")
        if not self._regex:
            raise MauiError("regex not defined in params")

        results = self._issue_cmd_get_results(
            self._uart_cmd, [self._regex], timeout=self._timeout
        )
        group = int(self._params.get("group", 0))
        return results[0][group] if isinstance(results[0], tuple) else results[0]
