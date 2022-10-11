# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for board config controls stud_evb board (i2c mux & ioexes)."""

from servo.drv import hw_driver
from servo.drv import pi4msd
from servo.drv import pi4ioe5

class studEvb(hw_driver.HwDriver):

  def __init__(self, interface, params):
    """Constructor

    Args:
      interface: FTDI interface object to handle low-level communication to
          control
      params: dictionary of params (k=v pairs) needed to perform operations on a driver

    Attributes:
      i2c_mux: Pi4Msd instance to talk to on-board i2c muxer
      ioex: Pi4Ioe5 instance to talk to on-board ioexpander
    """
    super(studEvb, self).__init__(interface, params)
    self.i2c_mux = pi4msd.pi4Msd(interface, params)
    self.ioex = pi4ioe5.pi4Ioe5(interface, params)

  def _get(self):
    """Get level and flags of particular stud_evb pin

    1. Store current mux configuration
    2. Set muxer properly if necessary
    3. Send command to ioex
    4. Restore muxer settings
    """
    mux_reg = self.i2c_mux._get()
    self.i2c_mux._set(1)
    retval = self.ioex._get()
    self.i2c_mux._set(1, mux_reg)
    return retval

  def _set(self, fmt_value):
    """Set value and configure ioexpander pin

    Args:
      fmt_value: see _help_msg_for_set() within pi4ioe5.py module for description.
    """
    self.i2c_mux._set(1)
    return self.ioex._set(fmt_value)

# TODO(b/254600309): Apply pins "restrictions" according to the Stud EVB User Guide
# TODO(b/254600051): Add option to configure pins on per-bank basis
