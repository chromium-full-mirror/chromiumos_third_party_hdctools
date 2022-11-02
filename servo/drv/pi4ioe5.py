# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for board config controls PI4IOE5V6534Q i2c ioexpander."""

from servo.drv import hw_driver
from servo.drv import i2c_reg

class Pi4Ioe5Error(hw_driver.HwDriverError):
  """Error occured accessing Pi4Ioe5."""

class pi4Ioe5(hw_driver.HwDriver):
  """Object to access drv=pi4ioe5 controls."""

  # Indexes for ioex registers being used
  REG_INP = 0x0
  REG_OUT = 0x5
  REG_DIR = 0xF
  REG_PULL_EN = 0x3F
  REG_PULL_SEL = 0x44
  REG_OUT_PORT_CONFIG = 0x53
  REG_OUT_PIN_CONFIG = 0x68

  PORT_CNT = 5
  PORT_VALID_ERR_STR = '0 .. 4'
  PULLUP_VALID_ERR_STR = '-1, 0 or 1'

  def __init__(self, interface, params):
    """Constructor

    Args:
      interface: FTDI interface object to handle low-level communication to
          control
      params: dictionary of params (k=v pairs) needed to perform operations on a driver.
        Notables for this class:
          child: integer, 7-bit i2c child address
          port: integer in [0 .. 4] range
          offset: integer, gpio's bit position from lsb

        Additional param keys are described in HwDriver class constructor
    """

    super(pi4Ioe5, self).__init__(interface, params)
    child = self._get_child() #i2c address of ioex
    self._i2c_obj = i2c_reg.I2cReg.get_device(
        self._interface, child, addr_len=1, reg_len=1, msb_first=True,
        no_read=False, use_reg_cache=False)
    self._port = self._get_port()

  def _help_msg_for_set(self):
    description ="""Incorrect arguments.

     Value to be set is comma-separated value string with:
       1. integers (0/1) corresponding to output pin values
       2. 'I'/'O' - direction to be configured
       3. 'PU'/'PD' - pullup of pulldown configuration for input
       4. 'PP'/'OD' - push-pull or open drain configuration for output

       Caller has four options:
       a) may provide only item 1. - then function sets pin to output (change
       from input if necessary) with this value applied and push-pull config
       b) only 'I' without pullup/pulldown
       c) 'I' with 'PU' or 'PD'
       d) 'O' with item 1. and 4.

    Examples:
      1. Set pin(s) to PD input:
      "I,PD"
      2. Set pin(s) to PP output with initial level high:
      "O,1,PP"
      3. Order of options don't matter, thus below are equivalents:
      "1,PP,O", "O,PP,1" and so on
      4. Set pin(s) to push-pull output with level low:
      "0"
       """

    return description

  def _set(self, fmt_value):
    """Set value and configure ioexpander pin

    Args:
      fmt_value: see _help_msg_for_set() above with description
    """
    self._check_set_args_and_call(fmt_value, self._set_pin_to_input, self._set_pin_to_output)

  def _get(self):
    """Get gpio value and flags.

    1. Read state from input register
    2. Read direction of the pin
    3. For inputs check if pullup/pulldown is applied
    4. For output check push-pull vs open drain

    Returns:
      string of format "<gpio_state> <I | O> <N/PU/PD | PP/OD>"
    """

    state = self._read_logical_from_reg(self.REG_INP)

    direction = 'I' if self._read_logical_from_reg(self.REG_DIR) == 1 else 'O'
    flags = str(state) + ' ' + direction + ' '
    if direction == 'I': # Input pin
      pull_en = self._read_logical_from_reg(self.REG_PULL_EN)
      pullup = self._read_logical_from_reg(self.REG_PULL_SEL)
      if pull_en and pullup:
        flags += 'PU'
      elif pull_en and not pullup:
        flags += 'PD'
      else:
        flags += 'N'
    else: # Output pin
      port_out_config = self._i2c_obj._read_reg(self.REG_OUT_PORT_CONFIG)
      port_out_config = (port_out_config >> self._port) & 0x1
      pin_out_config = self._read_logical_from_reg(self.REG_OUT_PIN_CONFIG)
      open_drain = port_out_config ^ pin_out_config
      if open_drain:
        flags += 'OD'
      else:
        flags += 'PP'

    return flags

  def _set_pin_to_input(self, pullup):
    """Configure particular ioex pin to input

    1. Set direction register
    2. Choose pullup or pulldown as requested by caller
    3. Enable pullup/pulldown

    Args:
      pullup: -1 for no pulldown/pullup resistor
        0 for pulldown resistor
        1 for pullup resistor
    """

    _, mask = self._get_offset_mask()
    if mask is None:
      raise Pi4Ioe5Error('Unable to determine mask. Is offset declared?')

    # Set pin direction to input
    current_dir_reg = self._i2c_obj._read_reg(self.REG_DIR + self._port)
    new_dir_reg = current_dir_reg | mask

    if new_dir_reg != current_dir_reg:
      self._i2c_obj._write_reg(self.REG_DIR + self._port, new_dir_reg)

    # Choose pullup or pulldown
    if pullup >= 0:
      current_pull_sel_reg = self._i2c_obj._read_reg(self.REG_PULL_SEL + self._port)
      if pullup == 0:
        new_pull_sel_reg = current_pull_sel_reg & ~mask
      else:
        new_pull_sel_reg = current_pull_sel_reg | mask

      if new_pull_sel_reg != current_pull_sel_reg:
        self._i2c_obj._write_reg(self.REG_PULL_SEL + self._port)

    # Enable pullup or pulldown
    current_pull_en_reg = self._i2c_obj._read_reg(self.REG_PULL_EN + self._port)
    if pullup == -1:
      new_pull_en_reg = current_pull_en_reg & ~mask
    else:
      new_pull_en_reg = current_pull_en_reg | mask

    if new_pull_en_reg != current_pull_en_reg:
      self._i2c_obj._write_reg(self.REG_PULL_EN + self._port)

  def _set_pin_to_output(self, value, opendrain):
    """Configure particular ioex pin to output

    1. Read Output register
    2. Mask accordingly and write back
    3. Read Output Port Configuration register
    4. Read Individual Pin Output Configuration register
    5. Mask accordingly and write back
    6. Read Configuration register
    7. Set pin to output and write back

    Args:
      value: Logical 0 or 1 to be set on output pin
      opendrain: 0 for push-pull and 1 for open drain configuration
    """

    _, mask = self._get_offset_mask()
    if mask is None:
      raise Pi4Ioe5Error('Unable to determine mask. Is offset declared?')

    hw_value = 0
    if value:
      hw_value = self._create_hw_value(value)

    # Read-modify-write output register
    current_out_reg = self._i2c_obj._read_reg(self.REG_OUT + self._port)
    new_out_reg = hw_value | (current_out_reg & ~mask)
    if new_out_reg != current_out_reg:
      self._i2c_obj._write_reg(self.REG_OUT + self._port, new_out_reg)

    # Open drain/push pull is configured on per-port basis via Output Port
    # Configuration Register and can be modified by settings in Individual
    # Pin Output Configuration Register.
    port_oden = self._i2c_obj._read_reg(self.REG_OPCR) >> self._port
    hw_value = port_oden ^ opendrain
    if hw_value:
      hw_value = self._create_hw_value(hw_value)

    current_ipoc_reg = self._i2c_obj._read_reg(self.REG_IPOC + self._port)
    new_ipoc_reg = hw_value | (current_ipoc_reg & ~mask)
    if new_ipoc_reg != current_ipoc_reg:
      self._i2c_obj._write_reg(self.REG_IPOC + self._port, new_ipoc_reg)

    # TODO(b/254521543): Add a knob for modifying output drive strength

    # Read-modify-write direction register
    current_dir_reg = self._i2c_obj._read_reg(self.REG_DIR + self._port)
    new_dir_reg = current_dir_reg & ~mask

    if new_dir_reg != current_dir_reg:
      self._i2c_obj._write_reg(self.REG_DIR + self._port, new_dir_reg)

  def _read_logical_from_reg(self, reg):
    """Read ioex register and get logical value of particular pin

    Args:
      reg: Offset of register within pi4ioe5 ioex to be read.

    Returns:
      logical value corresponding to particular pin in a register
    """

    value = self._i2c_obj._read_reg(reg + self._port)
    return self._create_logical_value(value)

  # Handler for a subclass controls - see 'get()' description in hw_driver.py
  def _Get_whole_ioex(self):
    """Get levels of all pins in particular ioex"""
    for port in range(PORT_CNT):
      value = self._i2c_obj._read_reg(self._REG_INP + port)
      output += "P" + str(port) + ":" + str(value) + "\n"

    return output

  # Handler for a subclass controls - see 'set()' description in hw_driver.py
  def _Set_whole_ioex(self, fmt_value):
    """Set value and configure all ioexpander pins

    Args:
      fmt_value: see _help_msg_for_set() above with description
    """
    self._check_set_args_and_call(fmt_value, self._set_ioex_to_input, self._set_ioex_to_output)


  def _set_ioex_to_input(self, pullup):
    """Configure all ioex pins to input

    1. Set direction register
    2. Choose pullup or pulldown as requested by caller
    3. Enable pullup/pulldown

    Args:
      pullup: -1 for no pulldown/pullup resistor
        0 for pulldown resistor
        1 for pullup resistor
    """
    for port in range(PORT_CNT):
      self._i2c_obj._write_reg(self.REG_DIR + port, 0xFF)

      if pullup == -1:
        # Disable pullup/pulldown and move to the next port
        self._i2c_obj._write_reg(self.REG_PULL_EN + port, 0x0)
        continue
      if pullup == 0:
        # Select pulldown
        self._i2c_obj._write_reg(self.REG_PULL_SEL + port, 0x0)
      elif pullup == 1:
        # Select pullup
        self._i2c_obj._write_reg(self.REG_PULL_SEL + port, 0xFF)
      else:
        raise Pi4Ioe5Error('Incorrect pullup value should be %r got %r.' %
                           self.PULLUP_VALID_ERR_STR, str(pullup))

      # Enable pullup/pulldown
      self._i2c_obj._write_reg(self.REG_PULL_EN + port, 0xFF)

  def _set_ioex_to_output(self, value, opendrain):
    raise Pi4Ioe5Error('Setting all ioex pins to output is not supported')

  def _check_set_args_and_call(self, fmt_value, set_input, set_output):
    """Parse input string and take appropriate action

    Arguments:
      fmt_value: see _help_msg_for_set() above with description
      set_input: Function to configure pin/whole ioex as inputs
      set_output: Function to configure pin/whole ioex as outputs
    """
    args = fmt_value.split(',')

    if len(args) > 3:
      raise Pi4Ioe5Error('Too many arguments')

    digit = False
    for idx, i in enumerate(args):
      if i.isdigit():
        digit = True
        int_idx = idx

    # Case d) e.g: "O,1,PP"
    if len(args) == 3:
      if not 'O' in args or (not 'PP' in args and not 'OD' in args) or not digit:
        raise Pi4Ioe5Error(self._help_msg_for_set())

      if 'PP' in args:
        flags = 0
      else:
        flags = 1
      set_output(int(args[int_idx]), flags)
      return

    # Case c) e.g.: "I,PD"
    if len(args) == 2:
      if not 'I' in args or (not 'PU' in args and not 'PD' in args):
        raise Pi4Ioe5Error(self._help_msg_for_set())

      if 'PU' in args:
        pullup = 1
      else:
        pullup = 0
      set_input(pullup)
      return

    # Case a) e.g. "I" and b) "1"
    if not 'I' in args and not digit:
      raise Pi4Ioe5Error(self._help_msg_for_set())

    if 'I' in args:
      pullup = -1 # Neither PU nor PD

    if digit:
      set_output(int(args[int_idx]), 0) # Default is push-pull
    else:
      set_input(pullup)

  def _get_child(self):
    """Check and return needed params to call driver.

    Returns:
      child: 7-bit i2c address
    """

    if 'child' not in self._params:
      raise Pi4Ioe5('getting child address')
    child = int(self._params['child'], 0)
    return child

  def _get_port(self):
    """Check and return needed params to call driver.

    Returns:
      port: port ( 0 .. 4 ) on the pi4ioe5 (used to calc register index)
    """

    if 'port' not in self._params:
      raise Pi4Ioe5Error('getting port')
    port = int(self._params['port'], 0)
    if port < 0 or port > self.PORT_CNT:
      raise Pi4Ioe5Error('port value should be %r' % self.PORT_VALID_ERR_STR)
    return port

