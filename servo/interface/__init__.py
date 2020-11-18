# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Entry point to build an interface given a template."""

import logging

from . import bbadc
from . import bbgpio
from . import bbi2c
from . import bbuart
from . import common as c
from . import empty
from . import ec3po_interface
from . import ftdi_common
from . import ftdigpio
from . import ftdii2c
from . import ftdiuart
from . import i2cbus
from . import interface
from . import stm32gpio
from . import stm32i2c
from . import stm32uart

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
