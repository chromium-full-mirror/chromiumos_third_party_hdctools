# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Atmega USB Keyboard emulator programmer."""

import time

from servo_mfg import exec_util
from servo_mfg import programmer
from servo_mfg import util


class AtmegaKBEmulatorProgrammerError(programmer.ProgrammerError):
  """AtmegaKBEmulatorProgrammer error class."""


class AtmegaKBEmulatorProgrammer(programmer.Programmer):
  """Atmega USB Keyboard emulator programmer."""

  NAME = 'ATMEGA32U4 Programmer'

  # USB KB emulator firmware binary filename
  BIN = 'Keyboard.hex'
  # The VID of the USB KB emulator. Same pre and post flashing.
  ATM_LUFA_VID = ATM_DFU_VID = 0x03eb
  # The PID of the USB KB emulator before programming/in DFU mode
  ATM_DFU_PID = 0x2ff4
  # The PID of the USB KB emulator after programming
  ATM_LUFA_PID = 0x2042

  # Binary to program the atmega programmer.
  PROGRAMMER_BIN = 'dfu-programmer'

  # These are the programmer parts to erase and write with the tool
  BASE_CMD = [PROGRAMMER_BIN, 'atmega32u4']

  # command to erase the atmega chip content.
  ERASE_CMD = BASE_CMD + ['erase', '--force']

  # command to write the binary to the atmega chip.
  WRITE_CMD = BASE_CMD + ['flash']

  # Name of the atmega firmware binary.
  BIN = 'Keyboard.hex'

  # The mask for the gpio expander input/output to determine reset signal
  # status.
  I2C_RD_MASK = 0x2

  # Time to wait after reset/power-cycle for the keyboard emulator to enumerate.
  ATM_BOOT_TIMEOUT_S = 10.0

  def __init__(self, force, i2caddr, i2coffset, parent_hub_vid=None,
               parent_hub_pid=None):
    """Initialize the programmer.

    Args:
      force: whether to force flashing even if the device appears to be flashed
      i2caddr: i2c address of the reset pin on the gpio expander
      i2coffset: offset of the reset pin on the gpio expander
      parent_hub_vid: vid of the usb hub the keyboard emulator enumerates on
      parent_hub_pid: pid of the usb hub the keyboard emulator enumerates on
    """
    programmer.Programmer.__init__(self, force=force)
    self._parent_hub_vid = parent_hub_vid
    self._parent_hub_pid = parent_hub_pid
    self._vid = self.ATM_DFU_VID
    self._i2caddr = i2caddr
    self._i2coffset = i2coffset
    # The command to read the reset enable pin.
    self._i2crd_cmd = r'i2cxfer r 1 0x%02x %d' % (self._i2caddr,
                                                  self._i2coffset)
    # The command to write to the reset enable pin.
    self._i2cwr_cmd = r'i2cxfer w 1 0x%02x %d' % (self._i2caddr,
                                                  self._i2coffset)

  def _find(self, timeout=ATM_BOOT_TIMEOUT_S):
    """Overwrite to avoid throwing an error iff the chip is programmed.

    Args:
      timeout: timeout in s for the chip to enumerate

    Returns:
      the result of |Programmer._find| if either |self.ATM_DFU_PID| or
      |self.ATM_LUFA_PID| can be found.

    Raises:
      AtmegaKBEmulatorProgrammerError: if neither PID is found.
    """
    # The chip might be in DFU mode or in normal mode, so check for both.
    for pid in [self.ATM_DFU_PID, self.ATM_LUFA_PID]:
      try:
        return programmer.Programmer._find(self, pid=pid, timeout=timeout)
      except programmer.ProgrammerError as e:
        self._logger.debug(str(e))
        self._logger.debug('chip might not show up in one of its modes. '
                           'Ignoring for now')
    # If we made it here, this means the chip was not found in any of its known
    # PIDs. Raise an error.
    raise AtmegaKBEmulatorProgrammerError('Atmega chip not found in any mode.')

  def program(self, tiny_servod, **kwargs):
    """Overwrite default |program| to ensure the chip is in reset.

    Args:
      tiny_servod: TinyServod object to communicate with servo ec
      **kwargs: args to forward to the |Programmer.program| section

    Returns:
      True on successful program, False otherwise
    """
    # Need to make sure that the chip is not in reset if possible.
    self._toggle_reset(tiny_servod.pty, on=True)
    return programmer.Programmer.program(self, tiny_servod=tiny_servod,
                                         **kwargs)

  def verify(self, tiny_servod, **kwargs):
    """Overwrite default |verify| to ensure the chip is not in reset.

    Args:
      tiny_servod: TinyServod object to communicate with servo ec
      **kwargs: args to forward to the |Programmer.verify| section

    Returns:
      True on successful verify, False otherwise
    """
    # Need to make sure that the chip is not in reset if possible.
    self._toggle_reset(tiny_servod.pty, on=True)
    return programmer.Programmer.verify(self, tiny_servod=tiny_servod, **kwargs)

  def _program(self, tiny_servod, **_):
    """Helper to perform actual programming.

    Args:
      tiny_servod: TinyServod object to communicate with servo ec

    Returns:
      result of self._verify after programming
    """
    self._reboot_in_dfu_mode(tiny_servod)
    ret, _, _ = exec_util.exec_blocking(self.ERASE_CMD, hint='erasing')
    if ret:
      self.throw_error('Issue on erase. Giving up.')
    write_cmd = self.WRITE_CMD + [util.find_binfile(self.BIN)]
    ret, _, _ = exec_util.exec_blocking(write_cmd, hint='writing')
    if ret:
      self.throw_error('Issue on write. Giving up.')
    self._reboot_in_normal_mode(tiny_servod)

  def _rd_atmega_reg(self, pty):
    """Get atmega reset signal value.

    Read ioexpander output register to determine current value of atmega_reset.

    Args:
      pty: object, ptyDriver instance talking to servo UART

    Returns:
      int, i2c read result from RST register.
    """
    # pylint: disable=protected-access
    # Regex is to extract the read value from the ec output.
    # Sample output: 0x8e [142]
    # need to convert first 'group' into an int based on base 16
    regex_atm = r'(0x[0-9a-f][0-9a-f])\s\[\d+\][\n\r]+'
    results = pty._issue_cmd_get_results(self._i2crd_cmd, [regex_atm])[0]
    rd = results[1].strip().strip('\n\r')
    return int(rd, 16)

  def _wr_atmega_reg(self, pty, wr_val):
    """Write to gpio expander to set atmega reset signal.

    Args:
      pty: object, ptyDriver instance talking to servo UART
      wr_val: int, value to write to the gpio. 1 to turn on reset, 0 to turn off
    """
    # pylint: disable=protected-access
    # private function access pattern required by API
    # Regex accepts anything until the next line to make sure that this only
    # returns once the command finishes.
    regex = '.*>'
    wr_cmd = '%s 0x%02x' % (self._i2cwr_cmd, wr_val)
    pty._issue_cmd_get_results(wr_cmd, [regex])

  def _toggle_dfu_mode(self, pty, on=True):
    """Toggle the DFU mode on the atmega to |on|.

    Note: for this to take effect, you need to go through reset after changing
    the signal once so it can reboot in the right mode.

    Args:
      pty: object, ptyDriver instance talking to servo UART
      on: whether DFU should be on or off
    """
    # pylint: disable=protected-access
    # private function access pattern required by API
    # The command needs to be inverted as it's active low.
    pty._issue_cmd('gpioset ATMEL_HWB_L %d' % int(not on))

  def _toggle_reset(self, pty, on=True):
    """Toggle the reset pin on the atmega to |on|.

    Args:
      pty: object, ptyDriver instance talking to servo UART
      on: whether reset should be on or off

    Raises:
      AtmegaKBEmulatorProgrammerError: on failure to toggle desired reset state
    """
    reg = self._rd_atmega_reg(pty)
    state = bool(reg & self.I2C_RD_MASK)
    if state == on:
      self._logger.debug('Atmega already %s, not setting anything' %
                         'on' if on else 'off')
      return
    # One can flip the value simply.
    wr_val = reg ^ self.I2C_RD_MASK
    self._wr_atmega_reg(pty, wr_val)
    time.sleep(0.2)
    reg = self._rd_atmega_reg(pty)
    state = bool(reg & self.I2C_RD_MASK)
    if state != on:
      raise AtmegaKBEmulatorProgrammerError('Failed to turn atmega reset %s.'
                                            % 'on' if on else 'off')

  def _reboot_in_dfu_mode(self, tiny_servod):
    """wrapper to go through full dfu boot flow.

    Args:
      tiny_servod: TinyServod object to communicate with servo ec
    """
    self._toggle_reset(tiny_servod.pty, on=False)
    self._toggle_dfu_mode(tiny_servod.pty, on=True)
    self._toggle_reset(tiny_servod.pty, on=True)
    programmer.Programmer._find(self, pid=self.ATM_DFU_PID,
                                timeout=self.ATM_BOOT_TIMEOUT_S)

  def _reboot_in_normal_mode(self, tiny_servod):
    """wrapper to go through full normal boot flow.

    Args:
      tiny_servod: TinyServod object to communicate with servo ec
    """
    self._toggle_reset(tiny_servod.pty, on=False)
    self._toggle_dfu_mode(tiny_servod.pty, on=False)
    self._toggle_reset(tiny_servod.pty, on=True)
    programmer.Programmer._find(self, pid=self.ATM_LUFA_PID,
                                timeout=self.ATM_BOOT_TIMEOUT_S)

  def _verify(self, **_):
    """Verify that the device came up with the LUFA pid.

    Returns:
      True if the device reboots with |ATM_LUFA_PID| in normal mode, False
      otherwise
    """
    try:
      programmer.Programmer._find(self, pid=self.ATM_LUFA_PID,
                                  timeout=self.ATM_BOOT_TIMEOUT_S)
      return True
    except programmer.ProgrammerError as e:
      self.debug(e)
      self.debug('Failed to find atmega programmed PID. marking as unverified.')
      return False

  def _verify_programming_env(self):
    """Helper to validate that programming tools are available."""
    # find the programming tool
    if not util.validate_exec_available(self.PROGRAMMER_BIN):
      self.exec_missing(self.PROGRAMMER_BIN)
    # find the template text file in binary
    if not util.find_binfile(self.BIN):
      self.bin_file_missing(self.BIN)
