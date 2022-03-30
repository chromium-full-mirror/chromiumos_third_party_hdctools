# Copyright 2016 The Chromium OS Authors. All rights reserved.
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
      if str(e) in ['Timeout waiting for response.', 'No data was sent from the pty.']:
        e.message += 'CCD console might be locked. Check and unlock with instructions \
          https://chromium.googlesource.com/chromiumos/platform/ec/+/cr50_stab/docs\
          /case_closed_debugging_cr50.md'
      # Raise the original exception
      raise

  return wrapper

class cr50Error(pty_driver.ptyError):
  """Exception class for Cr50."""


class cr50(pty_driver.ptyDriver):
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

  RDD_RE = r'Rdd:\s+(?P<rdd>\S+)[\r\n]+(KeepAlive: (?P<keepalive>\S+)\s)?'

  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: FTDI interface object to handle low-level communication to
        control
      params: dictionary of params needed to perform operations on
        devices. The only params used now is 'subtype', which is used
        by get/set method of base class to decide how to dispatch
        request.
    """
    super(cr50, self).__init__(interface, params)
    self._logger.debug('')
    self._interface = interface
    if not hasattr(self._interface, '_ec_uart_bitbang_props'):
      self._interface._ec_uart_bitbang_props = {
          'enabled': 0,
          'parity': None,
          'baudrate': None
      }

  @restricted_command
  def _get(self):
    # Explicit call parent class method to apply annotation.
    return super(cr50, self)._get()

  @restricted_command
  def _set(self, value):
    # Explicit call parent class method to apply annotation.
    return super(cr50, self)._set(value)

  def _issue_cmd_get_results(self, cmds, regex_list, flush=None,
                             timeout=pty_driver.DEFAULT_UART_TIMEOUT):
    """Send \n to make sure cr50 is awake before sending cmds

    Make sure we get some sort of response before considering cr50 up. If it's
    already up, we should see '>' almost immediately. If cr50 is in deep
    sleep, wait for console enabled.
    """
    trys_left = self.PROMPT_DETECTION_TRIES
    while trys_left > 0:
        trys_left -= 1
        try:
          super(cr50, self)._issue_cmd_get_results('\n\n',
                                                   [r'(>|Console is enabled)'])
          break
        except pty_driver.ptyError:
          logging.debug("cr50 prompt detection failed, %d attempts left.", trys_left)
          if trys_left <= 0:
              self._logger.warning('Consider checking whether the servo device has '
                                'read/write access to the Cr50 UART console.')
              raise cr50Error('cr50 uart is unresponsive')
          time.sleep(self.PROMPT_DETECTION_INTERVAL)

    return super(cr50, self)._issue_cmd_get_results(cmds, regex_list,
                                                    flush=flush,
                                                    timeout=timeout)

  def _Set_cold_reset(self, value):
    """Setter of cold_reset (active low).

    Args:
      value: 0=on, 1=off.
    """
    if value == 0:
      self._issue_cmd('ecrst on')
    else:
      self._issue_cmd('ecrst off')

  def _Set_warm_reset(self, value):
    """Setter of warm_reset (active low).

    Args:
      value: 0=on, 1=off.
    """
    if value == 0:
      self._issue_cmd('sysrst on')
    else:
      self._issue_cmd('sysrst off')

  def _Get_ccd_state(self):
    """Run a basic command that should take a short amount of time to check
    if ccd endpoints are still working.
    Returns:
      0: ccd is off.
      1: ccd is on.
    """
    try:
      # If gettime fails then the cr50 console is not working, which means
      # ccd is not working
      self._issue_cmd_get_results('gettime', ['.'], 3)
    except:
      return 0
    return 1

  def _Set_pwr_button(self, value):
    """CCD doesn't support pwr_button. Tell user about pwr_button_hold"""
    raise cr50Error('pwr_button not supported use pwr_button_hold')

  def _Set_cr50_reboot(self, value):
    """Reboot cr50 ignoring the value."""
    self._issue_cmd('reboot')

  def _Set_ccd_noop(self, value):
    """Used to ignore servo controls"""

  def _Get_ccd_noop(self):
    """Used to ignore servo controls"""
    return 'ERR'

  def _get_ccd_cap_state(self, cap):
    """Get the current state of the ccd capability"""
    result = self._issue_cmd_get_results('ccdstate', [r'%s:([^\n]*)\n' % cap])
    return result[0][1].strip()

  def _Get_ccd_keepalive_en(self):
    """Getter of ccd_keepalive_en.

    Returns:
      0: keepalive disabled.
      1: keepalive enabled.
    """
    result = self._issue_cmd_get_results('ccdstate', ['ccdstate.*>'])[0]
    rddstate = re.search(self.RDD_RE, result)
    if not rddstate:
      raise cr50Error('Unable to get rdd output %r', result)
    # Older versions of cr50 don't have a devoted KeepAlive field. Use the
    # keepalive output where possible.
    # Check for shorter strings in case servo drops output.
    keepalive = rddstate.group('keepalive')
    if keepalive:
      rv = 'ena' in keepalive
    else:
      rv = 'keep' in rddstate.group('rdd')
    return int(rv)

  def _Set_ccd_keepalive_en(self, value):
    """Setter of ccd_keepalive_en.

    Args:
      value: 0=off, 1=on.
    """
    self._issue_cmd('rddkeepalive %s' % ('on' if value else 'off'))

  def _Get_ec_uart_bitbang_en(self):
    return int(self._interface._ec_uart_bitbang_props['enabled'])

  def _Set_ec_uart_bitbang_en(self, value):
    if value:
      # We need parity and baudrate settings in order to enable bit banging.
      if not self._interface._ec_uart_bitbang_props['parity']:
        raise ValueError("No parity set.  Try setting 'ec_uart_parity' first.")

      if not self._interface._ec_uart_bitbang_props['baudrate']:
        raise ValueError(
            "No baud rate set.  Try setting 'ec_uart_baudrate' first.")

      # The EC UART index is 2.
      cmd = '%s %s %s' % ('bitbang 2',
                          self._interface._ec_uart_bitbang_props['baudrate'],
                          self._interface._ec_uart_bitbang_props['parity'])
      try:
        result = self._issue_cmd_get_results(cmd, ['Bit bang enabled'])
        if result is None:
          raise cr50Error('Unable to enable bit bang mode!')
      except pty_driver.ptyError:
        raise cr50Error('Unable to enable bit bang mode!')

      self._interface._ec_uart_bitbang_props['enabled'] = 1

    else:
      self._issue_cmd('bitbang 2 disable')
      self._interface._ec_uart_bitbang_props['enabled'] = 0

  def _Get_ccd_ec_uart_parity(self):
    self._logger.debug('%r', self._interface._ec_uart_bitbang_props)
    return self._interface._ec_uart_bitbang_props['parity']

  def _Set_ccd_ec_uart_parity(self, value):
    if value.lower() not in ['odd', 'even', 'none']:
      raise ValueError("Bad parity (%s). Try 'odd', 'even', or 'none'." % value)

    self._interface._ec_uart_bitbang_props['parity'] = value
    self._logger.debug('%r', self._interface._ec_uart_bitbang_props)

  def _Get_ccd_ec_uart_baudrate(self):
    return self._interface._ec_uart_bitbang_props['baudrate']

  def _Set_ccd_ec_uart_baudrate(self, value):
    if value is not None and value.lower() not in [
        'none', '1200', '2400', '4800', '9600', '19200', '38400', '57600',
        '115200'
    ]:
      raise ValueError("Bad baud rate(%s). Try '1200', '2400', '4800', '9600',"
                       " '19200', '38400', '57600', or '115200'" % value)

    if value.lower() == 'none':
      value = None
    self._interface._ec_uart_bitbang_props['baudrate'] = value

  def _Get_ec_boot_mode(self):
    boot_mode = 'off'
    result = self._issue_cmd_get_results('gpioget EC_FLASH_SELECT',
                                         [r'\s+([01])\*?\s+EC_FLASH_SELECT'])[0]
    if result:
      if result[1] == '1':
        boot_mode = 'on'

    return boot_mode

  def _Set_ec_boot_mode(self, value):
    self._issue_cmd('gpioset EC_FLASH_SELECT %s' % value)

  def _Get_uut_boot_mode(self):
    result = self._issue_cmd_get_results('gpiocfg', ['gpiocfg(.*)>'])[0][0]
    if re.search(r'GPIO0_GPIO15:\s+read 0 drive 0', result):
        return 'on'
    return 'off'

  def _Get_ap_flash_select(self):
    flash_select = 'off'
    result = self._issue_cmd_get_results('gpioget AP_FLASH_SELECT',
                                         [r'\s+([01])\*?\s+AP_FLASH_SELECT'])[0]
    if result:
      if result[1] == '1':
        flash_select = 'on'

    return flash_select

  def _Set_ap_flash_select(self, value):
    self._issue_cmd('gpioset AP_FLASH_SELECT %s' % value)

  def _Set_uut_boot_mode(self, value):
    self._issue_cmd('gpioset EC_TX_CR50_RX_OUT %s' % value)

  def _Set_detect_servo(self, val):
    """Setter of the servo detection state.

    ccdblock can be configured to enable servo detection even if ccd is enabled.
    Cr50 uses EC uart to detect servo. If cr50 drives that signal, it can't
    detect servo pulling it up. ccdblock servo will disable uart, so we can
    detect servo.
    """
    if val:
      self._issue_cmd('ccdblock servo enable')
      # make sure we aren't ignoring servo. That will interfere with detection.
      self._issue_cmd('ccdblock IGNORE_SERVO disable')
    else:
      self._issue_cmd('ccdblock servo disable')

  def _Get_rec_btn_force(self):
    result = self._issue_cmd_get_results(
        'recbtnforce', [r'RecBtn:([\S ]+)[\n\r]'])[0][1]
    if result is None:
      raise cr50Error('Cannot retrieve the recbtnforce on cr50 console.')
    if 'not pressed' in result:
      return 'off'
    if 'forced pressed' in result:
      return 'on'
    raise cr50Error('Invalid value for recbtnforce')

  def _Set_rec_btn_force(self, value):
    try:
      result = None
      if value:
        result = self._issue_cmd_get_results(
              'recbtnforce enable', ['forced pressed'])
      else:
        result = self._issue_cmd_get_results(
              'recbtnforce disable', ['not pressed'])
      if result is None:
        raise cr50Error('recbtnforce failed, Check GscFullConsole perm.')
    except pty_driver.ptyError:
      raise cr50Error('Unable to change recbtnforce status!')

  def _Get_rec_mode(self):
    result = 'off'
    gpio = self._issue_cmd_get_results('gpioget CCD_REC_LID_SWITCH',
                                       [r'\s+([01])\*?\s+CCD_REC_LID_SWITCH'])
    if gpio[0]:
      if gpio[0][1] == '0':
        result = 'on'

    if result != self._Get_rec_btn_force():
      raise cr50Error('recbtnforce and CCD_REC_LID_SWITCH don\'t match!')
    return result

  def _Set_rec_mode(self, value):
    self._issue_cmd('gpioset CCD_REC_LID_SWITCH %d' % value)
    self._Set_rec_btn_force(value == 0)
