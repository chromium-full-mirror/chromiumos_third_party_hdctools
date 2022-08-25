# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Servo Server."""

import collections
import logging
import sys
try:
  from SimpleXMLRPCServer import SimpleXMLRPCServer
except ImportError:
  from xmlrpc.server import SimpleXMLRPCServer
  # TODO(crbug.com/999878): This is for python3 compatibility.
  # Remove once fully moved to python3.

from servo import recovery
from servo import servo_dev_templates
from servo.utils import diagnose

class ServodError(Exception):
  """Exception class for servod."""


class Servod(object):
  """Main class for Servo debug/controller Daemon."""

  # Separator for control strings between servo device prefix and control name
  PREFIX_DELIMITER = '.'

  # This is the key to get the main serial used in the serialnames dict.
  MAIN_SERIAL = 'main'

  def __init__(self, usbkm232=None):
    """Servod constructor.

    Args:
      usbkm232: String. Optional. Path to USB-KM232 device which allow for
          sending keyboard commands to DUTs that do not have built in
          keyboards. Used in FAFT tests. Use None for on board AVR MCU.
          e.g. '/dev/ttyUSB0' or None.

    Raises:
      ServodError: if unable to locate init method for particular interface
    """
    self._logger = logging.getLogger('Servod')
    self._logger.debug('')
    self._usbkm232 = usbkm232
    self._keyboard = None
    self._usb_keyboard = None
    self._serialnames = collections.defaultdict(lambda: None)
    # A map of ServoDevices keyed by their name/prefix.
    # A ServoDevice can have multiple name/prefix (e.g. 'main', '')
    self._devices = collections.defaultdict(lambda: None)
    # A map of ServoDevices keyed by their id (vid, pid, serial)
    # Each ServoDevice has a unique id
    self._unique_devices = collections.defaultdict(lambda: None)
    # All known controls of this servod instance
    self._controls = set()

  def add_device(self, device, prefix):
    """ Add a ServoDevice to Servod.

    Args:
      device: a ServoDevice that can interact with Servod, dut, and other ServoDevices
      prefix: prefix of the ServoDevice recognized by Servod
    """
    self._logger.debug('Adding ServoDevice %s to instance.', device)
    if prefix in self._devices:
      if device != self._devices[prefix]:
        raise ServodError('ServoDevice prefix %s alredy represents device %s and cannot be added as %s.',
          prefix, self._devices[prefix], device)
      else:
        self._logger.debug('ServoDevice prefix %s is already added as %s.', prefix, self._devices[prefix])
        return
    self._unique_devices[device.get_id()] = device
    self._devices[prefix] = device
    self.add_serial_number(prefix, device._serial)
    if prefix == servo_dev_templates.MAIN_DEV_PREFIX:
      # This is the main device as the prefix is empty. Add prefix alias here
      # for the main device.
      self._devices[servo_dev_templates.MAIN_DEV_PREFIX_ALIAS] = device
      self.add_serial_number(self.MAIN_SERIAL, device._serial)

  def reinitialize(self):
    """Reinitialize all devices that support reinitialization"""
    for device in self._devices.values():
        device.reinitialize()

  def close(self):
    """Servod turn down logic."""
    for dev in self.get_devices():
      dev.close()

  def get_devices(self):
    """Get all devices connected to this servod instance."""
    return set(self._devices.values())

  @staticmethod
  def _get_control_prefix_and_name(name):
    """Return (prefix, name) tuple from name passed into servod.

    Args:
      name: name passed into any of the RPCs

    Returns:
      (prefix, name) tuple, where
        prefix is anything before the '.'
        name anything after it
        If there is no '.' in |name| return ('', name)
    Raises:
      ServodError: if there are more than one PREFIX_DELIMITER in |name|922gg
    """
    if Servod.PREFIX_DELIMITER not in name:
      return ('', name)
    parts = name.split(Servod.PREFIX_DELIMITER)
    if len(parts) > 2:
      # Returned early if no |PREFIX_DELIMITER| in name, therefore after the
      # split there have to be at least 2 parts here.
      raise ServodError('Name %r is malformed: at most one %r is allowed.' %
                        (name, Servod.PREFIX_DELIMITER))
    return tuple(parts)

  def _is_main_dev_prefix(self, prefix):
    """Return whether |prefix| is the main device prefix.

    Args:
      prefix: prefix to query

    Returns:
      True, if the prefix has a main device prefix
    """
    return prefix in servo_dev_templates.MAIN_DEV_PREFIXES

  def _get_dev_and_name(self, name):
    """Return (dev, name) tuple after processing the name's prefix.

    Args:
      name: control name to get dev for

    Returns:
      (dev, name) tuple where
        dev is the ServoDevice instance to handle |name|
        name is the name after removing the prefix, if there was one
    Raises:
      ServodError: if no ServoDev can be found to handle |name|
      NameError: if |name| not a known control on its servo dev.
    """
    prefix, processed_name = Servod._get_control_prefix_and_name(name)
    if prefix not in self._devices:
      raise ServodError('No servo device registered for prefix %s' % prefix)
    dev = self._devices[prefix]

    # Controls routed to main that are not covered by main are covered by their
    # root hub device.
    if not dev.syscfg.is_control(processed_name):
      if self._is_main_dev_prefix(prefix) and dev.get_root_hub_device() is not None:
        dev = dev.get_root_hub_device()
    
    if not dev.syscfg.is_control(processed_name):
      raise ServodError('Control %s is not registerd with any connected servo device. '
        'Servo device %s (prefix: \'%s\') is picked as the targed device for the control.'
        '\nAll controls: \n%s'
        % (name, dev, prefix, self._controls))
      # TODO(konmari): refactor this to be a control. Too long to show in command line

    self._logger.debug('Using servo device %s for control %s.', dev, name)
    return (dev, processed_name)

  def get(self, name):
    """Get control value.

    Args:
      name: name string of control

    Returns:
      Response from calling drv get method.  Value is reformatted based on
      control's dictionary parameters

    Raises:
      HwDriverError: Error occurred while using drv
      ServodError: if interfaces are not available within timeout period
    """
    dev, name = self._get_dev_and_name(name)
    return dev.get(name)

  def set(self, name, wr_val_str):
    """Set control on servo device.

    Args:
      name: name string of control
      wr_val_str: value string to write.  Can be integer, float or a
          alpha-numerical that is mapped to a integer or float.

    Returns:
      True, coming from the device's set call, to appease xmlrpc

    Raises:
      HwDriverError: Error occurred while using driver
      ServodError: if interfaces are not available within timeout period
    """
    dev, name = self._get_dev_and_name(name)
    return dev.set(name, wr_val_str)
  
  def update_known_ctrls(self):
    """Helper to generate a list of all accessible controls in servod."""
    known_ctrls = set()
    for prefix, dev in self._devices.items():
      dev_ctrls = dev.syscfg.get_all_controls()
      # controls for root and main dev does not need to have prefixes
      new_ctrls = set('%s.%s' % (prefix, ctrl) for ctrl in dev_ctrls) \
        if prefix else dev_ctrls 
      if prefix == servo_dev_templates.ROOT_DEV_PREFIX:
        new_ctrls |= dev_ctrls
      known_ctrls |= new_ctrls
    self._controls = sorted(list(known_ctrls))

  def has_control(self, control):
    """Returns True if control is available in servod."""
    return control in self._controls

  def doc_all(self):
    """Return all documenation for controls.

    Returns:
      string of <doc> text in config file (xml) and the params dictionary for
      all controls.

      For example:
      warm_reset             :: Reset the device warmly
      ------------------------> {'interface': '1', 'map': 'onoff_i', ... }
    """
    self.update_known_ctrls()
    rsp = []
    for name in self._controls:
      dev, control = self._get_dev_and_name(name)
      rsp.append(dev.syscfg.get_control_str(control))
    self._logger.debug("rsp %s", rsp)
    return '\n'.join(rsp)

  def doc(self, name):
    """Retreive doc string in system config file for given control name.

    Args:
      name: name string of control to get doc string

    Returns:
      doc string of name

    Raises:
      NameError: if fails to locate control
    """
    dev, control = self._get_dev_and_name(name)
    return dev.doc(control)

  def set_get_all(self, cmds):
    """Set &| get one or more control values.

    Args:
      cmds: list of control[:value] to get or set.

    Returns:
      rv: list of responses from calling get or set methods.
    """
    rv = []
    for cmd in cmds:
      if ':' in cmd:
        (control, value) = cmd.split(':', 1)
        rv.append(self.set(control, value))
      else:
        rv.append(self.get(cmd))
    return rv

  def get_all(self, verbose):
    """Get all controls values.

    Args:
      verbose: Boolean on whether to return doc info as well

    Returns:
      string creating from trying to get all values of all controls.  In case of
      error attempting access to control, response is 'ERR'.
    """
    self.update_known_ctrls()
    rsp = []
    for name in self._controls:
      # avoid repeating the controls starting with 'main.' and 'root.'
      if name.startswith('%s.' % servo_dev_templates.MAIN_DEV_PREFIX) or \
        name.startswith('%s.' % servo_dev_templates.ROOT_DEV_PREFIX):
        continue
      self._logger.debug('name = %s' % name)
      try:
        value = self.get(name)
      except Exception:
        value = 'ERR'
        pass
      if verbose:
        rsp.append('GET %s = %s :: %s' % (name, value, self.doc(name)))
      else:
        rsp.append('%s:%s' % (name, value))
    return '\n'.join(sorted(rsp))

  def echo(self, echo):
    """Mock echo function for testing/examples.

    Args:
      echo: string to echo back to client
    """
    self._logger.debug('echo(%s)' % (echo))
    return 'ECH0ING: %s' % (echo)

  def get_board(self):
    """Returns the board specified for the main device.

    Returns:
      A string of the board name, or None if not present.
    """
    main_device = self._devices[servo_dev_templates.MAIN_DEV_PREFIX]
    return main_device.board

  def get_base_board(self):
    """Returns the board probed from EC in case the main device is a dut controller.

    Returns:
      A string of the board name, or None if not present.
    """
    main_device = self._devices[servo_dev_templates.MAIN_DEV_PREFIX]
    return main_device.base_board

  def get_servo_serials(self):
    """Return all the serials associated with this process."""
    return self._serialnames

  def add_serial_number(self, name, serial_number):
    """Adds the serial number to the _serialnames dictionary.

    Args:
      name: A string which is the key into the _serialnames dictionary.
      serial_number: A string which is the key into the _serialnames dictionary.
    """
    self._serialnames[name] = serial_number
    self._logger.debug('Added %s %s to serialnames.', name, serial_number)

  def get_serials(self):
    """Gets the current servo serial."""
    return self._serialnames

  def get_main_device(self):
    """Gets the main servo device."""
    return self._devices[servo_dev_templates.MAIN_DEV_PREFIX]
  
  def get_root_device(self):
    """Gets the root servo device."""
    if servo_dev_templates.ROOT_DEV_PREFIX not in self._devices:
      return None
    return self._devices[servo_dev_templates.ROOT_DEV_PREFIX]

  def get_controls_for_tag(self, tag):
    """Get list of controls for a given tag.

    Args:
      tag: str, tag to query

    Returns:
      list of controls with that tag, or an empty list if no such tag, or
      controls under that tag
    """
    controls = set()
    for prefix, dev in self._devices.items():
      # controls for root and main dev does not need to have prefixes
      no_prefix = (prefix in servo_dev_templates.MAIN_DEV_PREFIXES) or \
                  (prefix == servo_dev_templates.ROOT_DEV_PREFIX)
      for dev_ctrl in dev.syscfg.get_controls_for_tag(tag):
        controls.add(dev_ctrl if no_prefix else '%s.%s' % (prefix, dev_ctrl))
    return list(controls)

  def get_config_files(self):
    """Gets the configuration files used for this servo server invocation"""
    config_files = {}
    for dev in self._unique_devices.values():
      xml_files = dev.syscfg._loaded_xml_files
      # See system_config.py for schema, but entry[0] is the file name
      config_files[dev.prefix] = [entry[0] for entry in xml_files]
    return config_files

  def get_interfaces(self):
    # TODO(konmari): temporarily use the main device to hold all interfaces and drvs.
    #                Will be cleaned up after ServoDevice interface is properly implemented.
    main_device = self._devices[servo_dev_templates.MAIN_DEV_PREFIX]
    return main_device._interfaces

  def get_interface_list(self):
    # TODO(konmari): temporarily use the main device to hold all interfaces and drvs.
    #                Will be cleaned up after ServoDevice interface is properly implemented.
    main_device = self._devices[servo_dev_templates.MAIN_DEV_PREFIX]
    return main_device._interface_list
  
  def validate_dut_controller(self):
    """Validate the servod instance has at least 1 dut controller."""
    for dev in self._devices.values():
      if dev.template.DUT_CONTROLLER:
        return
    
    # Start diagnosing why servod does not have DUT controller.
    # Fail if we requested board control but don't have an interface for this.
    if self.get_board():
      if self.get('dut_connection_type') == 'type-c':
        faults = diagnose.diagnose_ccd(self.get_main_device())
        if diagnose.SBU_VOLTAGE_FLOAT in faults:
          self.set('dut_sbu_voltage_float_fault', 'on')
      # No need to check for the LOW voltage signal here as the fault
      # is valid for both ccd and for servo micro: a controller is missing
      self.set('dut_controller_missing_fault', 'on')

      self._logger.error('No Servo Micro, C2D2, or CCD detected for board %s',
        self.get_board())
      self._logger.error('Try flipping the USB type C cable if you were using '
                         'servo v4 type C.')
      self._logger.error('If flipping the cable allows CCD, please file a bug '
                         'against the DUT platform with reproducing details.')

      dut_controller_tolerant = recovery.is_recovery_active()
      if dut_controller_tolerant:
        self._logger.info('Will continue startup as recovery mode has '
                        'been requested')
      else:
        self._logger.fatal('No device interface '
                        '(Servo Micro, C2D2, or CCD) connected.')
        sys.exit(-1)
