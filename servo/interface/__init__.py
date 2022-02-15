# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Entry point to build an interface given a template."""

import logging

from servo.interface import bbadc
from servo.interface import bbgpio
from servo.interface import bbi2c
from servo.interface import bbuart
from servo.interface import common as c
from servo.interface import empty
from servo.interface import ec3po_interface
from servo.interface import ftdi_common
from servo.interface import ftdigpio
from servo.interface import ftdii2c
from servo.interface import ftdiuart
from servo.interface import i2cbus
from servo.interface import interface
from servo.interface import stm32gpio
from servo.interface import stm32i2c
from servo.interface import stm32uart

# Keep track of known interfaces, and map their factory function to their name.
_interfaces = [
    # Known FTDI interfaces
    ftdii2c.Fi2c,
    ftdigpio.Fgpio,
    ftdiuart.Fuart,
    # Known BB interfaces
    bbadc.BBadc,
    bbgpio.BBgpio,
    bbi2c.BBi2c,
    bbuart.BBuart,
    # Known STM32 interfaces
    stm32gpio.Sgpio,
    stm32i2c.Si2cBus,
    stm32uart.Suart,
    # Other interfaces
    ec3po_interface.EC3PO,
    i2cbus.I2CBus,
    empty.Empty
]

# Generate a look-up table for these interface names to factory method.
_interface_map = {i.name(): i.Build for i in _interfaces}

# There is one special-case where an interface is actually two interfaces, and
# they are bundled togethre. For this, there is a special builder, and a special
# name. This is for compatibility reasons and new interfaces should not follow
# this template, but rather try to have independent interfaces.
_interface_map['ftdi_gpiouart'] = ftdiuart.Fuart.BuildGPIOUart


# General factory function
def Build(name, **kwargs):
  """Build an interface |name| given the kwargs."""
  factory = _interface_map.get(name, None)
  if not factory:
    c.build_logger.error('No template class found for interface named %s', name)
    raise c.InterfaceError('Unknown interface: %s' % name)
  return factory(**kwargs)
