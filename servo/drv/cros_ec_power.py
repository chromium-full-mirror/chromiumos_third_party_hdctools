# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import time

from servo.drv import power_state
from servo.drv import polling_control

CONTROL_COMMAND = 'ec_system_powerstate'
CONTROL_OUTPUT_EXPECTED = ['S5', 'G3']

class CrosECPower(power_state.PowerStateDriver):
  """Driver for power_state for boards support EC command."""

  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: driver interface object
      params: dictionary of params
    """
    super(CrosECPower, self).__init__(interface, params)
    self._apreset_ec_command = self._params.get('apreset_ec_command', '')
    self._shutdown_ec_command = self._params.get('shutdown_ec_command',
                                                 'apshutdown')
    self._shutdown_delay = float(self._params.get('shutdown_delay', 11.0))

  def _warm_reset(self):
    """Apply warm reset to the DUT."""
    if not self._apreset_ec_command:
      # Fallback to the default sequence, which is defined in the superclass
      super(CrosECPower, self)._warm_reset()
    else:
      self._interface.set('ec_uart_regexp', 'None')
      self._interface.set('ec_uart_cmd', self._apreset_ec_command)
      # After the reset, give the EC the time it needs to
      # re-initialize.
      time.sleep(self._reset_recovery_time)

  def _power_off(self, manage_delay=True):
    """Power off the DUT."""
    self._interface.set('ec_uart_regexp', 'None')
    self._interface.set('ec_uart_cmd', self._shutdown_ec_command)

    if manage_delay:
      if not polling_control.PollingControl().poll(self._interface,
                                                   CONTROL_COMMAND,
                                                   CONTROL_OUTPUT_EXPECTED,
                                                   logger = self._logger,
                                                   polling_timeout = self._shutdown_delay):
        self._logger.warning(
          "Timeout waiting for '%s' to reach '%s' after '%f s'"
          % (CONTROL_COMMAND, CONTROL_OUTPUT_EXPECTED, self._shutdown_delay))
