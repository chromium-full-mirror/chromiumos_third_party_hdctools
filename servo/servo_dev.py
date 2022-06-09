# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Servod device used by the server and watchdog."""

import logging
import os
import threading

from servo import interface as _interface
from servo import drv as servo_drv
from servo import servo_dev_templates
from servo import servo_interfaces
from servo import servo_logging
from servo import servo_postinit
from servo.utils import string_utils
import servo.utils.usb_hierarchy as usb_hierarchy

HwDriverError = servo_drv.hw_driver.HwDriverError


class ServoDeviceError(Exception):
  """General servo device error class."""
  pass


class ServoDevice(object):
  """Device class that each corresponds to a physical servo device.
  """

  # Reinit capable devices.
  REINIT_CAPABLE = set([servo_dev_templates.CcdCr50.ID, servo_dev_templates.CcdTi50.ID])

  # Available attempts to reconnect a device
  REINIT_ATTEMPTS = 100

  # Exceptions to count as known or ordinary.  Any errors that aren't instances
  # of these (or their subclasses) will be logged with "Please take a look."
  KNOWN_EXCEPTIONS = (AttributeError, NameError, HwDriverError)

  # Timeout to wait for interfaces to become available again if reinitialization
  # is taking place. In seconds. This is supposed to recover from brief resets.
  # If the interface disappears for more than 5 seconds, then someone probably
  # intentionally disconnected the device. Servod shouldn't be responsible for
  # waiting for the device during an intentional disconnect.
  INTERFACE_AVAILABILITY_TIMEOUT = 5

  def __init__(self, template, config, name, serialname=None, interfaces=None, board='',
               model='', version=None, servod=None):
    """ServoDevice constructor.

    Args:
      template: ServoDevTemplate class for this servo device
      config: instance of SystemConfig containing all controls for
          particular Servod invocation
      name: prefix/name of the ServoDevice recognized by Servod
      serialname: string of device serialname/number as defined in FTDI eeprom.
      interfaces: list of strings of interface types the server will instantiate
      version: String. Servo board version. Examples: servo_v1, servo_v2,
               servo_v2_r0, servo_v3, servo_v4_with_servo_micro_interface
      board: board name. e.g. octopus, coral, or scarlet.
      model: model name of a given board. e.g. fleex, ampton, or apel.
      servod: TODO(konmari) - a temporary hack to access servod to invoke controls with
                              interface 'servo' and access all other devices. Need to
                              reevaluate if this is the proper approach later.
    Raises:
      ServoDeviceError: if unable to locate init method for particular interface
      ServoDeviceError: the usb device path isn't found.
    """
    self._logger = logging.getLogger('ServoDevice %s - %s' % (template.TYPE, serialname))
    self._logger.debug('')
    self._template = template
    vendor = self._template.VID
    product = self._template.PID
    self._serial = serialname
    self._base_version = version
    self._version = version
    self._base_board = ''
    self._board = board
    if model:
      self._board += '_' + model
    self._model = model
    self._ifaces_available = threading.Event()
    self.connect()
    self._reinit_capable = (vendor, product) in self.REINIT_CAPABLE
    self._disconnect_ok = False
    sysfs_path = usb_hierarchy.Hierarchy.GetUsbDeviceSysfsPath(
                 vendor, product, serialname)
    self._name = name
    # TODO(konmari): a temporary hack to access servod to invoke controls with
    #                interface 'servo' and access all other devices.
    self._servod = servod
    self._servod.add_device(vendor, product, serialname, name, device=self)

    if not sysfs_path:
      raise ServoDeviceError('No sysfs path found for device.')
    self._sysfs_path = sysfs_path
    self._syscfg = config
    # Dict of Dict to map control name, function name to to tuple (params, drv)
    # Ex) _drv_dict[name]['get'] = (params, drv)
    self._drv_dict = {}
    # list of objects (Fi2c, Fgpio) to physical interfaces (gpio, i2c) that ftdi
    # interfaces are mapped to
    self._interface_list = []

    # TODO(konmari): temporarily use the main device to execute all interface
    #                operations and make it no-op for other devices
    if name != servo_dev_templates.MAIN_DEV_PREFIX:
      return
    if not interfaces:
      try:
        interfaces = servo_interfaces.INTERFACE_BOARDS[board][vendor][product]
      except KeyError:
        interfaces = servo_interfaces.INTERFACE_DEFAULTS[vendor][product]
    self._interfaces = interfaces
    self.init_servo_interfaces(vendor, product, serialname, interfaces)
    servo_postinit.post_init(self)
    self._syscfg.finalize()

  def __repr__(self):
    return str(self)

  def __str__(self):
    return '%s (%04x:%04x) %s' % (self._version, self._template.VID,
                                  self._template.PID, self._serial)

  def wait(self, wait_time):
    """Wait for the device to reconnect and the interfaces to become available.

    Args:
        wait_time: time to wait in seconds

    Raises:
      ServoDeviceError: if the interfaces aren't available within timeout period
    """
    if not self._ifaces_available.wait(wait_time):
      raise ServoDeviceError('Timed out waiting for interfaces to become '
                             'available.')

  def connect(self):
    """The device connected."""
    # Mark that the interfaces are available.
    self._ifaces_available.set()
    self._reinit_attempts = self.REINIT_ATTEMPTS

  def disconnect(self):
    """The device disconnected."""
    # Mark that the interfaces are unavailable.
    self._ifaces_available.clear()

    # If it's ok for the device to disconnect, allow it to stay disconnected
    # indefinitely.
    if self._disconnect_ok:
      return

    self._reinit_attempts -= 1
    self._logger.debug('%d reinit attempts remaining.', self._reinit_attempts)

  def reinit_ok(self):
    return self._reinit_capable and (self._reinit_attempts > 0)

  def get_id(self):
    """Return a tuple of the device information."""
    return self._template.VID, self._template.PID, self._serial

  def is_connected(self):
    """Returns True if the device is connected."""
    return os.path.exists(self._sysfs_path)

  def get_name(self):
    """Get the name."""
    return self._name

  def set_name(self, name):
    """Set the name."""
    self._name = name

  def set_disconnect_ok(self, disconnect_ok):
    """Set if it's ok for the device to disconnect.

    Don't decrease the reinit_attempts count if this is True. The device can
    be disconnected forever as long as disconnect is ok.

    Args:
      disconnect_ok: True if it's ok for the device to disconnect.
    """
    self._disconnect_ok = disconnect_ok
    self._reinit_attempts = self.REINIT_ATTEMPTS

  def disconnect_is_ok(self):
    """Returns True if it's ok for the device to disconnect."""
    return self._disconnect_ok

  def usb_devnum(self):
    """Return the current usb devnum."""
    return usb_hierarchy.Hierarchy.DevNumFromSysfs(self._sysfs_path)

  def get_interface_list(self):
    """Return interface_list."""
    return self._interface_list

  # TODO(konmari): to be cleaned up after interfaces are refactored properly.
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
      ServoDeviceError if unable to locate init method for particular interface.
    """
    # Extend the interface list if we need to.
    interfaces_len = len(interfaces)
    interface_list_len = len(self._interface_list)
    if interfaces_len > interface_list_len:
      # Fill with dummies.
      self._interface_list += [_interface.empty.Empty()] * (interfaces_len -
                                                            interface_list_len)

    for i, interface_data in enumerate(interfaces):
      if type(interface_data) is dict:
        name = interface_data['name']
        # Store interface index for those that care about it.
        interface_data['index'] = i
      elif type(interface_data) is str:
        if interface_data in ['empty', 'ftdi_empty']:
          # 'empty' reserves the interface for future use.  Typically the
          # interface will be managed by external third-party tools like
          # openOCD for JTAG or flashrom for SPI.  In the case of servo V4,
          # it serves as a placeholder for servo micro interfaces.
          continue
        name = interface_data
      else:
        raise ServoDeviceError('Illegal interface data type %s'
                          % type(interface_data))

      self._logger.info('Initializing interface %d to %s', i, name)
      result = _interface.Build(name=name, index=i, vid=vendor, pid=product,
                                sid=serialname, interface_data=interface_data,
                                servo_device=self)
      if isinstance(result, tuple):
        result_len = len(result)
        self._interface_list[i:(i + result_len)] = result
      else:
        self._interface_list[i] = result

  def reinitialize(self):
    """Reinitialize all interfaces that support reinitialization"""
    for i, interface in enumerate(self._interface_list):
      interface.reinitialize()
    # Indicate interfaces are safe to use again.
    device.connect()

  def close(self):
    """Servod turn down logic."""
    for i, interface in enumerate(self._interface_list):
      if not isinstance(interface, _interface.empty.Empty):
        # Only print this on real interfaces and not place holders.
        self._logger.info('Turning down interface %d', i)
        interface.close()

  def get(self, name):
    """Get control value.

    Args:
      name: name string of control

    Returns:
      Response from calling drv get method.  Value is reformatted based on
      control's dictionary parameters

    Raises:
      HwDriverError: Error occurred while using drv
      ServoDeviceError: if interfaces are not available within timeout period
    """
    with servo_logging.WrapGetCall(
            name, known_exceptions=self.KNOWN_EXCEPTIONS) as wrapper:
      (params, drv, device) = self._get_param_drv(name)
      if device in self._servod._devices:
        self._servod._devices[device].wait(self.INTERFACE_AVAILABILITY_TIMEOUT)

      val = drv.get()
      rd_val = self._syscfg.reformat_val(params, val)
      wrapper.got_result(rd_val)
      return rd_val

  def set(self, name, wr_val_str):
    """Set control.

    Args:
      name: name string of control
      wr_val_str: value string to write.  Can be integer, float or a
          alpha-numerical that is mapped to a integer or float.

    Raises:
      HwDriverError: Error occurred while using driver
      ServoDeviceError: if interfaces are not available within timeout period
    """
    with servo_logging.WrapSetCall(
            name, wr_val_str, known_exceptions=self.KNOWN_EXCEPTIONS):
      (params, drv, device) = self._get_param_drv(name, False)
      if device in self._servod._devices:
        self._servod._devices[device].wait(self.INTERFACE_AVAILABILITY_TIMEOUT)
      wr_val = self._syscfg.resolve_val(params, wr_val_str)

      drv.set(wr_val)

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

    # TODO(crbug.com/841097) Figure out why despite allow_none=True for both
    # xmlrpc server & client I still have to return something to appease the
    # marshall/unmarshall
    return True
  
  # TODO(konmari) - to be cleaned up after interfaces are separated to each servo device
  def _get_param_drv(self, control_name, is_get=True):
    """Get access to driver for a given control.

    Note, some controls have different parameter dictionaries for 'getting' the
    control's value versus 'setting' it.  Boolean is_get distinguishes which is
    being requested.

    Args:
      control_name: string name of control
      is_get: boolean to determine

    Returns:
      tuple (params, drv, device_info) where:
        params: param dictionary for control
        drv: instance object of driver for particular control
        device_info: servo device information

    Raises:
      ServoDeviceError: Error occurred while examining params dict
    """
    self._logger.debug('')
    # if already setup just return tuple from driver dict
    if control_name in self._drv_dict:
      if is_get and ('get' in self._drv_dict[control_name]):
        return self._drv_dict[control_name]['get']
      if not is_get and ('set' in self._drv_dict[control_name]):
        return self._drv_dict[control_name]['set']

    self._logger.debug('Did not find cached drvs for %r. Will generate '
                       'both set and get drvs.', control_name)

    set_params, get_params = self._syscfg.lookup_control_params(control_name)

    for params in [get_params, set_params]:
      # |cmd| is guaranteed to be in each params.
      mode = params['cmd']
      # Get the most suitable drv given the servo instance.
      drv_name = self._get_servo_specific_param(params, 'drv', control_name)
      if drv_name == 'na':
        # 'na' drv can be used to selectively turn controls into noops for
        # a given servo hardware. Ensure that there is an interface.
        params.setdefault('interface', 'servo')
        self._logger.debug('Setting interface to default to %r for %r unless '
                           ' defined  in params, as drv is %r.', 'servo',
                           control_name, 'na')
        # Setting input_type to str allows all inputs through enabling a true
        # noop
        params.update({'input_type': 'str'})

      interface_id = self._get_servo_specific_param(params, 'interface',
                                                    control_name)
      if None in [drv_name, interface_id]:
        raise ServoDeviceError('No drv/interface for control %r found' %
                          control_name)

      # this control only needs cross-servo-device communication and does not
      # need hardware interface for low-level communication
      if interface_id == 'servo':
        interface = None
        servod = self._servod
      # this control only needs hardware interface for low-level communication
      # and does not need cross-servo-device communication
      else:
        index = int(interface_id)
        interface = self._interface_list[index]
        servod = None

      device_info = None
      if hasattr(interface, 'get_device_info'):
        device_info = interface.get_device_info()
      drv_module = getattr(servo_drv, drv_name)
      drv_class = getattr(drv_module, string_utils.snake_to_camel(drv_name))
      drv = drv_class(interface, params, servod) if servod else drv_class(interface, params)
      if control_name not in self._drv_dict:
        self._drv_dict[control_name] = {}
      # Store the information in the right mode.
      self._drv_dict[control_name][mode] = (params, drv, device_info)
    # At this point, both 'set' and 'get' have been generated. The last thing
    # left to do is to pass each one of them a weak reference to the other.
    # This ensures that if a control needs to do read/modify/write for
    # instance it can do so without much overhead.
    _, set_drv, _ = self._drv_dict[control_name]['set']
    _, get_drv, _ = self._drv_dict[control_name]['get']
    set_drv.set_complement(get_drv)
    # Run the method again, as it will find the entries now in the cache.
    return self._get_param_drv(control_name, is_get)

  # TODO(konmari) - to be cleaned up after interfaces are separated to each servo device
  def _get_servo_specific_param(self, params, param_key, control_name):
    """Get |param_key| from params by looking for servo specific params first.

    Find the candidate servos.  Using servo_v4 with a servo_micro connected as
    example, the following shows the priority for selecting the interface.

    1. The full name. (e.g. - 'servo_v4_with_servo_micro_interface')
    2. servo_micro_interface
    3. servo_v4_interface
    4. Fallback to the default, interface.

    Args:
      params: params dictionary for a control
      param_key: identifier in the params dictionary to look for
      control_name: control name the params correspond to

    Returns:
      The best suited param value for param_key given the servo type or
      None if even the default is not defined.
    """
    candidates = [self._version]
    if '_with_' in self._version:
      v4, raw_dut_device = self._version.split('_with_')
      dut_devices = raw_dut_device.split('_and_')
      # NOTE(coconutruben): all of this nonsense is going away with the new
      # servod and is to bridge the time until then. Please forgive the below
      # until then.
      if '.' in control_name and not control_name.startswith('root'):
        # TODO(coconutruben): remove the root exception here once multi device
        # support is merged.
        # In the current implementation, the only case where a '.' (a prefix)
        # is in the control name is when there is a dual instance with micro and
        # ccd on a v4.
        dut_device = dut_devices[1]
      else:
        # In the normal control name, we need to make sure the version used
        # does not include the potential _and_ portion from a dual instance.
        dut_device = dut_devices[0]
      candidates.extend([dut_device, v4])
    candidates = ['%s_%s' % (c, param_key) for c in candidates]
    candidates.append(param_key)
    for c in candidates:
      if c in params:
        self._logger.debug('Using %s parameter.', c)
        return params[c]
    self._logger.error('Unable to determine %s for %s', param_key, control_name)
    self._logger.error('params: %r', params)
    return None

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

  def hwinit(self, verbose=False):
    """Initialize all controls.

    These values are part of the system config XML files of the form
    init=<value>.  This command should be used by clients wishing to return the
    servo and DUT its connected to a known good/safe state.

    Note that initialization errors are ignored (as in some cases they could
    be caused by DUT firmware deficiencies). This might need to be fine tuned
    later.

    Args:
      verbose: boolean, if True prints info about control initialized.
        Otherwise prints nothing.

    Returns:
      This function is called across RPC and as such is expected to return
      something unless transferring 'none' across is allowed. Hence adding a
      mock return value to make things simpler.
    """
    for control_name, value in self._syscfg.hwinit:
      try:
        # Workaround for bug chrome-os-partner:42349. Without this check, the
        # gpio will briefly pulse low if we set it from high to high.
        if self.get(control_name) != value:
          self.set(control_name, value)
        if verbose:
          self._logger.info('Initialized %s to %s', control_name, value)
      except Exception as e:
        self._logger.error(
            'Problem initializing %s -> %s', control_name, value)
        self._logger.error(str(e))
        self._logger.error('Please consider verifying the logs and if the '
                           'error is not just a setup issue, consider filing '
                           'a bug. Also checkout go/servo-ki.')

    # If there is the control of 'active_dut_controller',
    # set active_dut_controller to the default device as initialization.
    try:
      if self._syscfg.is_control('active_dut_controller'):
        self.set('active_dut_controller', 'default')
    except servo_drv.active_v4_device.activeV4DeviceError as e:
      self._logger.debug('Could not set active device: %s', str(e))

    return True