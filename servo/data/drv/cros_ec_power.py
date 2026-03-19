# Copyright 2014 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import contextlib
import time

from servo.data.drv import polling_control
from servo.data.drv import power_state


CONTROL_COMMAND = "ec_system_powerstate"
CONTROL_OUTPUT_EXPECTED = ["S5", "AP_POWER_STATE_S5", "G3", "AP_POWER_STATE_G3"]
POWER_OFF_POLLING_INTERVAL_S = 0.5


class CrosECPower(power_state.PowerStateDriver):
    """Driver for power_state for boards support EC command."""

    def _drv_init(self):
        """Driver specific initializer."""
        super()._drv_init()
        self._apreset_ec_commands = self._params.get("apreset_ec_commands", "")
        self._shutdown_ec_commands = self._params.get(
            "shutdown_ec_commands", "apshutdown"
        )
        self._shutdown_delay = float(self._params.get("shutdown_delay", 11.0))
        self._pd_reset_delay = float(self._params.get("pd_reset_delay", 8.0))
        self._no_battery = "yes" == self._params.get("no_battery", "no")

    @contextlib.contextmanager
    def quiet_console(self):
        """Temporarily mutes the EC console output to prevent background chatter."""
        self._logger.debug("Muting EC console channels.")
        self._driver_client.IssueCmdGetResult(
            cmds=["chan save", "chan 0"],
            regex_list=[],
            flush=False,
            time_out=0,
        )
        # Give in-flight output time to flush (equivalent to 'waitms 999').
        # 1.0 second is chosen to generously accommodate worst-case UART buffer flushing
        # delays. The risk is that if the EC takes longer than 1.0s to process the
        # command and actually flush its output, subsequent commands might read truncated
        # or overlapping output from the buffer.
        time.sleep(1.0)
        try:
            yield
        finally:
            self._logger.debug("Restoring EC console channels.")
            self._driver_client.IssueCmdGetResult(
                cmds="chan restore",
                regex_list=[],
                flush=False,
                time_out=0,
            )

    def _warm_reset(self):
        """Apply warm reset to the DUT."""
        if not self._apreset_ec_commands:
            # Fallback to the default sequence, which is defined in the superclass
            super()._warm_reset()
        else:
            self._servod_set("ec_uart_regexp", "None")
            self._servod_set("ec_uart_multicmd", self._apreset_ec_commands)
            # After the reset, give the EC the time it needs to
            # re-initialize.
            time.sleep(self._reset_recovery_time)

    def _power_off(self, manage_delay=True):
        """Power off the DUT."""
        self._servod_set("ec_uart_regexp", "None")
        self._servod_set("ec_uart_multicmd", self._shutdown_ec_commands)

        if manage_delay:
            if not polling_control.PollingControl().poll(
                self,
                CONTROL_COMMAND,
                CONTROL_OUTPUT_EXPECTED,
                logger=self._logger,
                polling_interval=POWER_OFF_POLLING_INTERVAL_S,
                polling_timeout=self._shutdown_delay,
            ):
                self._logger.warning(
                    "Timeout waiting for '%s' to reach '%s' after '%f s'"
                    % (CONTROL_COMMAND, CONTROL_OUTPUT_EXPECTED, self._shutdown_delay)
                )
        # When shutdown in recovery mode, EC will sysjump from RO to RW. If the
        # device is without battery and powered by USB-C adapter, e.g. Chromebox,
        # EC will brown out and reset due to PD hard reset. In this case we need
        # to give the EC the time it needs to re-initialize everything before
        # return.
        if self._no_battery:
            time.sleep(self._pd_reset_delay)
