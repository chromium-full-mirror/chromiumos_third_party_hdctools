# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver to talk to the i2c channels through the DUT EC console."""

import ec


# pylint: disable=invalid-name
# This conforms to the servod error naming pattern.
class ecI2cPinError(ec.ecError):
  """Exception class for ec i2c pin."""


# pylint: disable=invalid-name
# This conforms to the servod drv naming convention.
class ecI2cPin(ec.ec):
  """Class to handle communication with the EC console."""

  # 'i2cxfer %s[w|r] %d[bus] 0x%x[addr] 0x%x'[offset]
  BASE_CMD = 'i2cxfer %s %d 0x%x 0x%x'

  REGEX = r'(0x[0-9a-f]+) \[\d+\][\n\r]'

  REQUIRED_ARGS = ['bus', 'addr', 'offset', 'mask']

  def __init__(self, interface, params):
    """Setup the commands."""
    super(ecI2cPin, self).__init__(interface, params)
    # Set the valid input choices for this driver. Choices need to be set
    # to be strings.
    self._choices = {'0', '1'}
    for a in self.REQUIRED_ARGS:
      if a not in self._params:
        raise ecI2cPinError('Required argument %s not in params' % a)
    self._mask = int(self._params['mask'], 0)
    self._logger.debug('Mask %d' % self._mask)
    if bin(self._mask).count('1') != 1:
      # We want a binary mask.
      raise ecI2cPinError('Mask 0x%x covers does not mask only one bit'
                          % self._mask)
    bus = int(self._params['bus'])
    addr = int(self._params['addr'], 0)
    offset = int(self._params['offset'], 0)
    self._read = self.BASE_CMD % ('r', bus, addr, offset)
    self._write_base = self.BASE_CMD % ('w', bus, addr, offset)

  def _set(self, value):
    """Set the bit to tbe |value|."""
    # register value
    rv = self._raw_read()
    if value:
      rv |= self._mask
    else:
      rv &= ~self._mask
    # actually need to write the value.
    write_cmd = '%s 0x%x' % (self._write_base, rv)
    # Simply wait until the writing is finished.
    self._issue_cmd_get_results(write_cmd, ['>'])

  def _raw_read(self):
    """Read the raw hex value out for the whole offset."""
    # TODO(coconutruben): unify this with |_Get_output| in the ec.
    self._limit_channel()
    result = self._issue_cmd_get_results(self._read, [self.REGEX])
    self._restore_channel()
    if result is None:
      raise ecI2cPinError('Failed to read out the i2c register value')
    val_str = result[0][1]
    val = int(val_str, 16)
    return val

  def get(self):
    """Read out the value."""
    # Cast through bool to make it binary (it's set or it's not), and then
    # through int to return a proper int as required by the servod code.
    return int(bool(self._raw_read() & self._mask))
