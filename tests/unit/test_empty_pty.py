# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest

from servo.common.interface.empty import Empty
from servo.drv.pty_driver import PtyDriver
from servo.drv.pty_driver import ptyDriverError
from servo.drv.uart import uart


class TestEmptyPty(unittest.TestCase):
    """Test the behavior of UART/PTY drivers when the interface is missing."""

    def test_uart_empty_interface(self):
        """Verify uart.get_pty returns an empty string for Empty interface."""
        # Simulate the Fission data service failing to initialize a physical
        # UART interface which replaces it with an Empty() object.
        mock_interface = Empty()

        # Initialize the UART driver with a fake cmd param to satisfy hw_driver.
        driver = uart(None, None, mock_interface, {"cmd": "get", "subtype": "pty"})

        # get() should gracefully return an empty string instead of
        # throwing AttributeError
        self.assertEqual(driver.get(), "")

    def test_pty_driver_empty_interface(self):
        """Verify PtyDriver._open raises error when PTY path is empty."""
        mock_interface = Empty()
        # Initialize with a fake cmd param to satisfy hw_driver.
        driver = PtyDriver(None, None, mock_interface, {"cmd": "get", "subtype": "pty"})

        # When trying to send a command, _open() should raise a ptyDriverError
        # instead of attempting to open an empty string and crashing with
        # FileNotFoundError.
        with self.assertRaisesRegex(
            ptyDriverError, "Cannot open PTY: No PTY path available"
        ):
            driver._issue_cmd("test")


if __name__ == "__main__":
    unittest.main()
