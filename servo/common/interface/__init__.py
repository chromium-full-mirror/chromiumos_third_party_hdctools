# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Entry point to build an interface given a template."""

import logging

from servo.common.interface import common as c
from servo.common.interface import ec3po_interface
from servo.common.interface import empty
from servo.common.interface import ftdi_common
from servo.common.interface import ftdii2c
from servo.common.interface import ftdiuart
from servo.common.interface import i2cbus
from servo.common.interface import interface
from servo.common.interface import stm32gpio
from servo.common.interface import stm32i2c
from servo.common.interface import stm32uart


# Keep track of known interfaces, and map their factory function to their name.
_interfaces = [
    # Known FTDI interfaces
    ftdii2c.Fi2c,
    ftdiuart.Fuart,
    # Known STM32 interfaces
    stm32gpio.Sgpio,
    stm32i2c.Si2cBus,
    stm32uart.Suart,
    # Other interfaces
    ec3po_interface.EC3PO,
    i2cbus.I2CBus,
    empty.Empty,
]

# Generate a look-up table for these interface names to factory method.
_interface_map = {i.name(): i.build for i in _interfaces}


# General factory function
def build(name, **kwargs):
    """build an interface |name| given the kwargs."""
    factory = _interface_map.get(name, None)
    if not factory:
        c.build_logger.error("No template class found for interface named %s", name)
        raise c.InterfaceError("Unknown interface: %s" % name)
    return factory(**kwargs)
