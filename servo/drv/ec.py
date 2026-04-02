# Copyright 2012 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for board config controls of type=ec.

Provides the following EC controlled function:
  lid_open
  kbd_en
  kbd_m1_a0
  kbd_m1_a1
  kbd_m2_a0
  kbd_m2_a1
  dev_mode (Temporary. See crosbug.com/p/9341)
"""
import logging
import re
import time
import typing

from servo.drv import pty_driver
from servo.utils.retry_util import retry_hardware


KEY_STATE = [0, 1, 1, 1, 1]

# Key matrix row and column mapped from kbd_m*_a*
KEY_MATRIX = [[[(0, 4), (11, 4)], [(2, 4), None]], [[(0, 2), (11, 2)], [(2, 2), None]]]

# EC console mask for enabling only command channel
COMMAND_CHANNEL_MASK = 0x1

# EC PD Flags
PD_FLAGS_EXPLICIT_CONTRACT = 1 << 6
PD_FLAGS_TS_DTS_PARTNER = 1 << 16
PE_FLAGS_EXPLICIT_CONTRACT = 1 << 9
TC_FLAGS_TS_DTS_PARTNER = 1 << 1
TC_FLAGS_PARTNER_PD_CAPABLE = 1 << 12


class ecError(pty_driver.PtyError):
    """Exception class for ec."""


class ec(pty_driver.PtyDriver):
    """Object to access drv=ec controls.

    Note, instances of this object get dispatched via base class,
    HwDriver's get/set method. That method ultimately calls:
      "_[GS]et_%s" % params['subtype'] below.

    For example, a control to read kbd_en would be dispatched to
    call _Get_kbd_en.
    """

    def _drv_init(self):
        """Driver specific initializer."""
        super()._drv_init()

        self._has_chan = self._interface._uart_state.get("has_chan", True)
        self._role_swap_delay = float(self._params.get("role_swap_delay", 1.0))
        # Add locals to the values dictionary.
        if "kbd" not in self._interface._uart_state:
            self._interface._uart_state["kbd"] = list(KEY_STATE)

    def _limit_channel(self):
        """Save the current console channel setting and limit the output to the
        command channel (only print output from commands issued on console).

        Raises:
          ecError: when failing to retrieve channel settings
        """
        if not self._has_chan:
            return
        self._issue_cmd("chan save")
        self._issue_cmd("chan %d" % COMMAND_CHANNEL_MASK)

    def _restore_channel(self):
        """Load saved channel setting"""
        if not self._has_chan:
            return
        self._issue_cmd("chan restore")

    def _set_key_pressed(self, key_rc, pressed):
        """Press/release a key.

        Args:
          key_rc: Tuple containing row and column of the key.
          pressed: 0=release, 1=press.
        """
        if key_rc is None:
            return
        self._issue_cmd("kbpress %d %d %d" % (key_rc + (pressed,)))

    def _get_mx_ax_index(self, m, a):
        """Get the index of a kbd_mx_ax control.

        Args:
          m: Selection of kbd_m1 or kbd_m2. Note the value is 0/1, not 1/2.
          a: Selection of a0 and a1.
        """
        return m * 2 + a + 1

    def _set_both_keys(self, pressed):
        """Press/release both simulated key.

        Args:
          pressed: 0=release, 1=press.
        """
        m1_a0, m1_a1, m2_a0, m2_a1 = self._interface._uart_state["kbd"][1:5]
        self._set_key_pressed(KEY_MATRIX[1][m2_a0][m2_a1], pressed)
        self._set_key_pressed(KEY_MATRIX[0][m1_a0][m1_a1], pressed)

    def _Set_kbd_en(self, value):
        """Enable/disable keypress simulation."""

        org_value = self._interface._uart_state["kbd"][0]
        if org_value == 0 and value == 1:
            self._set_both_keys(pressed=1)
        elif org_value == 1 and value == 0:
            self._set_both_keys(pressed=0)
        self._interface._uart_state["kbd"][0] = value

    def _Get_kbd_en(self):
        """Retrieve keypress simulation enabled/disabled.

        Returns:
          0: Keyboard emulation is disabled.
          1: Keyboard emulation is enabled.
        """
        return self._interface._uart_state["kbd"][0]

    def _Set_kbd_mx_ax(self, m, a, value):
        """Implementation of _Set_kbd_m*_a*

        Args:
          m: Selection of kbd_m1 or kbd_m2. Note the value is 0/1, not 1/2.
          a: Selection of a0 and a1.
          value: The new value to set.
        """

        org_value = self._interface._uart_state["kbd"][self._get_mx_ax_index(m, a)]
        if self._Get_kbd_en() == 1 and org_value != value:
            org_value = [
                self._interface._uart_state["kbd"][self._get_mx_ax_index(m, 0)],
                self._interface._uart_state["kbd"][self._get_mx_ax_index(m, 1)],
            ]
            new_value = list(org_value)
            new_value[a] = value
            self._set_key_pressed(KEY_MATRIX[m][org_value[0]][org_value[1]], 0)
            self._set_key_pressed(KEY_MATRIX[m][new_value[0]][new_value[1]], 1)
        self._interface._uart_state["kbd"][self._get_mx_ax_index(m, a)] = value

    def _Set_kbd_m1_a0(self, value):
        """Setter of kbd_m1_a0."""
        self._Set_kbd_mx_ax(0, 0, value)

    def _Get_kbd_m1_a0(self):
        """Getter of kbd_m1_a0."""
        return self._interface._uart_state["kbd"][self._get_mx_ax_index(0, 0)]

    def _Set_kbd_m1_a1(self, value):
        """Setter of kbd_m1_a1."""
        self._Set_kbd_mx_ax(0, 1, value)

    def _Get_kbd_m1_a1(self):
        """Getter of kbd_m1_a1."""
        return self._interface._uart_state["kbd"][self._get_mx_ax_index(0, 1)]

    def _Set_kbd_m2_a0(self, value):
        """Setter of kbd_m2_a0."""
        self._Set_kbd_mx_ax(1, 0, value)

    def _Get_kbd_m2_a0(self):
        """Getter of kbd_m2_a0."""
        return self._interface._uart_state["kbd"][self._get_mx_ax_index(1, 0)]

    def _Set_kbd_m2_a1(self, value):
        """Setter of kbd_m2_a1."""
        self._Set_kbd_mx_ax(1, 1, value)

    def _Get_kbd_m2_a1(self):
        """Getter of kbd_m2_a1."""
        return self._interface._uart_state["kbd"][self._get_mx_ax_index(1, 1)]

    def _Set_lid_open(self, value):
        """Setter of lid_open.

        Args:
          value: 0=lid closed, 1=lid opened.
        """
        if value == 0:
            self._issue_cmd("lidclose")
        else:
            self._issue_cmd("lidopen")

    def _Get_volume_up(self):
        """Getter of Volup for Ryu"""
        result = self._issue_cmd_get_results(
            "btnpress volup", [r"Button volup pressed = (\d+)"]
        )[0]
        return int(result[1])

    def _Set_volume_up(self, value):
        """Setter of Volup for Ryu

        Args:
          value: 1=button pressed, 0=button released
        """
        self._issue_cmd("btnpress volup %d" % int(value))

    def _Get_volume_down(self):
        """Getter of Voldown for Ryu"""
        result = self._issue_cmd_get_results(
            "btnpress voldown", [r"Button voldown pressed = (\d+)"]
        )[0]
        return int(result[1])

    def _Set_volume_down(self, value):
        """Setter of Voldown for Ryu

        Args:
          value: 1=button pressed, 0=button released
        """
        self._issue_cmd("btnpress voldown %d" % int(value))

    def _Set_button_hold(self, value):
        """Setter for a button hold on the ec.

        'pwrbtn' or button for tablets/detachables.

        Args:
          value: number of ms to hold the volume button. Has to be at least 1.
        """
        if value < 1:
            self._logger.error(
                "Trying to set ec button press to %d ms. Overwriting "
                "the value to be 1ms.",
                value,
            )
            value = 1
        # One of 'button' or 'powerbtn'
        cmd = self._params.get("ec_cmd")
        # 'button' cmd requires vup|vdown or both while 'powerbtn' requires
        # no args.
        argline = self._params.get("ec_args", "")
        ec_cmd = "%s %s %d" % (cmd, argline, value)
        self._issue_cmd(ec_cmd)
        # Issuing a console command is async. Wait the button release.
        time.sleep(value / 1000.0)

    def _Get_warm_reset(self):
        """Getter of warm_reset (active low).

        Query the power sequence state. Return the value as if it is the legacy
        servo warm_reset pin.

        Returns:
          0: warm_reset on.
          1: warm_reset off.
        """
        self._limit_channel()
        try:
            result = self._issue_cmd_get_results(
                "powerinfo", ["power state [0-9]* = (.*),"]
            )[0][1]
            if "S0" in result or "S3" in result:
                return 1
        except pty_driver.PtyError:
            # If EC UART has no respond, treat it as warm_reset on.
            pass
        finally:
            self._restore_channel()
        return 0

    def _Set_warm_reset(self, value):
        """Setter of warm_reset (active low).

        Use the power sequence to emulate the legacy servo warm_reset pin.
        The servo warm_reset pin is active low.

        Args:
          value: 0=on  -> power off the AP
                 1=off -> power on the AP
        """
        if value == 0:
            self._issue_cmd("power off")
        else:
            self._issue_cmd("power on")

    @retry_hardware(exceptions=pty_driver.PtyError)
    def _Get_milliwatts(self):
        """Retrieves power measurements for the battery.

        Battery command in the EC currently exposes the following information:
           Temp:      0x0be1 = 304.1 K (31.0 C)
           Manuf:     SUNWODA
           Device:    S1
           Chem:      LION
           Serial:    0x0000
           V:         0x1ef7 = 7927 mV
           V-desired: 0x20d0 = 8400 mV
           V-design:  0x1ce8 = 7400 mV
           I:         0x06a9 = 1705 mA(CHG)
           I-desired: 0x06a4 = 1700 mA
           Mode:      0x7f01
           Charge:    66 %
             Abs:     65 %
           Remaining: 5489 mAh
           Cap-full:  8358 mAh
             Design:  8500 mAh
           Time-full: 2h:47
             Empty:   0h:0

        This method currently returns a subset of above.

        Returns:
          Dictionary where:
            mv: battery voltage in millivolts
            ma: battery amps in milliamps
            mw: battery power in milliwatts
        """
        # The uart often drops some of the output of the battery cmd.
        self._limit_channel()
        results = self._issue_cmd_get_results(
            "battery",
            [r"V:[\s0-9a-fx]*= (-*\d+) mV", r"I:[\s0-9a-fx]*= (-*\d+) mA"],
        )
        self._restore_channel()
        result = {"mv": int(results[0][1], 0), "ma": int(results[1][1], 0) * -1}
        return result["ma"] * result["mv"] / 1000.0

    def _Set_fan_target_rpm(self, value):
        """Set target fan RPM.

        This function sets target fan RPM or turns on auto fan control.

        Args:
          value: Non-negative values for target fan RPM. -1 is treated as maximum
            fan speed. -2 is treated as auto fan speed control.
        """
        if value == -2:
            self._issue_cmd("autofan")
        else:
            # "-1" is treated as max fan RPM in EC, so we don't need to handle that
            self._issue_cmd("fanset %d" % value)

    def _Get_feat(self):  # pylint: disable=invalid-name
        """Retrieves the EC feature flags encoded as a hexadecimal."""
        self._limit_channel()
        try:
            result = self._issue_cmd_get_results(
                "feat",
                [
                    r"Command 'feat' not found or ambiguous\.|"
                    r"0-31: (0x[0-9a-f]{8})\s*32-63: (0x[0-9a-f]{8})"
                ],
            )
        except pty_driver.PtyError:
            raise ecError("Cannot retrieve the feature flags on EC console.")
        finally:
            self._restore_channel()
        if result[0] == "Command 'feat' not found or ambiguous.":
            return "0x0"
        return hex((int(result[0][2], 16) << 32) | int(result[0][1], 16))

    def _read_port_role(self, p: int) -> typing.Tuple[str, int]:
        """Reads the PD state.

        The returned confidence score is to detect which port the servo is attached.
        The port with the highest score is likely to be the servo.

        Args:
          p: The port to read

        Returns: the tuple (data role, confidence score)
        """
        pd_state_cmd = "pd %d state"
        if self._params.get("pdc") == "yes":
            pd_state_cmd = "pdc status %d"

        result = self._issue_cmd_get_results(
            pd_state_cmd % p,
            [
                r"Invalid port|Parameter 2 invalid|Role: ([A-Z]+)-([A-Z]+)(-\S*)? (.*)\n",
            ],
            flush=True,
        )
        # TC Flags should always be present on TPMCv2
        tc_flags = 0
        pe_flags = 0
        v1_flags = 0
        m = re.match(r"TC State: \S* Flags: (0x\S+)", result[0][4])
        if m:
            tc_flags = int(m.group(1), 16)
            # PE Flags are only sometimes present
            m = re.match(r".*PE State: \S* Flags: (0x\S+)", result[0][4])
            if m:
                pe_flags = int(m.group(1), 16)
        else:
            # If no TC Flags, must be TPMCv1
            m = re.match(r".*Flags: (0x\S+)", result[0][4])
            if m:
                v1_flags = int(m.group(1), 16)
        if result[0] == "Parameter 2 invalid" or result[0] == "Invalid port":
            logging.warning(
                "Model doesn't have %d USB-C ports, please edit dut_pd_data_role "
                "port_count in the board overlay.xml file",
                p + 1,
            )
            return "", -1
        confidence = 0
        logging.debug(
            "role=%s tc_flags=%x pe_flags=%x v1_flags=%x",
            result[0][2],
            tc_flags,
            pe_flags,
            v1_flags,
        )
        # Servo usually has DTS enabled, the cc command can enable or disable it.
        if tc_flags & TC_FLAGS_TS_DTS_PARTNER or v1_flags & PD_FLAGS_TS_DTS_PARTNER:
            confidence += 1
        # Servo in src mode will have explicit contract
        if (
            tc_flags & TC_FLAGS_PARTNER_PD_CAPABLE
            or pe_flags & PE_FLAGS_EXPLICIT_CONTRACT
            or v1_flags & PD_FLAGS_EXPLICIT_CONTRACT
        ):
            confidence += 1
        return result[0][2], confidence

    def _find_servo_port(self) -> typing.Tuple[int, str]:
        """Find the USB-C port that has something (presumable servo) attached.

        Returns: the tuple (port number, data role)
        """
        port_count = int(self._params.get("port_count"))
        best_port = None
        best_score = -1
        best_role = None
        for p in range(port_count):
            role, confidence = self._read_port_role(p)
            if confidence > best_score:
                best_score = confidence
                best_port = p
                best_role = role
        if best_role:
            logging.debug("Assuming servo is on port %d role=%s", best_port, best_role)
            return best_port, best_role
        raise ecError("Could not find any connected USB-C port.")

    def _Get_dut_pd_data_role(self) -> str:
        self._limit_channel()
        try:
            port, role = self._find_servo_port()
            return role
        finally:
            self._restore_channel()

    def _Set_dut_pd_data_role(self, value: str) -> None:
        value = value.upper()
        if value not in ["DFP", "UFP"]:
            raise ValueError("Bad data role (%s). Try 'DFP' or 'UFP'." % value)

        self._limit_channel()
        try:
            port, role = self._find_servo_port()
            if role == value:
                return
            pd_role_swap_cmd = "pd %d swap data"
            if self._params.get("pdc") == "yes":
                pd_role_swap_cmd = "pdc drs %d"
            self._issue_cmd(pd_role_swap_cmd % port)
            time.sleep(self._role_swap_delay)
            role, _unused = self._read_port_role(port)
            if role != value:
                raise ecError(
                    "Failed to set port %d to PD role %s, got: %s" % (port, value, role)
                )
        finally:
            self._restore_channel()

    def _Set_pdc_ccd_keepalive_en(self, value: int) -> None:
        """Setter for pdc_ccd_keepalive_en

        Input value:
         0 for normal mux operation
         1 to force the SBU mux into debug (CCD forced on). Needed in conjunction with
           GSC's rddkeepalive for DUTs using PDC-driven CCD."""

        if value == 0:
            cmd = "pdc sbumux normal"
        elif value == 1:
            cmd = "pdc sbumux debug"
        else:
            raise ValueError("Value must be 0 or 1")

        try:
            self._issue_cmd(cmd)
        except pty_driver.PtyError as e:
            raise ecError(
                f"Cannot run `{cmd}`. Is this a DUT with PDC-driven CCD? "
                "(CONFIG_USBC_PDC_DRIVEN_CCD)"
            ) from e

    def _Get_pdc_ccd_keepalive_en(self) -> int:
        """Getter for pdc_ccd_keepalive_en

        Returns:
         0 for normal operation
         1 when SBU mux is forced into debug (CCD forced on)"""

        cmd = "pdc sbumux"

        try:
            results = self._issue_cmd_get_results(
                cmd, [r"CCD Port: C\d+, Mode: (\w+) \(\d+\)"]
            )
        except pty_driver.PtyError as e:
            raise ecError(
                f"Cannot run `{cmd}`. Is this a DUT with PDC-driven CCD? "
                "(CONFIG_USBC_PDC_DRIVEN_CCD)"
            ) from e

        if results[0][1] == "NORMAL":
            return 0
        elif results[0][1] == "FORCE_DEBUG":
            return 1
        else:
            raise ecError(f"Unexpected `{cmd}` output: '{results[0][0]}'")
