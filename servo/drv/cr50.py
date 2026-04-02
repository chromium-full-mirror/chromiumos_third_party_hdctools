# Copyright 2016 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Driver for board config controls of drv=cr50.

Provides the following Cr50 controlled function:
  cold_reset
  warm_reset
  ccd_keepalive_en
"""

import functools
import logging
import re
import time

from servo.drv import pty_driver


def restricted_command(func):
    """Decorator for methods which use restricted console command."""

    @functools.wraps(func)
    def wrapper(instance, *args, **kwargs):
        try:
            return func(instance, *args, **kwargs)
        except cr50Error as e:
            if str(e) in [
                "Timeout waiting for response.",
                "No data was sent from the pty.",
            ]:
                e.args = (
                    e.args[0]
                    + "CCD console might be locked. Check and unlock with instructions https://chromium.googlesource.com/chromiumos/platform/ec/+/cr50_stab/docs/case_closed_debugging_cr50.md",
                )
            # Raise the original exception
            raise

    return wrapper


class cr50Error(pty_driver.PtyError):
    """Exception class for Cr50."""


class cr50(pty_driver.PtyDriver):
    """Object to access drv=cr50 controls.

    Note, instances of this object get dispatched via base class,
    HwDriver's get/set method. That method ultimately calls:
      "_[GS]et_%s" % params['subtype'] below.

    For example, a control to read kbd_en would be dispatched to
    call _Get_kbd_en.
    """

    # Retry mechanism for prompt detection in case of spurious printfs.
    PROMPT_DETECTION_TRIES = 3
    PROMPT_DETECTION_INTERVAL = 1

    RDD_RE = re.compile(
        r"Rdd:\s+(?P<rdd>\S+)[\r\n]+(KeepAlive:\s+(?P<keepalive>\S+)\s)?"
    )

    def _drv_init(self):
        """Driver specific initializer."""
        super()._drv_init()

        if not hasattr(self._interface, "ccd_uart_bitbang_settings"):
            self._interface.ccd_uart_bitbang_settings = {
                "enabled": 0,
                "parity": None,
                "baudrate": None,
            }

    @restricted_command
    def _get(self):
        # Explicit call parent class method to apply annotation.
        return super()._get()

    @restricted_command
    def _set(self, value):
        # Explicit call parent class method to apply annotation.
        return super()._set(value)

    def _issue_cmd_get_results(
        self, cmds, regex_list, flush=None, timeout=pty_driver.DEFAULT_UART_TIMEOUT
    ):
        """Send \n to make sure cr50 is awake before sending cmds

        Make sure we get some sort of response before considering cr50 up. If it's
        already up, we should see '>' almost immediately. If cr50 is in deep
        sleep, wait for console enabled.
        """
        trys_left = self.PROMPT_DETECTION_TRIES
        while trys_left > 0:
            trys_left -= 1
            try:
                # Arrows -> and => in startup text are excluded from counting as the
                # prompt
                super()._issue_cmd_get_results("\n\n", [r"([^-=]>|Console is enabled)"])
                break
            except pty_driver.PtyError as e:
                logging.debug(
                    "cr50 prompt detection failed, %d attempts left.", trys_left
                )
                if trys_left <= 0:
                    self._logger.warning(
                        "Consider checking whether the servo device has "
                        "read/write access to the Cr50 UART console."
                    )
                    raise cr50Error("cr50 uart is unresponsive") from e
                time.sleep(self.PROMPT_DETECTION_INTERVAL)

        return super()._issue_cmd_get_results(
            cmds, regex_list, flush=flush, timeout=timeout
        )

    def _Get_cold_reset(self):
        """Return asserted or deasserted based on the EC_RST_L state"""
        result = self._issue_cmd_get_results(
            "ecrst", [r"EC_RST_L is (asserted|deasserted)"]
        )[0]
        return result[1]

    def _Set_cold_reset(self, value):
        """Setter of cold_reset (active low).

        Args:
          value: 0=on, 1=off.
        """
        if value == 0:
            self._issue_cmd("ecrst on")
        else:
            self._issue_cmd("ecrst off")

    def _Set_ecrst_pulse(self, value):
        """Setter of ecrst_pulse (active low).

        Args:
          value: 0=send ecrst pulse, 1=send ecrst off.
        """
        if value == 0:
            self._issue_cmd("ecrst pulse")
        else:
            self._issue_cmd("ecrst off")

    def _Set_warm_reset(self, value):
        """Setter of warm_reset (active low).

        Args:
          value: 0=on, 1=off.
        """
        if value == 0:
            self._issue_cmd("sysrst on")
        else:
            self._issue_cmd("sysrst off")

    def _Set_pwr_button(self, value):
        """CCD doesn't support pwr_button. Tell user about pwr_button_hold"""
        raise cr50Error("pwr_button not supported use pwr_button_hold")

    def _Set_gsc_reboot(self, _unused):
        """Reboot cr50 ignoring the value."""
        self._issue_cmd("reboot")

    def _get_ccd_cap_state(self, cap):
        """Get the current state of the ccd capability"""
        result = self._issue_cmd_get_results("ccdstate", [r"%s:([^\n]*)\n" % cap])
        return result[0][1].strip()

    def _Get_ccd_keepalive_en(self):
        """Getter of ccd_keepalive_en.

        Returns:
          0: keepalive disabled.
          1: keepalive enabled.
        """
        result = self._issue_cmd_get_results("ccdstate", ["ccdstate.*>"])[0]
        rddstate = self.RDD_RE.search(result)
        if not rddstate:
            raise cr50Error("Unable to get rdd output %r" % result)
        # Older versions of cr50 don't have a devoted KeepAlive field. Use the
        # keepalive output where possible.
        # Check for shorter strings in case servo drops output.
        keepalive = rddstate.group("keepalive")
        if keepalive:
            state = "ena" in keepalive
        else:
            state = "keep" in rddstate.group("rdd")
        return int(state)

    def _Set_ccd_keepalive_en(self, value):
        """Setter of ccd_keepalive_en.

        Args:
          value: 0=off, 1=on.
        """
        self._issue_cmd("rddkeepalive %s" % ("on" if value else "off"))

    def _Get_ec_uart_bitbang_en(self):
        return int(self._interface.ccd_uart_bitbang_settings["enabled"])

    def _Set_ec_uart_bitbang_en(self, value):
        if value:
            # We need parity and baudrate settings in order to enable bit banging.
            if not self._interface.ccd_uart_bitbang_settings["parity"]:
                raise ValueError("No parity set.  Try setting 'ec_uart_parity' first.")

            if not self._interface.ccd_uart_bitbang_settings["baudrate"]:
                raise ValueError(
                    "No baud rate set.  Try setting 'ec_uart_baudrate' first."
                )

            # The EC UART index is 2.
            cmd = "%s %s %s" % (
                "bitbang 2",
                self._interface.ccd_uart_bitbang_settings["baudrate"],
                self._interface.ccd_uart_bitbang_settings["parity"],
            )
            try:
                # Cr50 and Ti50 have different outputs.
                result = self._issue_cmd_get_results(
                    cmd, [r"Bit bang enabled|baud rate - parity"]
                )
                if result is None:
                    raise cr50Error("Unable to enable bit bang mode!")
            except pty_driver.PtyError as e:
                raise cr50Error("Unable to enable bit bang mode!") from e

            self._interface.ccd_uart_bitbang_settings["enabled"] = 1

        else:
            self._issue_cmd("bitbang 2 disable")
            self._interface.ccd_uart_bitbang_settings["enabled"] = 0

    def _Get_ccd_ec_uart_parity(self):
        self._logger.debug("%r", self._interface.ccd_uart_bitbang_settings)
        return self._interface.ccd_uart_bitbang_settings["parity"]

    def _Set_ccd_ec_uart_parity(self, value):
        if value.lower() not in ["odd", "even", "none"]:
            raise ValueError("Bad parity (%s). Try 'odd', 'even', or 'none'." % value)

        self._interface.ccd_uart_bitbang_settings["parity"] = value
        self._logger.debug("%r", self._interface.ccd_uart_bitbang_settings)

    def _Get_ccd_ec_uart_baudrate(self):
        return self._interface.ccd_uart_bitbang_settings["baudrate"]

    def _Set_ccd_ec_uart_baudrate(self, value):
        if value is not None and value.lower() not in [
            "none",
            "1200",
            "2400",
            "4800",
            "9600",
            "19200",
            "38400",
            "57600",
            "115200",
        ]:
            raise ValueError(
                "Bad baud rate(%s). Try '1200', '2400', '4800', '9600',"
                " '19200', '38400', '57600', or '115200'" % value
            )

        if value.lower() == "none":
            value = None
        self._interface.ccd_uart_bitbang_settings["baudrate"] = value

    def _Get_ec_boot_mode(self):
        """Return 1 if EC_FLASH_SELECT is asserted. 0 if it's deasserted"""
        result = self._issue_cmd_get_results(
            "gpioget EC_FLASH_SELECT", [r"\s+([01])\*?\s+EC_FLASH_SELECT"]
        )[0]
        return int(result[1])

    def _Set_ec_boot_mode(self, value):
        """Set EC_FLASH_SELECT"""
        self._issue_cmd("gpioset EC_FLASH_SELECT %s" % value)

    def _Get_uut_boot_mode(self):
        """Returns 0 if the boot_mode output is enabled. 1 if it isn't"""
        result = self._issue_cmd_get_results("gpiocfg", ["gpiocfg(.*)>"])[0][0]
        # GSC may read 0 or 1 on GPIO0_GPIO15. It just matters that GSC tries to
        # drive it to 0.
        # When uut_boot_mode is set, 0 turns uut_boot_mode on. 1 turns if off.
        if re.search(r"GPIO0_GPIO15:\s+read . drive 0", result):
            return 0
        return 1

    def _Get_ap_flash_select(self):
        """Returns 1 if AP_FLASH_SELECT is on. 0 if it's off"""
        result = self._issue_cmd_get_results(
            "gpioget AP_FLASH_SELECT", [r"\s+([01])\*?\s+AP_FLASH_SELECT"]
        )[0]
        return int(result[1])

    def _Set_ap_flash_select(self, value):
        self._issue_cmd("gpioset AP_FLASH_SELECT %s" % value)

    def _Set_uut_boot_mode(self, value):
        self._issue_cmd("gpioset EC_TX_CR50_RX_OUT %s" % value)

    def _Set_detect_servo(self, val):
        """Setter of the servo detection state.

        ccdblock can be configured to enable servo detection even if ccd is enabled.
        Cr50 uses EC uart to detect servo. If cr50 drives that signal, it can't
        detect servo pulling it up. ccdblock servo will disable uart, so we can
        detect servo.
        """
        if val:
            self._issue_cmd("ccdblock servo enable")
            # make sure we aren't ignoring servo. That will interfere with detection.
            self._issue_cmd("ccdblock IGNORE_SERVO disable")
        else:
            self._issue_cmd("ccdblock servo disable")

    def _Get_rec_btn_force(self):
        result = self._issue_cmd_get_results("recbtnforce", [r"RecBtn:([\S ]+)[\n\r]"])[
            0
        ][1]
        if result is None:
            raise cr50Error("Cannot retrieve the recbtnforce on cr50 console.")
        if "not pressed" in result:
            return 0
        if "forced pressed" in result:
            return 1
        raise cr50Error("Invalid value for recbtnforce")

    def _Set_rec_btn_force(self, value):
        """1 use recbtn command to press the recovery button. 0 release recbtn."""
        try:
            result = None
            if value:
                result = self._issue_cmd_get_results(
                    "recbtnforce enable", ["forced pressed"]
                )
            else:
                result = self._issue_cmd_get_results(
                    "recbtnforce disable", ["not pressed"]
                )
            if result is None:
                raise cr50Error("recbtnforce failed, Check GscFullConsole perm.")
        except pty_driver.PtyError as e:
            raise cr50Error("Unable to change recbtnforce status!") from e

    def _Get_rec_mode(self):
        """Return 1 if rec_mode is asserted. 0 if it's deasserted"""
        result = self._issue_cmd_get_results(
            "gpioget CCD_REC_LID_SWITCH", [r"\s+([01])\*?\s+CCD_REC_LID_SWITCH"]
        )
        gpio_state = int(result[0][1])
        recbtnforce = self._Get_rec_btn_force()
        # CCD_REC_LID_SWITCH is active low, so it should be the inverse of
        # recbtnforce.
        if gpio_state == recbtnforce:
            raise cr50Error(
                "recbtnforce (%s) and CCD_REC_LID_SWITCH (%sasserted) "
                "don't match!"
                % ("pressed" if recbtnforce else "released", "de" if gpio_state else "")
            )
        return gpio_state

    def _Set_rec_mode(self, value):
        self._issue_cmd("gpioset CCD_REC_LID_SWITCH %d" % value)
        self._Set_rec_btn_force(value == 0)
