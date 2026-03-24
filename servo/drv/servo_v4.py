# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Driver for Servo v4 custom logic built on the low-level controls."""

import glob
import time

from servo.drv import hw_driver


_DUT_USB3_OFF_SYSCONF_GLOB = "/etc/servo/dut_usb3.no"
_DUT_USB3_ON_SYSCONF_GLOB = "/etc/servo/dut_usb3.yes"
_DUT_USB3_OFF_DATA_GLOB = "/usr/share/servo/dut_usb3.no.*"
_DUT_USB3_ON_DATA_GLOB = "/usr/share/servo/dut_usb3.yes.*"


class servoV4(hw_driver.HwDriver):
    """Class to access drv=servo_v4 controls."""

    def _drv_init(self):
        """Driver specific initializer.

        Required params:
            'usb_reset_ms': str(int) e.g. '500' - How long in milliseconds to hold
                the DUT-facing USB hub in reset for triggering DUT re-enumeration of
                Servo USB devices.
            'automatic_default': 'disabled' or 'enabled' - The default value for the
                automatic USB3-to-DUT choice setting when the current Servo v4 is
                not present in either the default-enable or default-disable lists.
        """
        super()._drv_init()

        usb_reset_ms = int(self._params["usb_reset_ms"])
        if usb_reset_ms < 0:
            raise ValueError(
                "usb_reset_ms param value must be non-negative, instead "
                "it is: %d" % (usb_reset_ms,)
            )

        default = self._params["automatic_default"]
        if default not in ("disabled", "enabled"):
            raise ValueError("invalid automatic_default param value: %r" % (default,))

        # float for time.sleep()
        self._usb_reset_seconds = usb_reset_ms / 1000.0
        # 'disabled' or 'enabled'
        self._dut_usb3_default = default
        # {str: str} - Mapping of Servo v4 serial number to 'enabled' or 'disabled',
        # representing the USB3-to-DUT setting for the Servo when
        # reinit_dut_usb3_en:automatic is set.
        self._dut_usb3_servos = {}

        # Official lists of yes-DUT-USB3 servos.
        self._LoadDutUsb3Servos(_DUT_USB3_ON_DATA_GLOB, "enabled")
        # Official lists of no-DUT-USB3 servos.
        self._LoadDutUsb3Servos(_DUT_USB3_OFF_DATA_GLOB, "disabled")
        # Local lists of yes-DUT-USB3 servos, overrides the official lists.
        self._LoadDutUsb3Servos(_DUT_USB3_ON_SYSCONF_GLOB, "enabled")
        # Local lists of no-DUT-USB3 servos, overrides the official lists.
        self._LoadDutUsb3Servos(_DUT_USB3_OFF_SYSCONF_GLOB, "disabled")

    def _LoadDutUsb3Servos(self, globpath, value):
        """Load config files of Servo v4 serial numbers to enable or disable USB3.

        For each Servo serial number loaded, this populates self._dut_usb3_servos
        with the given value.

        Config format is a text file with one Servo serial number per line.
        Leading and trailing whitespace is ignored.
        Lines beginning with # are ignored.

        Args:
          globpath: str - glob.iglob() path of the config files to load
          value: str - The self._dut_usb3_servos value to set for each Servo serial
            number that is loaded.
        """
        self._logger.debug(
            "finding USB3-to-DUT %r config files matching %r" % (value, globpath)
        )
        for path in glob.iglob(globpath):
            self._logger.debug("loading USB3-to-DUT %r config file %r" % (value, path))
            with open(path, "r") as fobj:
                for line in fobj:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        self._dut_usb3_servos[line] = value

    def _Get_reinit_dut_usb3_en(self):
        """Get the value of dut_usb3_en control.

        Returns: int - 0 for off, 1 for on
        """
        name = self._servod_get("dut_usb3_en")
        if name == "disabled":
            return 0
        if name == "enabled":
            return 1
        raise ValueError("unexpected dut_usb3_en value: %r" % (name,))

    def _Set_reinit_dut_usb3_en(self, value):
        """Set dut_usb3_en control value, with enhanced functionality.

        Behavior:
        - dut_usb3_en is only set when its value will actually change.
        - When dut_usb3_en value will change, and dut_hub_usb_reset is off, the
          latter will be toggled on briefly to trigger re-enumeration of Servo USB
          devices on the DUT.  The duration of this toggle comes from the
          usb_reset_ms config parameter.
        - When the automatic setting is used (see value arg below), exempt lists of
          Servo v4 units known to be capable or likely incapable of reliable
          USB3-to-DUT function are used.

        Args:
          value: int - 0 for off, 1 for on, 2 for automatic
        """
        if value == 0:
            new = "disabled"
        elif value == 1:
            new = "enabled"
        elif value == 2:  # 'automatic'
            serialnum = self._servod_get("root.serialname")
            new = self._dut_usb3_servos.get(serialnum, self._dut_usb3_default)
        else:
            raise ValueError("invalid reinit_dut_usb3_en map value: %r" % (value,))

        if new == self._servod_get("dut_usb3_en"):
            # No change to dut_usb3_en.
            return

        dut_hub_usb_reset = self._servod_get("dut_hub_usb_reset")
        if dut_hub_usb_reset == "on":
            # DUT USB hub is already in reset, just change dut_usb3_en.
            self._servod_set("dut_usb3_en", new)
        elif dut_hub_usb_reset == "off":
            # DUT USB hub is active, hold it in reset briefly while changing
            # dut_usb3_en to force re-enumeration.
            self._servod_set("dut_hub_usb_reset", "on")
            try:
                self._servod_set("dut_usb3_en", new)
                time.sleep(self._usb_reset_seconds)
            finally:
                self._servod_set("dut_hub_usb_reset", "off")
        else:
            raise ValueError(
                "unexpected dut_hub_usb_reset value: %r" % (dut_hub_usb_reset,)
            )
