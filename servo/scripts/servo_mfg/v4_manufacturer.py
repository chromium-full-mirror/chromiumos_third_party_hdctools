# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""v4 manufacturer providing usb data, setting up programmers and phases."""

from servo_mfg import device_util
from servo_mfg import manufacturer
from servo_mfg.atmega_kb_programmer import AtmegaKBEmulatorProgrammer
from servo_mfg.rtk_eth_programmer import RTKEthProgrammer
from servo_mfg.serial_programmer import SerialProgrammer
from servo_mfg.servo_programmer import ServoProgrammer


class V4ManufacturerError(Exception):
    """V4Manufacturer error class."""


class V4Manufacturer(manufacturer.Manufacturer):
    """Class performing all device programming for servo v4."""

    SERVO_IFACE = 0

    BOARD = "servo_v4"

    # The VID/PID of the stm chip before programming/in DFU mode
    STM_DFU_VID = 0x0483
    STM_DFU_PID = 0xDF11
    # The VID/PID of the servo device once programmed
    SERVO_VID = 0x18D1
    SERVO_PID = 0x501B

    # The HH VID/PID is HOST hub i.e. the usb hub facing the servo host side
    # of the servo.
    HH_VID = 0x04B4  # Cypress
    HH_PID = 0x6572

    # The DH VID/PID is DUT hub i.e. the usb hub facing the dut side of the servo.
    DH_VID = 0x04B4  # Cypress
    DH_PID = 0x6502
    DH_PID3 = 0x6500

    # The atmega keyboard emulator needs to know where it is on the gpioexpander
    # to toggle modes and reboot.
    ATM_I2C_ADDR = 0x20
    ATM_I2C_OFFSET = 2

    def __init__(self, validation, args):
        """Initialize the logger."""
        manufacturer.Manufacturer.__init__(self, validation)
        # Note: below, to make the code less verbose, 'td' is used as a suffix
        # for task description

        dfu_td = "Firmware Flashing (STM32F072) DFU [U3]"
        dfu_programmer = None
        if args.flash:
            dfu_programmer = ServoProgrammer(
                self.BOARD, dfu_vid=self.STM_DFU_VID, dfu_pid=self.STM_DFU_PID
            )
        self._set_dfu_task(dfu_programmer, dfu_td)

        eth_td = "Ethernet adapter (RTL8153B) Serial EEPROM/MAC Programming [U29]"
        eth_programmer = None
        if args.mac:
            eth_programmer = RTKEthProgrammer(
                args.force_mac,
                parent_hub_vid=self.DH_VID,
                parent_hub_pid=self.DH_PID,
                parent_hub_pid3=self.DH_PID3,
            )
        self._register_post_dfu_task(eth_programmer, eth_td)

        kb_td = "Keyboard Emulator (ATMEGA32U4) Programming [U13]"
        kb_programmer = None
        if args.kb_emulator:
            kb_programmer = AtmegaKBEmulatorProgrammer(
                args.force_kb_emulator,
                i2caddr=self.ATM_I2C_ADDR,
                i2coffset=self.ATM_I2C_OFFSET,
                parent_hub_vid=self.DH_VID,
                parent_hub_pid=self.DH_PID,
            )
        self._register_post_dfu_task(kb_programmer, kb_td)

        serial_td = "Serialname Writing"
        serial_programmer = None
        if args.serial:
            serial_programmer = SerialProgrammer(
                args.force_serial,
                servo_vid=self.SERVO_VID,
                servo_pid=self.SERVO_PID,
                parent_hub_vid=self.HH_VID,
                parent_hub_pid=self.HH_PID,
            )
        self._register_post_dfu_task(serial_programmer, serial_td)

    # Wait here for all the necessary usb devices to be available. The
    # individual programmers do not wait for the usb device, rather they check
    # and give up if not found.

    def _dfu_prep(self):
        """Instruct user to plug in device in DFU mode."""
        device_util.wait_for_usb_device(
            vid=self.STM_DFU_VID,
            pid=self.STM_DFU_PID,
            message="Plug the servo v4 in with the OTG "
            "cable into the host side connector, "
            "coming up in DFU mode.",
        )

    def _dfu_post(self):
        """Wait until the device is disconnected from DFU and reconnected again."""
        device_util.wait_for_usb_disconnect(
            vid=self.STM_DFU_VID,
            pid=self.STM_DFU_PID,
            message="Unplug the host side USB OTG cable from the servo v4.",
        )
        device_util.wait_for_usb_device(
            vid=self.SERVO_VID,
            pid=self.SERVO_PID,
            message="Plug the servo v4 in with the "
            "normal mode cable (regular micro usb "
            "cable).",
        )

    def _post_dfu_prep(self):
        """Wait for host side and dut side connection both."""
        # Wait again for the host-hub as we don't know what state we're in here.
        device_util.wait_for_usb_device(
            vid=self.HH_VID,
            pid=self.HH_PID,
            message="Ensure the host side is plugged "
            "in with the normal mode cable (regular "
            "micro usb cable).",
        )
        # The servo devices enumerates automatically when the right cables are
        # plugged in. Wait here explicitly for it as this is the first time the
        # device enumerates after flashing.
        device_util.wait_for_usb_device(vid=self.SERVO_VID, pid=self.SERVO_PID)
        device_util.wait_for_usb_device(
            vid=self.DH_VID, pid=self.DH_PID, message="Plug DUT side cable in."
        )
