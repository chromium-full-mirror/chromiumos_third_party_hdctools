# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver to control relay switch."""

import time

import serial
from serial.tools import list_ports

from servo.drv import hw_driver


class RelaySwitchError(hw_driver.HwDriverError):
    """Error class for RelaySwitch errors."""


class relaySwitch(hw_driver.HwDriver):
    """Driver for Relay Switch that controls the DUT power button.

    This driver can only control relay switches the Servo Host sees.
    The uServo port always faces the Servo Host.
    The other USB ports might be muxed to the DUT or Servo Host.
    """

    def _drv_init(self):
        """Driver specific initializer."""
        super()._drv_init()

    def _Get_relay_serial_port(self):
        """Returns the url of the serial port connected to the relay (/dev/ttyUSB0).

        Returns:
                Either url of serial port or None if nothing is found
        """
        for port in list_ports.comports():
            # check if port is associated with:
            # ID 1a86:7523 QinHeng Electronics HL-340 USB-Serial adapter
            # https://www.amazon.com/dp/B01CN7E0RQ
            if port.vid == 0x1A86 and port.pid == 0x7523:
                return port.device
        return None

    def _Set_relay_pwrbtn_press(self, press_secs, num_attempts=6):
        """Hold down power button for [press_secs] seconds.

        This function results in the relay switch being turned on.

        Args:
          press_secs: a numerical value representing how long the relay switch
            should be activated for
          num_attempts: the max number of attempts to find the relay switch

        Raises:
          RelaySwitchError: if relay switch is not found
        """
        delay_btwn_attempts = 0.5  # arbitrarily chosen number that seems right

        # Check if relay switch is connected, and get its port
        serial_port = self._Get_relay_serial_port()
        num_attempts -= 1
        while serial_port is None:
            if num_attempts <= 0:
                raise RelaySwitchError("Unable to find relay switch")
            time.sleep(delay_btwn_attempts)
            serial_port = self._Get_relay_serial_port()
            num_attempts -= 1

        ser = serial.Serial(serial_port, "9600", timeout=2)

        # Activate the relay switch

        try:
            ser.write(b"\xa0\x01\x01\xa2\r\n")
            # Wait the delay
            time.sleep(press_secs)
            # De-activate the relay switch
            ser.write(b"\xa0\x01\x00\xa1\r\n")
        finally:
            ser.close()
