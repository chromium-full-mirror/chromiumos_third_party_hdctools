# Copyright 2018 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Driver to initialize keyboard handlers."""

# TODO(crbug.com/874707): This is a temporary solution until a more complete
# approach to interface handling and overwriting is implemented, at which point
# this code will be removed in favor of usb_keyboard and keyboard being
# interfaces.

from servo.common.proto import servo_dev_pb2
from servo.drv import hw_driver


# pylint: disable=invalid-name
# Follows error naming convention in servod.
class kbHandlerInitError(hw_driver.HwDriverError):
    """Error class for keyboard initialization issues."""


# pylint: disable=invalid-name
# Servod requires camel-case class names
class kbHandlerInit(hw_driver.HwDriver):
    """Class to handle initialization of different types of keyboard handlers."""

    # pylint: disable=protected-access

    def _drv_init(self):
        """Driver specific initializer.

        Optional params:
            handler_type: type of keyboard handler to use
        """
        super()._drv_init()
        self._handler_type = self._params.get("handler_type", None)

    def _Get_init_usb_keyboard(self):
        """Return whether the usb keyboard on the servo instance is initialized."""
        # This flag is used in servo v2 to setup the atmega chip properly.
        legacy_atmega = "init_atmega_uart" in self._params
        response = self._driver_client.GetInitUsbKeyboard(value=legacy_atmega)
        return response.open

    def _Set_init_usb_keyboard(self, value):
        from servo.common.utils import json_utils

        legacy_atmega = "init_atmega_uart" in self._params
        val_pb = json_utils.wrap_value(value)
        self._driver_client.SetInitUsbKeyboard(value=val_pb, is_legacy=legacy_atmega)

    def _Get_init_default_keyboard(self):
        """Return whether the keyboard on the servo instance is initialized."""
        response = self._driver_client.GetInitKeyboard(type=self._handler_type)
        return response.open

    def _Set_init_default_keyboard(self, value):
        """Initialize the default keyboard on the servo instance."""
        from servo.common.utils import json_utils

        val_pb = json_utils.wrap_value(value)
        self._driver_client.SetInitKeyboard(
            handler_type=self._handler_type, value=val_pb
        )
