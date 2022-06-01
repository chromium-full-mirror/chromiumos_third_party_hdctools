# Copyright (c) 2012 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Servo Server."""
import logging
import os
import re
try:
  from SimpleXMLRPCServer import SimpleXMLRPCServer
except ImportError:
  from xmlrpc.server import SimpleXMLRPCServer
  # TODO(crbug.com/999878): This is for python3 compatibility.
  # Remove once fully moved to python3.
import weakref

from servo import servo_dev
from servo import servo_dev_templates
from servo import servo_interfaces
from servo import servo_postinit

class ServodError(Exception):
  """Exception class for servod."""


class Servod(object):
  """Main class for Servo debug/controller Daemon."""

  # This is the key to get the main serial used in the _serialnames dict.
  MAIN_SERIAL = 'main'
  SERVO_MICRO_SERIAL = 'servo_micro'
  C2D2_SERIAL = 'c2d2'
  CCD_SERIAL = 'ccd'

  # Separator for control strings between servo device prefix and control name
  PREFIX_DELIMITER = '.'

  # TODO(konmari): to be moved to ServoDevice class.
  #                Need to move interface list to ServoDevice first.
  def init_servo_interfaces(self, vendor, product, serialname, interfaces):
    """Init the servo interfaces with the given interfaces.

    We don't use the self._{vendor,product,serialname} attributes because we
    want to allow other callers to initialize other interfaces that may not
    be associated with the initialized attributes (e.g. a servo v4 servod object
    that wants to also initialize a servo micro interface).

    Args:
      vendor: USB vendor id of FTDI device.
      product: USB product id of FTDI device.
      serialname: String of device serialname/number as defined in FTDI
          eeprom.
      interfaces: List of strings of interface types the server will
          instantiate.

    Raises:
      ServodError if unable to locate init method for particular interface.
    """
    # If it is a new device add it to the list
    device = (vendor, product, serialname)
    if device not in self._devices:
      vendor, product, serialname = device

      template = servo_dev_templates.GetTemplateClass(vid=vendor, pid=product, serial=serialname)
      servod_device = servo_dev.ServoDevice(template, self._syscfg, serialname, interfaces, 
        self._version, weakref.proxy(self), self._board)
      self._devices[device] = servod_device
    # TODO(konmari): temporarily use the main device to hold all interfaces and drvs. 
    #                Will be cleaned up after ServoDevice interface is properly implemented.
    main_device = self._devices[(self._vendor, self._product, self._serialnames[self.MAIN_SERIAL])]
    main_device.init_servo_interfaces(vendor, product, serialname, interfaces)

  def __init__(self, config, vendor, product, serialname=None, interfaces=None,
               board='', model='', version=None, usbkm232=None):
    """Servod constructor.

    Args:
      config: instance of SystemConfig containing all controls for
          particular Servod invocation
      vendor: usb vendor id of FTDI device
      product: usb product id of FTDI device
      serialname: string of device serialname/number as defined in FTDI eeprom.
      interfaces: list of strings of interface types the server will instantiate
      board: board name. e.g. octopus, coral, or scarlet.
      model: model name of a given board. e.g. fleex, ampton, or apel.
      version: String. Servo board version. Examples: servo_v1, servo_v2,
          servo_v2_r0, servo_v3
      usbkm232: String. Optional. Path to USB-KM232 device which allow for
          sending keyboard commands to DUTs that do not have built in
          keyboards. Used in FAFT tests. Use None for on board AVR MCU.
          e.g. '/dev/ttyUSB0' or None.

    Raises:
      ServodError: if unable to locate init method for particular interface
    """
    self._logger = logging.getLogger('Servod')
    self._logger.debug('')
    self._vendor = vendor
    self._product = product
    self._version = version
    self._serialnames = {self.MAIN_SERIAL: serialname}
    self._usbkm232 = usbkm232
    self._keyboard = None
    self._usb_keyboard = None
    self._base_board = ''
    self._board = board
    if model:
      self._board += '_' + model
    self._model = model
    self._devices = {}
    # TODO(konmari): _syscfg are to be moved to ServoDevice class.
    #                Need to refactor servo_postinit first.
    self._syscfg = config
    if not interfaces:
      try:
        interfaces = servo_interfaces.INTERFACE_BOARDS[board][vendor][product]
      except KeyError:
        interfaces = servo_interfaces.INTERFACE_DEFAULTS[vendor][product]
    self._interfaces = interfaces
    self.init_servo_interfaces(vendor, product, serialname, interfaces)
    servo_postinit.post_init(self)
    self._syscfg.finalize()

  def reinitialize(self):
    """Reinitialize all devices that support reinitialization"""
    for device in self._devices.values():
        device.reinitialize()

  def get_servo_interfaces(self, position, size):
    """Get the list of servo interfaces.

    Args:
      position: The index the first interface to get.
      size: The number of the interfaces.
    """
    # TODO(konmari): temporarily use the main device to hold all interfaces and drvs. 
    #                Will be cleaned up after ServoDevice interface is properly implemented.
    main_device = self._devices[(self._vendor, self._product, self._serialnames[self.MAIN_SERIAL])]
    return main_device.get_interface_list()[position:(position + size)]

  # TODO(konmari): to be moved to ServoDevice class.
  #                Need to move interface list to ServoDevice first.
  def set_servo_interfaces(self, position, interfaces):
    """Set the list of servo interfaces.

    Args:
      position: The index the first interface to set.
      interfaces: The list of interfaces to set.
    """
    # TODO(konmari): temporarily use the main device to hold all interfaces and drvs. 
    #                Will be cleaned up after ServoDevice interface is properly implemented.
    main_device = self._devices[(self._vendor, self._product, self._serialnames[self.MAIN_SERIAL])]
    size = len(interfaces)
    main_device.get_interface_list()[position:(position + size)] = interfaces

  # TODO(konmari): to be moved to ServoDevice class.
  #                Need to move interface list to ServoDevice first.
  def close(self):
    """Servod turn down logic."""
    for dev in self.get_devices():
      dev.close()

  def get_devices(self):
    return self._devices.values()

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
    # TODO(konmari): temporarily use the main device to hold all interfaces and drvs. 
    #                Will be cleaned up after ServoDevice prefix is properly implemented.
    main_device = self._devices[(self._vendor, self._product, self._serialnames[self.MAIN_SERIAL])]
    # TODO(konmari): not pass processed_name because main device is still proxy
    #                for all devices. Will be fixed once we separate device controls
    return (main_device, name)

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
    # TODO(konmari): to be cleaned up after servod metadata is refactored to another pattern
    if 'serialname' in name:
      # This route is to retrieve serialnames on servo v4, which
      # connects to multiple servo-micros or CCD, like the controls,
      # 'ccd_serialname', 'servo_micro_for_soraka_serialname', etc.
      # TODO(aaboagye): Refactor it.
      return self.get_serial_number(name.split('serialname')[0].strip('_'))

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

  def hwinit(self, verbose=False):
    """Initialize all controls on the servo device.

    See ServoDev for details

    Args:
      verbose: boolean, if True prints info about control initialized.
        Otherwise prints nothing.

    Returns:
      This function is called across RPC and as such is expected to return
      something unless transferring 'none' across is allowed. Hence adding a
      dummy return value to make things simpler.
    """
    # TODO(konmari): temporarily use the main device to hold all interfaces and drvs. 
    #                Will be cleaned up after ServoDevice interface is properly implemented.
    main_device = self._devices[(self._vendor, self._product, self._serialnames[self.MAIN_SERIAL])]
    main_device.hwinit(verbose)
    return True

  # TODO(konmari): to be moved to ServoDevice class.
  #                Need to refactor servo_postinit first.
  def clear_cached_drv(self):
    """Clear the cached drivers.

    The drivers are cached in the Dict _drv_dict when a control is got or set.
    When the servo interfaces are relocated, the cached values may become wrong.
    Should call this method to clear the cached values.
    """
    self._drv_dict = {}

  
  # TODO(konmari): to be moved to ServoDevice class.
  #                Need to refactor syscfg to each servo device first.
  def _has_control(self, control):
    """Returns True if control is available in servod."""
    return self._syscfg.is_control(control)

  # TODO(konmari): to be moved to ServoDevice class.
  #                Need to refactor syscfg to each servo device first.
  def doc_all(self):
    """Return all documenation for controls.

    Returns:
      string of <doc> text in config file (xml) and the params dictionary for
      all controls.

      For example:
      warm_reset             :: Reset the device warmly
      ------------------------> {'interface': '1', 'map': 'onoff_i', ... }
    """
    return self._syscfg.display_config()

  # TODO(konmari): to be moved to ServoDevice class.
  #                Need to refactor syscfg to each servo device first.
  def doc(self, name):
    """Retreive doc string in system config file for given control name.

    Args:
      name: name string of control to get doc string

    Returns:
      doc string of name

    Raises:
      NameError: if fails to locate control
    """
    self._logger.debug('name(%s)' % (name))
    if self._syscfg.is_control(name):
      return self._syscfg.get_control_docstring(name)
    else:
      raise NameError('No control %s' % name)

  # TODO(konmari): to be moved to ServoDevice class.
  #                Need to refactor syscfg to each servo device first.
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

  def add_serial_number(self, name, serial_number):
    """Adds the serial number to the _serialnames dictionary.

    Args:
      name: A string which is the key into the _serialnames dictionary.
      serial_number: A string which is the key into the _serialnames dictionary.
    """
    self._serialnames[name] = serial_number
    self._logger.debug('Added %s %s to serialnames %r', name, serial_number,
                       self._serialnames)

  def get_serial_number(self, name):
    """Returns the desired serial number from the serialnames dict.

    Args:
      name: A string which is the key into the _serialnames dictionary.

    Returns:
       A string containing the serial number or "unknown".
    """
    # Remove the prefix from the serialname control. Serialnames are
    # universal. It doesn't matter what the prefix is.
    # The prefix is separated from the main control with '.'
    name = name.split('.', 1)[-1]

    if not name:
      name = 'main'
    try:
      return self._serialnames[name]
    except KeyError:
      self._logger.debug("'%s_serialname' not found!", name)
      return 'unknown'

  # TODO(konmari): to be refactored.
  #                Need to refactor syscfg to each servo device first.
  def get_all(self, verbose):
    """Get all controls values.

    Args:
      verbose: Boolean on whether to return doc info as well

    Returns:
      string creating from trying to get all values of all controls.  In case of
      error attempting access to control, response is 'ERR'.
    """
    rsp = []
    for name in self._syscfg.syscfg_dict['control']:
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
    """Return the board specified at startup, if any."""
    return self._board

  def get_base_board(self):
    """Returns the board name of the base if present.

    Returns:
      A string of the board name, or '' if not present.
    """
    # The value is set in servo_postinit.
    return self._base_board

  def get_version(self):
    """Get servo board version."""
    return self._version

  def get_servo_serials(self):
    """Return all the serials associated with this process."""
    return self._serialnames


def test():
  """Integration testing.

  TODO(tbroch) Enhance integration test and add unittest (see mox)
  """
  logging.basicConfig(
      level=logging.DEBUG,
      format='%(asctime)s - %(name)s - ' + '%(levelname)s - %(message)s')
  # configure server & listen
  servod_obj = Servod(1)
  # 5 == number of interfaces on a FT4232H device
  for i in range(1, 5):
    if i == 2:
      # its an i2c interface ... see __init__ for details and TODO to make
      # this configureable
      servod_obj._interface_list[i].wr_rd(0x21, [0], 1)
    else:
      # its a gpio interface
      servod_obj._interface_list[i].wr_rd(0)

  server = SimpleXMLRPCServer(('localhost', 9999), allow_none=True)
  server.register_introspection_functions()
  server.register_multicall_functions()
  server.register_instance(servod_obj)
  logging.info('Listening on localhost port 9999')
  server.serve_forever()


if __name__ == '__main__':
  test()

  # simple client transaction would look like
  """remote_uri = 'http://localhost:9999' client = xmlrpclib.ServerProxy(remote_uri, verbose=False) send_str = "Hello_there" print "Sent " + send_str + ", Recv " + client.echo(send_str)

  """
