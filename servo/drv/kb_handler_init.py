# Copyright 2018 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Driver to initialize keyboard handlers."""

# TODO(crbug.com/874707): This is a temporary solution until a more complete
# approach to interface handling and overwriting is implemented, at which point
# this code will be removed in favor of usb_keyboard and keyboard being
# interfaces.

import time

from servo.drv import hw_driver
from servo.drv import keyboard_handlers


# pylint: disable=invalid-name
# Follows error naming convention in servod.
class kbHandlerInitError(hw_driver.HwDriverError):
    """Error class for keyboard initialization issues."""


# pylint: disable=invalid-name
# Servod requires camel-case class names
class kbHandlerInit(hw_driver.HwDriver):
    """Class to handle initialization of different types of keyboard handlers."""

    # pylint: disable=protected-access
    # This class needs to set the private handlers inside Servod instance

    def _drv_init(self):
        """Driver specific initializer.

        Optional params:
            handler_type: type of keyboard handler to use
        """
        super(kbHandlerInit, self)._drv_init()
        self._handler_type = self._params.get("handler_type", None)

    def _Get_init_usb_keyboard(self):
        """Return whether the usb keyboard on the servo instance is initialized."""
        if not self._servod._usb_keyboard:
            # Setup the keyboard handler and turn it off.
            self._servod.set("init_usb_keyboard", "off")
        return int(self._servod._usb_keyboard.is_open())

    def _setup_usb_keyboard(self, value):
        """Setup the usb keyboard on the servo instance."""
        # Avoid reinitializing the same usb keyboard handler.
        if self._servod._usbkm232:
            usb_kb = keyboard_handlers.USBkm232Handler(
                self._servod, self._servod_usbkm232
            )
        else:
            self._logger.debug(
                "No device path specified for usbkm232 handler. Use "
                "the servo atmega chip to handle."
            )
            # Use servo onboard keyboard emulator.
            if not self._servod.has_control("atmega_rst"):
                msg = "No atmega in servo board. So no keyboard support."
                self._logger.warning(msg)
                raise kbHandlerInitError(msg)
            # This flag is used in servo v2 to setup the atmega chip properly.
            legacy_atmega = "init_atmega_uart" in self._params
            usb_kb = keyboard_handlers.ServoUSBkm232Handler(self._servod, legacy_atmega)
        self._servod._usb_keyboard = usb_kb

    def _Set_init_usb_keyboard(self, value):
        if not self._servod._usb_keyboard:
            # Setup the keyboard always, and then turn on/off as needed.
            self._setup_usb_keyboard(value)
        if value:
            self._servod._usb_keyboard.open()
        else:
            self._servod._usb_keyboard.close()

    def _Get_init_default_keyboard(self):
        """Return whether the keyboard on the servo instance is initialized."""
        if not self._servod._keyboard:
            # Setup the keyboard handler and turn it off.
            self._servod.set("init_keyboard", "off")
        return int(self._servod._keyboard.is_open())

    def _Set_init_default_keyboard(self, value):
        """Initialize the default keyboard on the servo instance."""
        if not self._servod._keyboard:
            if self._handler_type == "usb":
                # Call through servo instead of calling method directly, because the
                # |_params| for default keyboard is not the same as for usb keyboard.
                if self._servod.has_control("init_usb_keyboard"):
                    self._servod.set("init_usb_keyboard", value)
                    self._servod._keyboard = self._servod._usb_keyboard
                else:
                    # This might be working as intended e.g. micro without a v4.
                    # Warn the user about this, but don't make a scene.
                    self._logger.warning(
                        "The servo setup does not have a usb keyboard "
                        "emulator. Will not throw an error, but note "
                        "that the keyboard controls will fail, as only "
                        "noop keyboard could be setup."
                    )
                    self._servod._keyboard = keyboard_handlers.NoopHandler()
            else:
                # The main keyboard is a normal keyboard handler.
                handler_class_name = "%sHandler" % self._handler_type
                handler_class = getattr(keyboard_handlers, handler_class_name)
                self._servod._keyboard = handler_class(self._servod)
        if value:
            self._servod._keyboard.open()
        else:
            # Here, we want to turn off the kb handler.
            self._servod._keyboard.close()
