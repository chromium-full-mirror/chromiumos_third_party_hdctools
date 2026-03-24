# Copyright 2018 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Driver to execute some control commands directly on ftdii2c.

See ftdii2c.py for details on controls available.
"""
from servo.common.exceptions import HwDriverError
from servo.common.grpc_client import GrpcClient
from servo.common.interface import ftdii2c
from servo.common.proto import driver_grpc
from servo.drv.hw_driver import HwDriver


# pylint: disable=C0103
class ftdii2cCmdError(HwDriverError):
    """Exception class for ftdii2c_cmd."""


class ftdii2cCmd(HwDriver):
    """Object to access drv=ftdii2c_cmd controls.

    Attributes:
      _ftdii2c: ftdi i2c object to execute commands on

    """

    def _drv_init(self):
        """Driver specific initializer."""
        # pylint: disable=protected-access
        super()._drv_init()
        # Create a gRPC channel to the specified host and port
        grpc_data_host, grpc_data_port = self.grpc_data_addr
        channel = GrpcClient.create_grpc_channel(grpc_data_host, grpc_data_port)
        self._data_client = driver_grpc.DriverService(channel)

    def _set(self, cmd):
        """Execute |cmd| on |self._ftdii2c| object.

        Args:
          cmd: str representing the ftdi i2c command to execute
        """
        self._data_client.SetFtdii2cCmd(cmd=cmd)

    def _get(self):
        """Raise error as a command needs to be specified."""
        raise ftdii2cCmdError("No cmd specified for ftdii2c_cmd")
