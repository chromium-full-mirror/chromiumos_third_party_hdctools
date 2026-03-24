# Copyright 2015 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Driver for keyboard control servo feature."""

from servo.drv import hw_driver


class KbError(hw_driver.HwDriverError):
    """Error class for kb class."""


# pylint: disable=invalid-name
# Servod requires camel-case class names
class kb(hw_driver.HwDriver):
    """HwDriver wrapper around servod's keyboard functions."""

    def _drv_init(self):
        """Driver specific initializer.

        Required params:
            key: indicates what key should be pressed with each instance.

        Optional params:
            handler: indicate if default or usb keyboard handler should
                     be used for key press execution.
        """
        super()._drv_init()
        # pylint: disable=protected-access
        self._handler = self._params.get("handler", "default")
        if self._handler not in ["default", "usb"]:
            raise KbError("Unknown keyboard handler requested: %s" % self._handler)
        self._key = self._params["key"]

    def _Set_key(self, duration):
        """Press key combo for |duration| seconds.

        Note: the key to press is defined in the params of the control under
        'key'.

        Args:
          duration: seconds to hold the key pressed.
        """
        from servo.common.utils import json_utils

        val_pb = json_utils.wrap_value(duration)
        self._driver_client.SetKeyboardKey(
            key=self._key, handler=self._handler, duration=val_pb
        )

    def _Set_arb_key_config(self, key):
        """Set the key to be pressed when arb_key control is called

        Args:
          key: the key to press when arb_key is called
        """
        # Call core gRPC to set arb_key
        self._driver_client.SetArbKeyConfig(key=key, handler=self._handler)

    def _Set_arb_keys_config(self, key):
        """Set the keys to be pressed when arb_key control is called

        Args:
          key: the key to press when arb_key is called
        """
        # Call core gRPC to set arb_keys
        self._driver_client.SetArbKeysConfig(key=key, handler=self._handler)
