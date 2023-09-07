# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""c2d2 manufacturer providing usb data, setting up programmers and phases."""

from servo_mfg import color_mode as cm
from servo_mfg import device_util
from servo_mfg import manufacturer
from servo_mfg.serial_programmer import SerialProgrammer
from servo_mfg.servo_programmer import ServoProgrammer


class C2D2ManufacturerError(Exception):
    """C2D2Manufacturer error class."""


class C2D2Manufacturer(manufacturer.Manufacturer):
    """Class performing all device programming for c2d2."""

    # Redefine the interface as c2d2 has its servo console on usb interface
    # 3 unlike other devices.
    SERVO_IFACE = 3

    BOARD = "c2d2"

    # The VID/PID of the stm chip before programming/in DFU mode
    STM_DFU_VID = 0x0483
    STM_DFU_PID = 0xDF11
    # The VID/PID of the servo device once programmed
    SERVO_VID = 0x18D1
    SERVO_PID = 0x5041

    def __init__(self, validation, args):
        """Initialize the logger, and register the programmers/task descriptions."""
        manufacturer.Manufacturer.__init__(self, validation)
        # Initialize all programmers to be None.

        # Note: below, to make the code less verbose, 'td' is used as a suffix
        # for task description

        dfu_td = "Firmware Flashing (STM32F072) DFU [U1]"
        dfu_programmer = None
        if args.flash:
            dfu_programmer = ServoProgrammer(
                self.BOARD, dfu_vid=self.STM_DFU_VID, dfu_pid=self.STM_DFU_PID
            )
        self._set_dfu_task(dfu_programmer, dfu_td)

        serial_td = "Serialname Writing"
        serial_programmer = None
        if args.serial:
            serial_programmer = SerialProgrammer(
                args.force_serial, servo_vid=self.SERVO_VID, servo_pid=self.SERVO_PID
            )
        self._register_post_dfu_task(serial_programmer, serial_td)

    # Wait here for all the necessary usb devices to be available. The
    # individual programmers do not wait for the usb device, rather they check
    # and give up if not found.

    def _dfu_prep(self):
        """Instruct user to plug in device in DFU mode."""
        m = cm.blue("Plug c2d2 in with the OTG cable, coming up in DFU mode.")
        device_util.wait_for_usb_device(
            vid=self.STM_DFU_VID, pid=self.STM_DFU_PID, message=m
        )

    def _dfu_post(self):
        """Wait until the device is disconnected from DFU and reconnected again."""
        m = cm.blue("Unplug the host side USB OTG cable.")
        device_util.wait_for_usb_disconnect(
            vid=self.STM_DFU_VID, pid=self.STM_DFU_PID, message=m
        )
        m = cm.red("Plug c2d2 in with normal mode cable (regular micro USB cable).")
        device_util.wait_for_usb_device(
            vid=self.SERVO_VID, pid=self.SERVO_PID, message=m
        )

    def _post_dfu_prep(self):
        """Wait for servo (programmed) to appear as a USB device."""
        # Wait again for the servo as we don't know what state we're in here.
        m = cm.red(
            "Ensure the c2d2 is plugged in in normal mode (regular micro USB cable)."
        )
        device_util.wait_for_usb_device(
            vid=self.SERVO_VID, pid=self.SERVO_PID, message=m
        )
