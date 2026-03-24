# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Driver to handle getting and setting the gbb flags with futility."""

import re
import subprocess

from servo.common.utils import json_utils
from servo.drv import hw_driver
from servo.utils.sys_interface import sys_interface


class futilityGbbError(hw_driver.HwDriverError):
    """Exception class for futility GBB."""


# pylint: disable=invalid-name
# Servod driver discovery logic requires this naming convention
class futilityGbb(hw_driver.HwDriver):
    """Driver to handle getting and setting the gbb flags with futility."""

    # The ccd device uses the "ccd" prefix
    _CCD_SERIAL = "ccd_serialname"
    _CCD_CPU_FW_SPI = "ccd_cpu_fw_spi"

    # Used to lookup saved device information
    _KEY_BASE_COMMAND = "base_command"
    _KEY_CPU_FW_SPI = "cpu_fw_spi"

    # futility args
    _FUTILITY = "futility"
    _GBB = "gbb"
    _CCD_PROGRAMMER = "raiden_debug_spi:target=AP,serial=%s"
    _CUSTOM_RST = ",custom_rst=true"
    _GET = "--get"
    _SET = "--set"
    _FLAGS = "--flags"

    # Used to validate the flag input
    _OK_FLAG_RE = r"^0x[0-9a-fA-F]{1,8}$"
    # Regex used to find the flag value from the futility output
    _OUTPUT_FLAG_RE = r"flags: (0x\S*)"

    def _device_info(self, arg):
        if not hasattr(self, "futility_device_info"):
            self.futility_device_info = {}
        if self._prefix not in self.futility_device_info:
            self._init_ccd_futility_info()
        return self.futility_device_info[self._prefix][arg]

    def _init_ccd_futility_info(self):
        """Initialize the ccd programmer args."""
        info = self.futility_device_info
        info[self._prefix] = {}
        prefix = self._prefix + "." if self._prefix else ""
        ccd_cpu_fw_spi = prefix + self._CCD_CPU_FW_SPI
        if not self._servod_has_control(ccd_cpu_fw_spi):
            ccd_cpu_fw_spi = None
        info[self._prefix][self._KEY_CPU_FW_SPI] = ccd_cpu_fw_spi

        # If boards have a ccd_cpu_fw_spi control, manually set it before
        # and after the futility command. Add the custom_rst=true arg to
        # the programmer, so futility doesn't override the ccd_cpu_fw_spi
        # setting.
        programmer = self._get_ccd_programmer()
        if ccd_cpu_fw_spi:
            programmer += self._CUSTOM_RST
        base_command = [self._FUTILITY, self._GBB, "-p", programmer]
        info[self._prefix][self._KEY_BASE_COMMAND] = base_command

    def _get_ccd_programmer(self):
        """Return the futility programmer arg with the correct serial."""
        return (
            self._CCD_PROGRAMMER
            % self._driver_client.GetServo(control_name=self._CCD_SERIAL).response
        )

    def _run_command(self, command):
        """Run a command on the servo host"""
        self._logger.debug("running %r", command)
        return sys_interface.check_output(command, encoding="utf-8")

    def _run_ccd_futility_gbb_command(self, args):
        """Run the GBB command"""
        cpu_fw_spi = self._device_info(self._KEY_CPU_FW_SPI)
        command = []
        command.extend(self._device_info(self._KEY_BASE_COMMAND))
        command.extend(args)
        try:
            # Enable access to AP SPI flash over CCD
            if cpu_fw_spi:
                val_pb = json_utils.wrap_value("on")
                self._driver_client.SetServo(control_name=cpu_fw_spi, value=val_pb)

            # Run the futility gbb command
            return self._run_command(command)
        finally:
            # Undo the AP SPI flash setup
            if cpu_fw_spi:
                val_pb = json_utils.wrap_value("off")
                self._driver_client.SetServo(control_name=cpu_fw_spi, value=val_pb)

    def _Set_ccd_flags(self, value):
        """Set the GBB flags with CCD."""
        flags = value.strip()
        if not re.search(self._OK_FLAG_RE, flags):
            raise futilityGbbError("Invalid flags: %r" % flags)
        args = [self._SET, self._FLAGS + "=" + flags]
        result = self._run_ccd_futility_gbb_command(args)
        self._logger.debug("Set flags: %s", result)

    def _Get_ccd_flags(self):
        """Get the GBB flags with CCD."""
        args = [self._GET, self._FLAGS]
        result = self._run_ccd_futility_gbb_command(args)
        self._logger.debug("futility output: %s", result)
        match = re.search(self._OUTPUT_FLAG_RE, result)
        if not match:
            raise futilityGbbError("Failed to get flags: %r" % result)
        return match.group(1)
