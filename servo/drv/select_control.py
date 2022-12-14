# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from servo.drv import hw_driver


class selectControlError(Exception):
  """Exception class for selectControl."""

class selectControl(hw_driver.HwDriver):
  """Add support for choosing which control to use.

  There may be multiple ways to control the dut. Add a driver to select which
  control to use. This may be used to select between using a servo hardware
  signal and a ccd signal. Different tests may need to verify ccd control or
  hardware control.

  To use this create a control CONTROL_NAME_select. Use that to select the
  control uses to get/set CONTROL_NAME.
  ex setting cold_reset_select to ec_reset will make servo use ec_reset to
  get/set the cold_reset value.
  """

  SELECT_SUFFIX = '_select'

  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: driver interface object
      params: dictionary of params
    """
    # Maps don't translate correctly when the selected control changes. Ignore
    # the maps. servo.get(selected_control) will handle the mapping.
    if 'map' in params:
        del params['map']
    super(selectControl, self).__init__(interface, params)
    if not hasattr(self._interface, 'selected_controls'):
      self._interface.selected_controls = {}

  def _Set_select(self, val):
    """Set the control to use."""
    if not val:
        return
    control_key = self._get_control_key()
    self._logger.info('%s -> %s', control_key, val)
    self._interface.selected_controls[control_key] = self._prefix + val

  def _Get_select(self):
    """Get the control value."""
    control_key = self._get_control_key()
    if control_key not in self._interface.selected_controls:
      self._Set_select(self._params['init'])
    rv = self._interface.selected_controls.get(control_key, '')
    if rv:
      self._logger.info('using %r for %r', rv, control_key)
    return rv

  def _Get_control(self):
    """Get the value from the selected control."""
    selected_control = self._get_selected_control()
    return self._interface.get(selected_control)

  def _Set_control(self, value):
    """Set the selected control to value."""
    selected_control = self._get_selected_control()
    return self._interface.set(selected_control, value)

  def _get_control_key(self):
    """Get the base control name."""
    control_name = self._params.get('control_name', '')
    if not control_name:
      raise selectControlError('control_name not found')
    return control_name.partition(self.SELECT_SUFFIX)[0]

  def _get_selected_control(self):
    """Return the control being used."""
    control_name = self._params.get('control_name', '')
    return self._interface.get(control_name + self.SELECT_SUFFIX)
