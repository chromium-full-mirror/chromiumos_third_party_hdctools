# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for board config controls stud_evb board (i2c mux & ioexes)."""

import copy
import time

from servo.drv import hw_driver
from servo.drv import pi4msd
from servo.drv import pi4ioe5

class StudEvbError(hw_driver.HwDriverError):
  """Error occured accessing StudEvb controls"""

class studEvb(hw_driver.HwDriver):

  # Special pins definitions
  BOARD_ID_PINS = ['STUD_EVB_LEGO_ADDR_0_R',
                   'STUD_EVB_LEGO_ADDR_1_R',
                   'STUD_EVB_LEGO_ADDR_2_R',
                   'STUD_EVB_LEGO_ADDR_0_1M',
                   'STUD_EVB_LEGO_ADDR_1_1M',
                   'STUD_EVB_LEGO_ADDR_2_1M']
  FB_PPVAR_PINS = ['STUD_EVB_FB_PPVAR_SYS_0',
                   'STUD_EVB_FB_PPVAR_SYS_1']

  # LEGO_RST pin credentials
  LEGO_RST_PIN_OFFSET = 0
  LEGO_RST_PIN_PORT = 2
  LEGO_RST_PIN_IOEX_I2C_ADDR = 0x21

  def __init__(self, interface, params):
    """Constructor

    Args:
      interface: FTDI interface object to handle low-level communication to
          control
      params: dictionary of params (k=v pairs) needed to perform operations on a driver

    Attributes:
      i2c_mux: Pi4Msd instance to talk to on-board i2c muxer
      ioex: Pi4Ioe5 instance to talk to on-board ioexpander
    """
    super(studEvb, self).__init__(interface, params)
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
    description ="""Incorrect arguments.

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
    board_id_pins = [((2,5),(3,0)), # LEGO_ADDR_0_[R|M]
                     ((2,6),(3,1)), # LEGO_ADDR_1_[R|M]
                     ((2,7),(3,2))] # LEGO_ADDR_2_[R|M]

    if 'force' not in args:
      raise StudEvbError('Please provide "force" argument in order to proceed\n' +
                           self._board_id_setter_help())
    else:
      self._logger.warning('force flag provided, assuming that LEGO_ADDR physical switches are set to position "5"(NC).')

    # Remove "force" flag as it is not needed for lower level drivers
    args.remove('force')

    digit = False
    for idx, i in enumerate(args):
      if i.isdigit():
        digit = True
        int_idx = idx
        break

    if len(args) != 1 and len(args) != 3:
      raise StudEvbError(self._board_id_setter_help())

    # Hi-Z input - just continue without extra handling
    if len(args) == 1 and 'I' in args:
      return

    # Case with setting to output e.g. "O,1,PP" or just "0"/"1"
    # We are allowing only PP output
    if len(args) == 3:
      if 'O' not in args or 'PP' not in args or not digit:
        raise StudEvbError(self._board_id_setter_help())

    if len(args) == 1 and not digit:
      raise StudEvbError(self._board_id_setter_help())

    if int(args[int_idx]) not in (0,1):
      raise StudEvbError(self._board_id_setter_help())

    this_pin = (int(self._params['port']), int(self._params['offset']))

    # Find a buddy
    for buddies in board_id_pins:
      for pin in [0,1]:
        if this_pin == buddies[pin]:
          buddy_pin = buddies[1 - pin]

    # Create ioex object for buddy
    board_id_params = copy.copy(self._params)
    board_id_params['port'] = str(buddy_pin[0])
    board_id_params['offset'] = str(buddy_pin[1])
    board_id_ioex = pi4ioe5.pi4Ioe5(self._interface, board_id_params)

    # Pins and their buddies are on the same ioex, so i2c_mux credentials are
    # the same as for original pin, thus can use object instantiated in
    # constructor
    self.i2c_mux._set(1)

    # Configure buddy pin to Hi-Z input
    board_id_ioex._set("I")

    # Configure original pin to desired value
    fmt_value = ','.join(args)
    self.ioex._set(fmt_value)

  def _fb_ppvar_setter_help(self):
    description ="""Incorrect arguments.

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
    if 'force' not in args:
      raise StudEvbError('Please provide "force" argument in order to proceed\n' +
                           self._fb_ppvar_setter_help())
    else:
      self._logger.warning('LEGO_RST will assert to allow for PPVAR_SYS voltage changes to take effect.')

    # Remove "force" flag as it is not needed for lower level drivers
    args.remove('force')

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
    elif len(args) == 1 and 'I' not in args:
        raise StudEvbError(self._fb_ppvar_setter_help())

    # Create ioex object for LEGO_RST pin
    lego_rst_params = copy.copy(self._params)
    lego_rst_params['offset'] = str(self.LEGO_RST_PIN_OFFSET)
    lego_rst_params['port'] = str(self.LEGO_RST_PIN_PORT)
    lego_rst_params['child'] = str(self.LEGO_RST_PIN_IOEX_I2C_ADDR)
    lego_rst_ioex = pi4ioe5.pi4Ioe5(self._interface, lego_rst_params)

    # FB_PPVAR_SYS[0:1] and LEGO_RST are placed on the same I2C bus, so i2c_mux
    # credentials are the same as for original pin, thus can use object
    # instantiated in constructor
    self.i2c_mux._set(1)

    # Configure LEGO_RST as PP output with low level
    lego_rst_ioex._set("0")

    # Set desired FB_PPVAR_SYS pin value
    fmt_value = ','.join(args)
    self.ioex._set(fmt_value)
    time.sleep(0.5)

    # Configure LEGO_RST as hi-z input
    lego_rst_ioex._set("I")

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
    args = fmt_value.split(',')

    if self._params['control_name'] in self.BOARD_ID_PINS:
      self._apply_board_id_restrictions(args)
      return True
    elif self._params['control_name'] in self.FB_PPVAR_PINS:
      self._apply_fb_ppvar_restrictions(args)
      return True

    # Warn user that force flag is being set even though it is not required.
    if 'force' in args:
      raise StudEvbError('Please not set "force" flag if not playing with '
                         'special pins (See EVB user guide)')
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
    """Helper to get bank information from params. It returns credentials of
    start pin and end pin of particular bank.

    Return:
      bank_data: Tuple (start_port, start_pin, end_port, end_pin)
    """
    if 'port' not in self._params or 'offset' not in self._params or \
       'end_port' not in self._params or 'end_offset' not in self._params:
      raise StudEvbError('getting bank pins credentials')

    start_port = int(self._params['port'])
    start_pin = int(self._params['offset'])
    end_port = int(self._params['end_port'])
    end_pin = int(self._params['end_offset'])

    return (start_port, start_pin, end_port, end_pin)

  def _get_bank_pins(self):
    """Helper to go through all pins in particular bank

    Returns:
      Pins: list of strings with pins configuration, one line for each pin:
        <BASE|BRICK><_BANK_><A..D><0..9>:<gpio_state>,<I | O>,<N/PU/PD | PP/OD>
    """
    bank_pins = self._get_bank_params()

    if 'bank_type' not in self._params or 'bank_str' not in self._params:
      raise StudEvbError('gettin bank_type and bank_str')

    bank_type = self._params['bank_type']
    bank_str = self._params['bank_str']

    retval = ''

    pin_cnt = 0
    for port in range(self.ioex.PORT_CNT):
      for pin in range(self.ioex.PINS_PER_PORT):
        if (port == bank_pins[0] and pin >= bank_pins[1]) or \
           (port == bank_pins[2] and pin <= bank_pins[3]):
          pin_params = copy.copy(self._params)
          retval += ("%s_BANK_%s%d:" % (bank_type, bank_str, pin_cnt))
          pin_params = copy.copy(self._params)
          pin_params['port'] = str(port)
          pin_params['offset'] = str(pin)
          pin_ioex = pi4ioe5.pi4Ioe5(self._interface,pin_params)
          retval += pin_ioex._get()
          retval += '\n'
          pin_cnt += 1

    return retval

  def _Get_whole_bank(self):
    """Subtype function to handle get() invocation on BANK controls. Each bank
    consist of 10 pins grouped together in 1 ioex on Lego EVB.

    Returns:
      Pins: See _get_bank_pins() for details
    """
    mux_reg = self.i2c_mux._get()
    self.i2c_mux._set(1)
    retval = self._get_bank_pins()
    self.i2c_mux._set(1, mux_reg)
    return retval

  def _set_bank(self, fn_name, *fn_args):
    """Helper function to iterate through all pins in bank and invoke set() on
    each of them.

    Args:
      fn_name: string with either "_set_pin_to_input" or "_set_pin_to_output"
      fn_args: Arguments to be provided to fn_name()
    """
    bank_pins = self._get_bank_params()

    for port in range(self.ioex.PORT_CNT):
      for pin in range(self.ioex.PINS_PER_PORT):
        if (port == bank_pins[0] and pin >= bank_pins[1]) or \
           (port == bank_pins[2] and pin <= bank_pins[3]):
          pin_params = copy.copy(self._params)
          pin_params['port'] = str(port)
          pin_params['offset'] = str(pin)
          pin_ioex = pi4ioe5.pi4Ioe5(self._interface,pin_params)
          getattr(pin_ioex, fn_name)(*fn_args)

  def _set_bank_to_input(self, pullup):
    self._set_bank('_set_pin_to_input', pullup)

  def _set_bank_to_output(self, value, opendrain):
    self._set_bank('_set_pin_to_output', value, opendrain)

  def _Set_whole_bank(self, fmt_value):
    """Subtype function to handle get() invocation on BANK controls. Each bank
    consist of 10 pins grouped together in 1 ioex on Lego EVB.
    """
    self.i2c_mux._set(1)
    self.ioex._check_set_args_and_call(fmt_value, self._set_bank_to_input, self._set_bank_to_output)
