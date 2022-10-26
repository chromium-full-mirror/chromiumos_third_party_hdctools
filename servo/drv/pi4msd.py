# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for board config controls pi4msd5v954 i2c multiplexer."""

from servo.drv import hw_driver
from servo.drv import i2c_reg

class Pi4MsdError(hw_driver.HwDriverError):
  """Error occurred accessing PI4MSD."""

class pi4Msd(hw_driver.HwDriver):
  """Object to access drv=pi4msd controls."""

  PI4MSD_I2C_ADDR = 0x70
  PI4MSD_EN_BIT_OFFSET = 2

  MUX_CHAN_VALID_MASK = 0x1
  MUX_CHAN_VALID_ERR_STR = '0 | 1'

  VALID_CTRL_REG_VAL = [0b101, 0b100, 0b001, 0b000]

  def __init__(self, interface, params):
    """Constructor

    Args:
      interface: FTDI interface object to handle low-level communication to
          control
      params: dictionary of params (k=v pairs) needed to perform operations on a driver.
        Notables for this class:
          mux_chan: Number of PI4MSD5V954 i2c channel to be enabled/disabled

        Additional param keys are described in HwDriver class constructor
    """

    super(pi4Msd, self).__init__(interface, params)
    self._i2c_obj = i2c_reg.I2cReg.get_device(
        self._interface, self.PI4MSD_I2C_ADDR, addr_len=1, reg_len=1, msb_first=True,
        no_read=False, use_reg_cache=False)

  def _get(self):
    """Get value of mux control register"""

    # Cannot use dedicted _read_reg since muxer has only one register and there
    # is no extra i2c transaction with register addr"""
    return self._i2c_obj._i2c.wr_rd(self.PI4MSD_I2C_ADDR, [], 1)

  def _set(self, enable, ctrl_reg=None):
    """Enable or disable i2c muxer, configure channel for particular control.

    Args:
      enable: Either enable (1) or disable (0) i2c muxer, configure channel according to
        "mux_chan" value from 'params' for particular control. This value is ignored if
        caller provides ctrl_reg.
      ctrl_reg: value to be written into i2c mux control register
        BIT0 - channel number to be selected (0 or 1)
        BIT1 - reserved
        BIT2 - enable (1) or disable (0) i2c mux
        BIT3-BIT8 - reserved
        Supported values: 0b101, 0b100, 0b001, 0b000
        Once ctrl_reg is provided by the caller, this ctrl_reg is written directly into
          i2c muxer control register (ignoring enable value). With this optional parameter
          _get() and _set() may be symmetric that is output from _get() can be fed into
          _set().
    """
    if ctrl_reg is None:
      # Interface expects ints and not booleans.
      if enable not in [0, 1]:
        raise Pi4MsdError('enable value should be 0 or 1, got: %d' % enable)
      ctrl_reg = (enable << self.PI4MSD_EN_BIT_OFFSET) | self._get_chan()

    if ctrl_reg not in self.VALID_CTRL_REG_VAL:
      raise Pi4MsdError("Incorrect value for i2c mux ctrl reg")

    self._i2c_obj._i2c.wr_rd(self.PI4MSD_I2C_ADDR,[ctrl_reg], 0)

  def _get_chan(self):
    """Check and return needed params to call driver.

    Returns:
      mux_chan: Channel (0 | 1) on the i2c mux to be enabled/disabled
    """

    if 'mux_chan' not in self._params:
      raise Pi4MsdError('"mux_chan" not found in params')

    if self._params['mux_chan'] not in ['0', '1']:
      raise Pi4MsdError('Invalid mux chan value should be %r got %r' %
                        self.MUX_CHAN_VALID_ERR_STR, self._params['mux_chan'])

    # mux_chan parameter is a string needs to convert it to int
    return int(self._params['mux_chan'], 0)
