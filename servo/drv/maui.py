# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for board config controls of type=maui."""
import logging
import re

from servo.drv import pty_driver
from servo.drv import uart


# A firmware error is a complete line (output arrives in chunks) that is:
# - printed in red, the colour of every Zephyr shell error, or
# - one of the known messages below, for when shell colours are off.
# Log lines ("[00:00:01.234,000] <err> mod: ...") start with '[' or '<' and
# never count as errors.
_FW_ERROR_TEXT_RE = (
    r"(?:Failed to|Invalid argument|Usage:|Unknown channel"
    r"|No temperature sensor"
    r"|[^\r\n\x1b\[<][^\r\n\x1b]*"
    r"(?:not ready|command not found|wrong parameter count))"
)
_FW_ERROR_RE = (
    r"(?:^|\n)"
    r"(?:\x1b\[1;31m(?![\[<])|(?:\x1b\[[0-9;]*m)?(?=" + _FW_ERROR_TEXT_RE + r"))"
    r"(?P<maui_error>[^\r\n\x1b]+)(?=(?:\x1b\[[0-9;]*m)*[\r\n])"
)

# Line printed by the firmware once each action has been accepted. 'cycle'
# returns as soon as the cycle has started, for both power and data.
_POWER_DONE_RE = {
    "off": r"DUT Power: OFF",
    "on": r"DUT Power: ON",
    "cycle": r"DUT Power: Cycling started",
}
_DATA_DONE_RE = {
    "off": r"DUT Data: OFF",
    "on": r"DUT Data: ON",
    "cycle": r"DUT Data: Cycling started",
}


class MauiError(uart.uartError):
    """Error class for Maui class."""


class maui(uart.uart):
    """Object to access type=maui controls."""

    # Shell argument for each value of map="maui_onoffcycle".
    DUT_ONOFFCYCLE_ARGS = ["off", "on", "cycle"]

    def __init__(self, grpc_core_addr, grpc_data_addr, interface, params):
        super().__init__(grpc_core_addr, grpc_data_addr, interface, params)
        self._logger = logging.getLogger("Maui")
        self._uart_cmd = self._params.get("uart_cmd")
        self._regex = self._params.get("regex")
        self._timeout = float(self._params.get("timeout", 10.0))
        self._prompt_found = False
        self._logger.info("Maui driver in use")

    def _issue_cmd_get_results(
        self,
        cmds,
        regex_list,
        flush=None,
        timeout=pty_driver.DEFAULT_UART_TIMEOUT,
    ):
        """Send |cmds| and match |regex_list|, failing fast on firmware errors.

        Args:
          cmds: The commands issued, either a list or a string.
          regex_list: List of regular expressions to match in order. They are
            wrapped in an alternation, so they must not start with inline
            global flags such as '(?i)'.
          flush: Flag to flush the console before sending, see PtyDriver.
          timeout: Timeout value in seconds.

        Returns:
          Same as PtyDriver._issue_cmd_get_results() for |regex_list|.

        Raises:
          MauiError: if the firmware reports an error instead of the expected
            output.
        """
        # The first time we issue a command, send a CR to wake up the prompt
        if not self._prompt_found:
            self._prompt_found = True
            self._logger.debug("First command, attempting to wake up prompt...")
            try:
                super()._issue_cmd_get_results("\n\n\n", [r"maui\$ "], flush, 5)
                self._logger.debug("Found initial prompt.")
            except (uart.uartError, pty_driver.PtyError) as e:
                self._logger.warning("Error while waiting for initial prompt: %s", e)
                # Continue anyway, maybe the next command will work

        wrapped = ["(?:%s)|%s" % (regex, _FW_ERROR_RE) for regex in regex_list]
        results = super()._issue_cmd_get_results(cmds, wrapped, flush, timeout)
        return [
            self._check_result(cmds, regex, result)
            for regex, result in zip(regex_list, results)
        ]

    @staticmethod
    def _check_result(cmds, regex, result):
        """Check one match of a regex wrapped with _FW_ERROR_RE.

        Args:
          cmds: The commands issued, used for the error message.
          regex: The original (unwrapped) regular expression.
          result: The match result for the wrapped regular expression.

        Returns:
          The result in the shape |regex| alone would have produced.

        Raises:
          MauiError: if the firmware error branch matched.
        """
        ngroups = re.compile(regex).groups
        if not isinstance(result, tuple):
            # Regex without groups matched.
            return result
        if len(result) > ngroups + 1 and result[ngroups + 1]:
            raise MauiError(
                "Maui command %r failed: %s" % (cmds, result[ngroups + 1].strip())
            )
        return result[: ngroups + 1] if ngroups else result[0]

    def _run_action(self, cmd, done_re, value):
        """Run |cmd| with the off/on/cycle argument for |value|.

        Args:
          cmd: The Maui shell command, e.g. 'power_dut'.
          done_re: Dict of action -> regex printed when the action finished.
          value: 0 (off), 1 (on) or 2 (cycle), see map maui_onoffcycle.

        Raises:
          MauiError: if |value| is invalid or the firmware reports an error.
        """
        if value not in range(len(self.DUT_ONOFFCYCLE_ARGS)):
            raise MauiError("Invalid value %r: use off, on or cycle" % (value,))
        action = self.DUT_ONOFFCYCLE_ARGS[int(value)]
        self._issue_cmd_get_results(
            "%s %s" % (cmd, action), [done_re[action]], timeout=self._timeout
        )

    def _Set_dut_power(self, value):
        """Turn DUT power off/on or cycle it (map maui_onoffcycle)."""
        self._run_action("power_dut", _POWER_DONE_RE, value)

    def _Set_dut_data(self, value):
        """Turn DUT USB data off/on or cycle it (map maui_onoffcycle)."""
        self._run_action("data_dut", _DATA_DONE_RE, value)

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
