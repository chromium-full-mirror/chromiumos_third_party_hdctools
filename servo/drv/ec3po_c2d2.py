# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for c2d2 specific controls through ec3po."""

from servo.drv import ec3po_servo
from servo.drv import pty_driver


class ec3poC2d2(ec3po_servo.ec3poServo):
    """Object to access drv=ec3po_c2d2 controls.

    Note, instances of this object get dispatched via base class,
    HwDriver's get/set method. That method ultimately calls:
      "_[GS]et_%s" % params['subtype'] below.

    For example, a control to read kbd_en would be dispatched to
    call _Get_kbd_en.
    """

    def _drv_init(self):
        """Driver specific initializer."""
        super()._drv_init()

    def _Get_ec_uart_en(self):
        """Returns '1' if the EC UART output is enabled. '0' if it's disabled."""
        rv = self._issue_cmd_get_results(
            "gpioget EN_CLK_CSN_EC_UART", [r"\s+([01])\*?\s+EN_CLK_CSN_EC_UART"]
        )
        return rv[0][1]

    def _Set_ec_uart_en(self, value):
        """Controls the EC UART output enable.

        Args:
          value: 1 to enable output, 0 to disable it.
        """
        self._issue_cmd("gpioset EN_CLK_CSN_EC_UART %s" % value)

    def _Get_uut_boot_mode(self):
        """Gets the current UUT (UART) boot mode for the EC.

        Returns:
          'on' if EC_TX is being held low. The UART on stm32 is disabled
          'off' if EC_TX and EC_RX are in normal UART mode
        """
        # EC UART is connected to USART1
        result = self._issue_cmd_get_results("hold_usart usart1", [r"status: (\w+)"])[
            0
        ][1]
        if result == "normal":
            return "off"
        return "on"

    def _Set_uut_boot_mode(self, value):
        """Sets the current UUT (UART) boot mode for the EC

        Args:
          value: 1 to hold EC_TX low, 0 to use EC UART as normal
        """
        # EC UART is connected to USART1
        self._issue_cmd("hold_usart usart1 %s" % value)

    def _Get_h1_reset(self):
        """Gets the current H1 reset state for DUT.

        Returns:
          1 if H1 is being held in reset. 0 if H1 can run normally.
        """
        result = self._issue_cmd_get_results("h1_reset", [r"H1 reset held: (\w+)"])[0][
            1
        ]
        return int(result == "yes")

    def _Set_h1_reset(self, value):
        """Sets the current H1 reset state for DUT.

        Args:
          value: 1 to hold H1 in reset, 0 to release H1 from reset.
        """
        self._issue_cmd("h1_reset %s" % value)

    def _Get_pwr_button(self):
        """Gets the current power button state for DUT.

        Returns:
          'on' if power button is being held in reset.
          'off' if power button is released
        """
        result = self._issue_cmd_get_results(
            "pwr_button", [r"Power button held: (\w+)"]
        )[0][1]
        return result

    def _Set_pwr_button(self, value):
        """Sets the current power button state for DUT.

        Args:
          value: 1 to hold power button, 0 to release power button.
        """
        self._issue_cmd("pwr_button %s" % value)

    def _Get_spi_vref(self):
        """Gets the current SPI Vref for DUT voltage.

        Returns:
          Rail voltage in mV
        """
        result = self._issue_cmd_get_results("enable_spi", [r"SPI Vref: (\d+)"])[0][1]
        return result

    def _Set_spi_vref(self, value):
        """Sets the current SPI Vref for DUT voltage.

        Args:
          value: 0, 1800, and 3300; The mV to the rail
        """
        self._issue_cmd("enable_spi %s" % value)

    def _Get_i2c_speed(self):
        """Gets the i2c bus speed for the bus specified in the control

        Returns:
          I2C Bus speed in kbps units
        """
        bus = self._params["bus"]
        result = self._issue_cmd_get_results(
            "enable_i2c %s" % bus,
            # The original C2D2 Console responded with kpbs instead of kbps :(
            [r"I2C speed k[bp]+s: (\d+)"],
        )[0][1]
        return result

    def _Set_i2c_speed(self, value):
        """Sets the i2c bus speed for the bus specified in the control.

        Args:
          value: 0, 100, 400, and 1000; The i2c bus speed in kbps units
        """
        bus = self._params["bus"]
        self._issue_cmd("enable_i2c %s %d" % (bus, value))

    def _Get_h1_vref(self):
        """Gets if H1 Vref is present or not

        Returns:
          1 if H1 vref is present, otherwise 0
        """
        result = self._issue_cmd_get_results("h1_vref", [r"H1 Vref: (\w+)"])[0][1]
        return int(result == "on")
