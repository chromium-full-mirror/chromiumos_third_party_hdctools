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

  def __init__(self, interface, params, servod):
    """Constructor.

    Args:
      interface: hardware interface for low-level communication; ignored here
      params: dictionary of params
      servod: Servod that is used for cross-servo-device communication
    """
    super(selectControl, self).__init__(interface, params, servod)
    if not hasattr(self._servod, 'selected_controls'):
      self._servod.selected_controls = {}

  def _get(self):
    """Get the control value."""
    control_name = self._params.get('control_name', None)
    if not control_name:
      raise selectControlError('Need control_name to modify control')

    # Return the selected control
    select, control_key = self._get_control_key_info(control_name)
    if select:
      return self._servod.selected_controls.get(control_key, '')

    # Return the value from the selected control
    selected_control = self._get_selected_control(control_key)
    return self._servod_get(selected_control)

  def _get_control_key_info(self, control_name):
    """Get the base control information

    Returns:
        A tuple (True if control_name ends with '_select', The key string used
                 in the selected_controls dictionary)
    """
    select = control_name.endswith(self.SELECT_SUFFIX)
    if select:
        return (True, control_name.rsplit(self.SELECT_SUFFIX, 1)[0])
    return (False, control_name)

  def _get_selected_control(self, control_key):
    """Return the control being used."""
    selected_control = self._servod.selected_controls.get(control_key, None)
    if not selected_control:
      raise selectControlError('%r not set' % control_key)
    return selected_control

  def _set(self, logical_value):
    """Set the control to |logical_value|.

    Args:
      logical_value: Integer value to write to hardware.
    """
    control_name = self._params.get('control_name', None)
    if not control_name:
      raise selectControlError('Need control_name to modify control')

    select, control_key = self._get_control_key_info(control_name)
    if select:
      # Change the selected control
      self._logger.info('%s -> %s', control_key, logical_value)
      self._servod.selected_controls[control_key] = logical_value
      return
    # Set the value of the selected control
    selected_control = self._get_selected_control(control_key)
    self._servod_set(selected_control, logical_value)
