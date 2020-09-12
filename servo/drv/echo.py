# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Echo servod driver that can be used to store constants for overlays."""

import hw_driver


class echo(hw_driver.HwDriver):
  """Driver to echo values back."""
  # pylint: disable=invalid-name
  # naming convention needed for servod driver query.

  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: driver interface object
      params: dictionary of params
    """
    # pylint: disable=invalid-name
    # Class name format needed for drv class routing in servod.
    super(echo, self).__init__(interface, params)
    self._val = self._params.get('value', 'unknown')

  def get(self):
    """Return the value."""
    return self._val
