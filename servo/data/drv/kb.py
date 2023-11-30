# Copyright 2015 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Driver for keyboard control servo feature."""

from servo.data.drv import hw_driver


class KbError(hw_driver.HwDriverError):
    """Error class for kb class."""


# pylint: disable=invalid-name
# Servod requires camel-case class names
class kb(hw_driver.HwDriver):
    """HwDriver wrapper around servod's keyboard functions."""

    def __init__(self, interface, params, servod):
        """Constructor.

        Args:
          interface: hardware interface for low-level communication; ignored here
          params: dictionary of params;
            'key' attribute indicates what key should be pressed with each instance.
            'handler' optional, indicate if default or usb keyboard handler should
                      be used for key press execution.
          servod: Servod that is used for cross-servo-device communication
        """
        super(kb, self).__init__(interface, params.copy(), servod)
        # pylint: disable=protected-access
        self._handler = self._params.get("handler", "default")
        if self._handler not in ["default", "usb"]:
            raise KbError("Unknown keyboard handler requested: %s" % self._handler)
        self._key = params["key"]

    def _GetKeyboard(self):
        """Get the correct keyboard to use."""
        keyboard = (
            self._servod._usb_keyboard
            if self._handler == "usb"
            else self._servod._keyboard
        )
        if not keyboard:
            raise KbError("Keyboard %s handler not setup." % (self._handler,))
        return keyboard

    def _Set_key(self, duration):
        """Press key combo for |duration| seconds.

        Note: the key to press is defined in the params of the control under
        'key'.

        Args:
          duration: seconds to hold the key pressed.

        Raises:
          KbError: if key is not a member of kb_precanned map.
        """
        turn_off_needed = False
        keyboard = self._GetKeyboard()
        if not keyboard.is_open():
            turn_off_needed = True
            self._logger.info(
                "Keyboard %s handler not setup. Turning on now.", self._handler
            )
            keyboard.open()
        func = getattr(keyboard, self._key, None)
        if func is None:
            raise KbError("Key %r not found." % (self._key,))
        func(press_secs=duration)
        if turn_off_needed:
            self._logger.info("Keyboard was not on for call. Turning it off again.")
            keyboard.close()

    def _Set_arb_key_config(self, key):
        """Set the key to be pressed when arb_key control is called

        Args:
          key: the key to press when arb_key is called
        """
        self._GetKeyboard().arb_key_config(key)

    def _Set_arb_keys_config(self, key):
        """Set the keys to be pressed when arb_key control is called

        Args:
          key: the key to press when arb_key is called
        """
        self._GetKeyboard().arb_keys_config(key)
