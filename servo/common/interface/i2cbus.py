# Copyright 2014 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Accesses I2C buses through Linux i2c-dev driver."""

import fcntl
import io
from typing import Any, List, Optional

from servo.common.interface import i2c_base


class I2CBus(i2c_base.BaseI2CBus):
    """I2C bus class to access devices on the bus.

    Usage:
      bus = I2CBus('/dev/i2c-0')
      # read 1 byte from child(0x48) register(0x16)
      bus.wr_rd(0x48, [0x16], 1)
      # write 2 bytes to child(0x48) register(0x20)
      bus.wr_rd(0x48, [0x20, 0x01, 0x02])
    """

    _I2C_WORKER_FORCE = 0x0706

    def __init__(self, interface: str) -> None:
        i2c_base.BaseI2CBus.__init__(self)
        self._interface_path = interface
        self._interface = io.open(self._interface_path, mode="r+b", buffering=0)

    def close(self) -> None:
        """Closes the I2C bus file."""
        if self._interface:
            self._interface.close()
            self._interface = None
        super().close()

    def __del__(self) -> None:
        self.close()

    @staticmethod
    def build(interface_data: Any, **_kwargs: Any) -> "I2CBus":
        """Factory method to implement the interface."""
        return I2CBus("/dev/i2c-%d" % interface_data["bus_num"])

    @staticmethod
    def name() -> str:
        """Name to request interface by in interface config maps."""
        return "dev_i2c"

    def _raw_wr_rd(
        self,
        child_address: int,
        write_list: Optional[List[int]],
        read_count: Optional[int] = None,
        auto_release: bool = True,
    ) -> Optional[List[int]]:
        """Implements hdctools wr_rd() interface.

        This function writes byte values list to I2C device, then reads
        byte values from the same device.

        Args:
          child_address: 7 bit I2C child address.
          write_list: list of output byte values [0~255].
          read_count: number of byte values to read from device.
          auto_release: Ignored for compatibility with Si2cBus.
        """
        del auto_release
        fcntl.ioctl(self._interface.fileno(), self._I2C_WORKER_FORCE, child_address)
        if write_list:
            output_buf = bytes(write_list)
            self._interface.write(output_buf)
        if read_count:
            return list(bytearray(self._interface.read(read_count)))
        return None
