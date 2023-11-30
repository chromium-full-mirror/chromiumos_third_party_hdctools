# Copyright 2018 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Driver to execute some control commands directly on ftdii2c.

See ftdii2c.py for details on controls available.
"""

from servo.data.drv import hw_driver
from servo.interface import ftdii2c


# pylint: disable=C0103
class ftdii2cCmdError(hw_driver.HwDriverError):
    """Exception class for ftdii2c_cmd."""


class ftdii2cCmd(hw_driver.HwDriver):
    """Object to access drv=ftdii2c_cmd controls.

    Attributes:
      _ftdii2c: ftdi i2c object to execute commands on

    """

    def _drv_init(self):
        """Driver specific initializer."""
        # pylint: disable=protected-access
        super(ftdii2cCmd, self)._drv_init()

        for _unused, interface in servod.get_interface_list():
            if isinstance(interface, ftdii2c.Fi2c):
                self._ftdii2c = interface
                break
        else:
            raise ftdii2cCmdError("No ftdi_i2c object found.")

    def _set(self, cmd):
        """Execute |cmd| on |self._ftdii2c| object.

        Args:
          cmd: str representing the ftdi i2c command to execute
        """
        try:
            func = getattr(self._ftdii2c, cmd)
        except AttributeError:
            raise ftdii2cCmdError("ftdi_i2c object does not have method %r" % cmd)
        self._logger.debug("Running %s on ftdii2c interface.", cmd)
        func()

    def _get(self):
        """Raise error as a command needs to be specified."""
        raise ftdii2cCmdError("No cmd specified for ftdii2c_cmd")
