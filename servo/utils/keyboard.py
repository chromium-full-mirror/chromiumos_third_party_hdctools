# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import logging

from servo.common.utils import keyboard_handlers


class KeyboardUtilError(Exception):
    """Error class for keyboard util."""


def get_keyboard(servod, handler):
    """
    Get the correct keyboard to use.

    Args:
        servod: Servod instance
        handler: keyboard handler
    """
    keyboard = servod._usb_keyboard if handler == "usb" else servod._keyboard
    if not keyboard:
        raise KeyboardUtilError("Keyboard %s handler not setup." % (handler,))
    return keyboard


def set_usb_keyboard(grpc_core_addr, servod, legacy_atmega):
    """
    set keyboard values
    """
    logger = logging.getLogger("keyboardUtil")
    # Avoid reinitializing the same usb keyboard handler.
    if servod._usbkm232:
        usb_kb = keyboard_handlers.USBkm232Handler(grpc_core_addr, servod._usbkm232)
    else:
        logger.debug(
            "No device path specified for usbkm232 handler. Use "
            "the servo atmega chip to handle."
        )
        # Use servo onboard keyboard emulator.
        if not servod.has_control("atmega_rst"):
            msg = "No atmega in servo board. So no keyboard support."
            logger.warning(msg)
            raise KeyboardUtilError(msg)
        # This flag is used in servo v2 to setup the atmega chip properly.
        usb_kb = keyboard_handlers.ServoUSBkm232Handler(grpc_core_addr, legacy_atmega)
    servod._usb_keyboard = usb_kb


def set_keyboard(grpc_core_addr, servod, handler_type, value):
    """
    set keyboard values
    """
    logger = logging.getLogger("keyboardUtil")
    if not servod._keyboard:
        if handler_type == "usb":
            # Call through servo instead of calling method directly, because the
            # |_params| for default keyboard is not the same as for usb keyboard.
            if servod.has_control("init_usb_keyboard"):
                servod.set("init_usb_keyboard", value)
                servod._keyboard = servod._usb_keyboard
            else:
                # This might be working as intended e.g. micro without a v4.
                # Warn the user about this, but don't make a scene.
                logger.warning(
                    "The servo setup does not have a usb keyboard "
                    "emulator. Will not throw an error, but note "
                    "that the keyboard controls will fail, as only "
                    "noop keyboard could be setup."
                )
                servod._keyboard = keyboard_handlers.NoopHandler(grpc_core_addr)
        else:
            # The main keyboard is a normal keyboard handler.
            handler_class_name = "%sHandler" % handler_type
            handler_class = getattr(keyboard_handlers, handler_class_name)
            servod._keyboard = handler_class(grpc_core_addr)
    if value:
        servod._keyboard.open()
    else:
        # Here, we want to turn off the kb handler.
        servod._keyboard.close()
