# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""A drv to raise an error whenever set or get are used."""

from servo.drv import hw_driver


# pylint: disable=invalid-name
# naming convention needed for servod driver query.
class error(hw_driver.HwDriver):
  """class to raise set or get errors."""

  def get(self):
    """raise error that |get| is not defined."""
    raise hw_driver.HwDriverError('get not defined for %r.' %
                                  self._params['control_name'])

  def set(self, _):
    """raise error that |set| is not defined."""
    raise hw_driver.HwDriverError('set not defined for %r.' %
                                  self._params['control_name'])
