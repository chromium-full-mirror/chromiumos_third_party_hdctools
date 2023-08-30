# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Helper class to facilitate communication to servo ec console during mfg."""

import servo.drv.pty_driver as pty_driver
import servo.interface.stm32uart as stm32uart


class TinyServod(object):
    """Helper class to wrap a pty_driver with interface."""

    def __init__(self, vid, pid, interface, serialname=None):
        """Build the driver and interface.

        Args:
          vid: servo device vid
          pid: servo device pid
          interface: which usb interface the servo console is on
          serialname: optional, serial if this is used in a multi device setting
        """
        self.suart = stm32uart.Suart(
            vendor=vid, product=pid, interface=interface, serialname=serialname
        )
        self.suart.run()
        # Pass a fake dictionary as params to appease the hw_driver API.
        self.pty = pty_driver.ptyDriver(self.suart, dict(cmd="get"))

    def reinitialize(self):
        """Reinitialize the connect after a reset/disconnect/etc."""
        self.suart.reinitialize()
        # Pass a fake dictionary as params to appease the hw_driver API.
        self.pty = pty_driver.ptyDriver(self.suart, dict(cmd="get"))

    def close(self):
        """Close out the connection and release resources.

        Note: if another TinyServod process or servod itself needs the same device
              it's necessary to call this to ensure the usb device is available.
        """
        self.suart.close()
