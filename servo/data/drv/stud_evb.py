# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for board config controls stud_evb board (i2c mux & ioexes)."""

import copy
import re
import time

from servo.data.drv import hw_driver
from servo.data.drv import pi4ioe5
from servo.data.drv import pi4msd


class StudEvbError(hw_driver.HwDriverError):
    """Error occurred accessing StudEvb controls"""


class studEvb(hw_driver.HwDriver):
    # Special pins definitions
    BOARD_ID_PINS = [
        "STUD_EVB_LEGO_ADDR_0_R",
        "STUD_EVB_LEGO_ADDR_1_R",
        "STUD_EVB_LEGO_ADDR_2_R",
        "STUD_EVB_LEGO_ADDR_0_1M",
        "STUD_EVB_LEGO_ADDR_1_1M",
        "STUD_EVB_LEGO_ADDR_2_1M",
    ]
    FB_PPVAR_PINS = ["STUD_EVB_FB_PPVAR_SYS_0", "STUD_EVB_FB_PPVAR_SYS_1"]
    LEGO_RST_PIN = ["STUD_EVB_LEGO_RST_ODL"]

    # LEGO_RST pin credentials
    LEGO_RST_PIN_OFFSET = 0
    LEGO_RST_PIN_PORT = 2
    LEGO_RST_PIN_IOEX_I2C_ADDR = 0x21

    def __init__(self, interface, params):
        """Constructor

        Args:
          interface: FTDI interface object to handle low-level communication to
              control or the servo_server.Servod for a whole_bank subtype
          params: dictionary of params (k=v pairs) needed to perform operations on a driver
          servod: Servod that is used for cross-servo-device communication

        Attributes:
          i2c_mux: Pi4Msd instance to talk to on-board i2c muxer
          ioex: Pi4Ioe5 instance to talk to on-board ioexpander
        """
        super(studEvb, self).__init__(interface, params)
        if "subtype" in self._params:
            # Below controls only use control names, so no direct access to i2c
            # interface required
            if self._params["subtype"] in [
                "whole_bank",
                "all_base_pins",
                "all_brick_pins",
            ]:
                self.i2c_mux = None
                self.ioex = None
                return
        self.i2c_mux = pi4msd.pi4Msd(interface, params)
        self.ioex = pi4ioe5.pi4Ioe5(interface, params)

    def _get(self):
        """Get level and flags of particular stud_evb pin

        1. Store current mux configuration
        2. Set muxer properly if necessary
        3. Send command to ioex
        4. Restore muxer settings
        """
        mux_reg = self.i2c_mux._get()
        self.i2c_mux._set(1)
        retval = self.ioex._get()
        self.i2c_mux._set(1, mux_reg)
        return retval

    def _set(self, fmt_value):
        """Set value and configure ioexpander pin

        Args:
          fmt_value: see _help_msg_for_set() within pi4ioe5.py module for description.
        """
        if self._apply_pins_restrictions(fmt_value):
            return
        self.i2c_mux._set(1)
        return self.ioex._set(fmt_value)

    def _board_id_setter_help(self):
        description = """Incorrect arguments.

    For BOARD_ID pins value to be set is comma-separated value string with:
      1. integers (0/1) corresponding to output pin values
      2. 'I'/'O' - direction to be configured
      3. 'PP' - as BOARD_ID pins can only be push-pull outputs
      4. 'force' flag - REQUIRED to ensure that user set LEGO_ADDR physical
         switches to position "5"(NC).

    Caller has three options:
      a) item 1 + 'force'
      b) 'I' + 'force'
      c) 'O' + 'PP' + item 1 + 'force'

    Examples:
    1. Set board ID pin to input:
    "I,force"
    2. Set board ID pin to high-level output:
    "O,PP,1,force"
    3. Set board ID pin to low-level output:
    "0,force"
    """
        return description

    def _apply_board_id_restrictions(self, args):
        """BOARD_ID pins on EVB requires extra handling:
          1. LEGO_ADDR pins can only be set as HIGH/LOW outputs or Hi-Z inputs
          2. Only allow one of LEGO_ADDR_[0:2]_R or LEGO_ADDR_[0:2]_1M to be set.
             If LEGO_ADDR_[0:2]_R is set to output, LEGO_ADDR_[0:2]_1M is set as
             Hi-Z input

        Args:
          args: Table of command line options provided by the caller
        """
        # List of tuples with correlated pins represented as their credentials on
        # the ioex - (port_number,pin_number).
        board_id_pins = [
            ((2, 5), (3, 0)),  # LEGO_ADDR_0_[R|M]
            ((2, 6), (3, 1)),  # LEGO_ADDR_1_[R|M]
            ((2, 7), (3, 2)),
        ]  # LEGO_ADDR_2_[R|M]

        if "force" not in args:
            raise StudEvbError(
                'Please provide "force" argument in order to proceed\n'
                + self._board_id_setter_help()
            )
        else:
            self._logger.warning(
                'force flag provided, assuming that LEGO_ADDR physical switches are set to position "5"(NC).'
            )

        # Remove "force" flag as it is not needed for lower level drivers
        args.remove("force")

        digit = False
        for idx, i in enumerate(args):
            if i.isdigit():
                digit = True
                int_idx = idx
                break

        if len(args) != 1 and len(args) != 3:
            raise StudEvbError(self._board_id_setter_help())

        # Hi-Z input - just continue without extra handling
        if len(args) == 1 and "I" in args:
            return

        # Case with setting to output e.g. "O,1,PP" or just "0"/"1"
        # We are allowing only PP output
        if len(args) == 3:
            if "O" not in args or "PP" not in args or not digit:
                raise StudEvbError(self._board_id_setter_help())

        if len(args) == 1 and not digit:
            raise StudEvbError(self._board_id_setter_help())

        if int(args[int_idx]) not in (0, 1):
            raise StudEvbError(self._board_id_setter_help())

        this_pin = (int(self._params["port"]), int(self._params["offset"]))

        # Find a buddy
        for buddies in board_id_pins:
            for pin in [0, 1]:
                if this_pin == buddies[pin]:
                    buddy_pin = buddies[1 - pin]

        # Create ioex object for buddy
        board_id_params = copy.copy(self._params)
        board_id_params["port"] = str(buddy_pin[0])
        board_id_params["offset"] = str(buddy_pin[1])
        board_id_ioex = pi4ioe5.pi4Ioe5(self._interface, board_id_params)

        # Pins and their buddies are on the same ioex, so i2c_mux credentials are
        # the same as for original pin, thus can use object instantiated in
        # constructor
        self.i2c_mux._set(1)

        # Configure buddy pin to Hi-Z input
        board_id_ioex._set("I")

        # Configure original pin to desired value
        fmt_value = ",".join(args)
        self.ioex._set(fmt_value)

    def _fb_ppvar_setter_help(self):
        description = """Incorrect arguments.

    For FB_PPVAR_SYS[0:1] pins value to be set is comma-separated value string with:
      1. integers - '0' as FB_PPVAR may only byi set to LOW level when output
      2. 'I'/'O' - direction to be configured
      3. 'PP' - as BOARD_ID pins can only be push-pull outputs
      4. 'force' flag - REQUIRED to ensure that user is aware LEGO_RST pin
         status will be modified during the procedure.

    Caller has three options:
      a) '0' + 'force'
      b) 'I' + 'force'
      c) 'O' + 'PP' + item 1 + 'force'

    Examples:
    1. Set FB_PPVAR_SYS[0:1] pin to input:
    "I,force"
    2. Set FB_PPVAR_SYS[0:1] pin to low-level output:
    "O,PP,0,force"
    3. Shorter version:
    "0,force"
    """
        return description

    def _apply_fb_ppvar_restrictions(self, args):
        """FB_PPVAR_SYS_[0:1] pins on EVB requires extra handling:
          1. Before a FB_PPVPAR_SYS_[0:1] pin state is changed, LEGO_RST must be
             set as an output LOW.
          2. LEGO_RST will change to a Hi-Z input with a delay after FB_PPVAR_SYS
             pin is changed.
          3. FB_PVPAR_SYS pins can only be set as Hi-Z inputs or LOW outputs.

        Args:
          args: Table of command line options provided by the caller
        """
        if "force" not in args:
            raise StudEvbError(
                'Please provide "force" argument in order to proceed\n'
                + self._fb_ppvar_setter_help()
            )
        else:
            self._logger.warning(
                "LEGO_RST will assert to allow for PPVAR_SYS voltage changes to take effect."
            )

        # Remove "force" flag as it is not needed for lower level drivers
        args.remove("force")

        digit = False
        for idx, i in enumerate(args):
            if i.isdigit():
                digit = True
                int_idx = idx
                break

        if len(args) != 1 and len(args) != 3:
            raise StudEvbError(self._fb_ppvar_setter_help())

        if len(args) == 1 and digit:
            if int(args[int_idx]) != 0:
                raise StudEvbError(self._fb_ppvar_setter_help())
        elif len(args) == 1 and "I" not in args:
            raise StudEvbError(self._fb_ppvar_setter_help())

        # Case with setting to output "O,0,PP"
        if len(args) == 3:
            if "O" not in args or "PP" not in args or not digit:
                raise StudEvbError(self._fb_ppvar_setter_help())

            if int(args[int_idx]) != 0:
                raise StudEvbError(self._fb_ppvar_setter_help())

        # Create ioex object for LEGO_RST pin
        lego_rst_params = copy.copy(self._params)
        lego_rst_params["offset"] = str(self.LEGO_RST_PIN_OFFSET)
        lego_rst_params["port"] = str(self.LEGO_RST_PIN_PORT)
        lego_rst_params["child"] = str(self.LEGO_RST_PIN_IOEX_I2C_ADDR)
        lego_rst_ioex = pi4ioe5.pi4Ioe5(self._interface, lego_rst_params)

        # FB_PPVAR_SYS[0:1] and LEGO_RST are placed on the same I2C bus, so i2c_mux
        # credentials are the same as for original pin, thus can use object
        # instantiated in constructor
        self.i2c_mux._set(1)

        # Configure LEGO_RST as PP output with low level
        lego_rst_ioex._set("0")

        # Set desired FB_PPVAR_SYS pin value
        fmt_value = ",".join(args)
        self.ioex._set(fmt_value)
        time.sleep(0.5)

        # Configure LEGO_RST as hi-z input
        lego_rst_ioex._set("I")

    def _lego_rst_setter_help(self):
        description = """Incorrect arguments.

    For LEGO_RST_ODL pin value to be set is comma-separated value string with:
      1. integers - '0' as LEGO_RST_ODL may only by set to LOW level when output
      2. 'I'/'O' - direction to be configured
      3. 'PP' - as BOARD_ID pins can only be push-pull outputs
      4. 'force' flag - REQUIRED to ensure that user is aware LEGO_RST_ODL pin
         status will be modified during the procedure.

    Caller has three options:
      a) '0' + 'force'
      b) 'I' + 'force'
      c) 'O' + 'PP' + '0' + 'force'

    Examples:
    1. Set LEGO_RST_ODL pin to input:
    "I,force"
    2. Set LEGO_RST_ODL pin to low-level output:
    "O,PP,0,force"
    3. Shorter version:
    "0,force"
    """
        return description

    def _apply_lego_rst_pin_restrictions(self, args):
        """LEGO_RST_ODL pin on EVB requires extra handling:
          1. LEGO_RST_ODL pin can only be set as Hi-Z input or LOW output.

        Args:
          args: Table of command line options provided by the caller
        """
        if "force" not in args:
            raise StudEvbError(
                'Please provide "force" argument in order to proceed\n'
                + self._lego_rst_setter_help()
            )
        else:
            self._logger.warning("force flag provided, LEGO_RST_ODL can be changed.")

        # Remove "force" flag as it is not needed for lower level drivers
        args.remove("force")

        digit = False
        for idx, i in enumerate(args):
            if i.isdigit():
                digit = True
                int_idx = idx
                break

        if len(args) != 1 and len(args) != 3:
            raise StudEvbError(self._lego_rst_setter_help())

        if len(args) == 1 and digit:
            if int(args[int_idx]) != 0:
                raise StudEvbError(self._lego_rst_setter_help())
        elif len(args) == 1 and "I" not in args:
            raise StudEvbError(self._lego_rst_setter_help())

        # Case with setting to output "O,0,PP"
        if len(args) == 3:
            if "O" not in args or "PP" not in args or not digit:
                raise StudEvbError(self._lego_rst_setter_help())

            if int(args[int_idx]) != 0:
                raise StudEvbError(self._lego_rst_setter_help())

        self.i2c_mux._set(1)
        self.ioex._set(",".join(args))

    def _apply_pins_restrictions(self, fmt_value):
        """Some pins' configurations on stud EVB are invalid and we need to protect
        user from setting those. Some other options require manual actions from the
        user and we should also require to have an extra "force" flag to be set in
        such case, so that we are sure user is aware of the fact.

        Args:
          fmt_value: see _help_msg_for_set() within pi4ioe5.py module for description.

        Returns:
          True: All pin operations are completed, caller may return
          False: Only specific part of a sequence are done, caller should continue
                 normal execution
        """
        args = fmt_value.split(",")

        if self._params["control_name"] in self.BOARD_ID_PINS:
            self._apply_board_id_restrictions(args)
            return True
        elif self._params["control_name"] in self.FB_PPVAR_PINS:
            self._apply_fb_ppvar_restrictions(args)
            return True
        elif self._params["control_name"] in self.LEGO_RST_PIN:
            self._apply_lego_rst_pin_restrictions(args)
            return True

        # Warn user that force flag is being set even though it is not required.
        if "force" in args:
            raise StudEvbError(
                'Please not set "force" flag if not playing with '
                "special pins (See EVB user guide)"
            )
        return False

    def _Set_whole_ioex(self, fmt_value):
        """Set value and configure all ioexpander pins

        Args:
          fmt_value: see _help_msg_for_set() within pi4ioe5.py module for description.
        """
        self.i2c_mux._set(1)
        self.ioex._Set_whole_ioex(fmt_value)

    def _Get_whole_ioex(self):
        """Get levels of all pins in particular ioex"""
        mux_reg = self.i2c_mux._get()
        self.i2c_mux._set(1)
        retval = self.ioex._Get_whole_ioex()
        self.i2c_mux._set(1, mux_reg)
        return retval

    def _get_bank_params(self):
        """Helper to get bank information from params. It returns bank type and name

        Return:
          bank_data: Tuple (bank_type, bank_str)
        """
        if "bank_type" not in self._params or "bank_str" not in self._params:
            raise StudEvbError("getting bank_type and bank_str")

        bank_type = self._params["bank_type"]
        bank_str = self._params["bank_str"]

        return (bank_type, bank_str)

    def _get_bank_pin_controls(self, bank_type, bank_str):
        """Helper to get all pin control names in particular bank

        Args:
          bank_type: Bank type string (BASE or BRICK)
          bank_str: Bank name string (A, B, C or D)

        Returns:
          Pins: list of strings which pin controls names:
            ["STUD_EVB_<bank_type>_IO_<bank_str>0", "STUD_EVB_<bank_type>_IO_<bank_str>1",
            ..., "STUD_EVB_<bank_type>_IO_<bank_str>9"]
        """
        return ["STUD_EVB_" + bank_type + "_IO_" + bank_str + str(i) for i in range(10)]

    def _Get_whole_bank(self):
        """Subtype function to handle get() invocation on BANK controls. Each bank
        consist of 10 pins grouped together in 1 ioex on Lego EVB.

        Returns:
          Pins: list of strings with pins configuration, one line for each pin:
            <BASE|BRICK><_BANK_><A..D><0..9>:<gpio_state>,<I | O>,<N/PU/PD | PP/OD>
        """
        bank_type, bank_str = self._get_bank_params()
        pin_controls = self._get_bank_pin_controls(bank_type, bank_str)
        retval = ""
        for control in pin_controls:
            # Get pin number from last char in control name
            pin = control[-1]
            retval += "%s_BANK_%s%s:" % (bank_type, bank_str, pin)
            retval += self._servod_get(control)
            retval += "\n"

        return retval

    def _Set_whole_bank(self, fmt_value):
        """Subtype function to handle set() invocation on BANK controls. Each bank
        consist of 10 pins grouped together in 1 ioex on Lego EVB.
        """
        bank_type, bank_str = self._get_bank_params()
        pin_controls = self._get_bank_pin_controls(bank_type, bank_str)
        for control in pin_controls:
            self._servod_set(control, fmt_value)

    def _find_matching_pin(self, port, pin, ioex_addr, base_pins=True):
        """Iterate through controls marked with 'stud_evb_io' tag and return name of
        the pin with matching ioex i2c address, ioex port and pin within this port.

        Args:
          port: Number of IOEX port to be mapped
          pin: Number of pin within IOEX port to be mapped
          ioex_addr: i2c address of IOEX where particular pin should be found
          base_pins: If True check only BASE controls, BRICK controls otherwise

        Returns:
          pin_name: String with letter of bank and pin number within this bank, None
          if not found
        """
        for control_name in self.servod.get_controls_for_tag("stud_evb_io"):
            if base_pins:
                matching_str = "STUD_EVB_BASE_IO_[A-D][0-9]"
            else:
                matching_str = "STUD_EVB_BRICK_IO_[A-D][0-9]"
            if not re.match(matching_str, control_name):
                continue

            # Find a control with particular pin/port/i2c_addr
            params, _unused, _unused = self.servod.get_main_device()._get_param_drv(
                control_name
            )
            if int(params.get("child"), base=16) != ioex_addr:
                continue

            if (int(params.get("offset")) == pin) and (int(params.get("port")) == port):
                return re.findall("STUD_EVB_.*_IO_(.*)", control_name)[0]

    def _io_name_to_index(self, io_name):
        """Convert name of IO pin into index of BASE/BRICK list of pins

        Args:
          io_name: Expect string in format <BANK_LETTER><PIN_NUMBER>

        Returns:
          index: Linear index of particular IO within BASE or BRICK pins table
        """
        return 10 * (ord(io_name[0]) - ord("A")) + int(io_name[1])

    def _fill_io_table_from_ioex(self, ioex_pins_table, ioex_str, ioex_addr, base_pins):
        """Fill linear list of BASE/BRICK pins levels based on the IOEX readings remapped
        to proper index from controls' params.

        Args:
          ioex_pins_table: List of pins' levels to be filled
          ioex_str: Return value from whole IOEX controls
          ioex_addr: i2c address of IOEX which is being read
          base_pins: If True check only BASE controls, BRICK controls otherwise
        """
        # Port value strings have format of "P<number>:Value\n"
        ioex_ports_str = ioex_str.splitlines()

        for port, port_str in enumerate(ioex_ports_str):
            port_value = int(re.search(":(.+)$", port_str).group(1))
            for pin in range(8):
                io_name = self._find_matching_pin(port, pin, ioex_addr, base_pins)
                if io_name:
                    ioex_pins_table[self._io_name_to_index(io_name)] = (
                        port_value & (1 << pin)
                    ) >> pin

    def _Get_all_base_pins(self):
        """Get all BASE_IO_* pins from stud EVB. Return them in form of a list with
        level of each pin.
        """
        ioex_pins_table = [0] * 40
        ioex_control = "STUD_EVB_IOEX_0"
        ioex_string = self._servod_get(ioex_control)
        self._fill_io_table_from_ioex(
            ioex_pins_table, ioex_string, 0x21, base_pins=True
        )

        ioex_control = "STUD_EVB_IOEX_1"
        ioex_string = self._servod_get(ioex_control)
        self._fill_io_table_from_ioex(
            ioex_pins_table, ioex_string, 0x23, base_pins=True
        )
        return " ".join(str(e) for e in ioex_pins_table)

    def _Set_all_base_pins(self, fmt_value):
        """Set all BASE_IO_* pins from stud EVB."""
        control_name = "STUD_EVB_IOEX_0"
        self._servod_set(control_name, fmt_value)
        control_name = "STUD_EVB_BASE_BANK_D"
        self._servod_set(control_name, fmt_value)

    def _Get_all_brick_pins(self):
        """Get all BRICK_IO_* pins from stud EVB. Return them in form of a list with
        level of each pin.
        """
        ioex_pins_table = [0] * 40
        ioex_control = "STUD_EVB_IOEX_2"
        ioex_string = self._servod_get(ioex_control)
        self._fill_io_table_from_ioex(
            ioex_pins_table, ioex_string, 0x22, base_pins=False
        )

        ioex_control = "STUD_EVB_IOEX_1"
        ioex_string = self._servod_get(ioex_control)
        self._fill_io_table_from_ioex(
            ioex_pins_table, ioex_string, 0x23, base_pins=False
        )
        return " ".join(str(e) for e in ioex_pins_table)

    def _Set_all_brick_pins(self, fmt_value):
        """Set all BRICK_IO_* pins from stud EVB."""
        control_name = "STUD_EVB_IOEX_2"
        self._servod_set(control_name, fmt_value)
        control_name = "STUD_EVB_BRICK_BANK_D"
        self._servod_set(control_name, fmt_value)
