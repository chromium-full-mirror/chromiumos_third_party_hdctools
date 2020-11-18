# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Custom power_state driver for grunt for b/167734179."""

from servo.drv import cros_ec_softrec_power


# pylint: disable=invalid-name
# This name conforms to the servod drv naming convention.
class gruntPower(cros_ec_softrec_power.crosEcSoftrecPower):
  """Driver for power_state for grunt."""

  CTRL = 'c0_ppc_pp1_en'

  def _power_on_bytype(self, *args, **kwargs):
    """We want to make sure that the issue does not arise during :rec either."""
    # |_power_on_bytype| is used inside power_state:rec to turn off the AP
    # before turning it on again to come back in recovery mode. To ensure a safe
    # turn off sequence, turn off the c0_ppc_pp1 before the function.
    self._interface.set(self.CTRL, 'off')
    # Now we can safely call the super class's |_power_on_bytype|
    super(gruntPower, self)._power_on_bytype(*args, **kwargs)

  def _power_off(self):
    """Power off DUT.

    On grunt this might be dangerous to do if servo v4 is in 'snk' mode and
    ccd is active. Thus, we need to make sure the ppc does not turn off the SBU
    lines when we enter G3.
    """
    # NOTE: the control cannot be turned off _before_ |_power_off()| because
    # the system might be booted from a usb stick, and this would remove the
    # memory.
    super(gruntPower, self)._power_off()
    if self._needs_c0_pp1():
      # Turn off the c0_ppc_pp1 right after turning off. It takes the EC ~10s to
      # transition to out G3 implementation that turns off the VBUS, and causes
      # the issue.
      self._interface.set(self.CTRL, 'off')

  def _needs_c0_pp1(self):
    """Whether grunt needs to manage the c0 ppc pp1 enable manually."""
    if self._interface._has_control('servo_v4_role'):
      if self._interface.get('servo_v4_role') == 'snk':
        self._logger.debug('Determined grunt needs to turn manage c0 ppc pp1')
        return True
    # By default, we don't need to
    return False

  def _power_on(self, rec_mode):
    """reenable the ppc on power-on if no rec-mode is requested."""
    super(gruntPower, self)._power_on(rec_mode)
    if self._needs_c0_pp1() and rec_mode == self.REC_OFF:
      # This is the vanilla 'power_state:on'
      self._interface.set(self.CTRL, 'on')

  def _reset_cycle(self):
    """Reset on grunt runs through cr50, so disable c0 ppc pp1."""
    # Turn off the c0_ppc_pp1 before resetting the EC.
    self._interface.set(self.CTRL, 'off')
    super(gruntPower, self)._reset_cycle()
    # Note that there is no need to restore the value here manually as the EC
    # will set the appropiate value (depending on the port's needs) upon
    # rebooting
