# Copyright 2019 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Servod device used by the server and watchdog."""

import json
import logging
import os
import threading

from servo import interface as _interface
from servo import drv as servo_drv
from servo import servo_dev_templates
from servo import servo_interfaces
from servo import servo_logging
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

  def __init__(self, dev_entry, config, interfaces=None, servod=None):
    """ServoDevice constructor.

    Args:
      dev_entry: ServoDeviceEntry that holds USB, device hierarchy, and devopts
                 information for this servo device.
      config: instance of SystemConfig containing all controls for
          particular Servod invocation
      interfaces: list of strings of interface types the server will instantiate
      servod: a pointer to access servod to invoke controls targetd at the servod
              daemon and other devices.

    Raises:
      ServoDeviceError: if unable to locate init method for particular interface
    """
    self.template = dev_entry.dev_template
    self.prefix = dev_entry.devopts.prefix
    self._logger = logging.getLogger('ServoDevice %s - %s'
      % (self.template.TYPE, self.prefix))
    self._logger.debug('')
    
    vendor = self.template.VID
    product = self.template.PID
    self._serial = dev_entry.serial
    board = dev_entry.devopts.board
    self.board = board
    self.base_board = None
    self.model = dev_entry.devopts.model
    if self.model:
      self.board += '_' + self.model
    self._ifaces_available = threading.Event()
    self.connect()
    self._reinit_capable = (vendor, product) in self.REINIT_CAPABLE
    self._disconnect_ok = False
    self._sysfs_path = dev_entry.dev_path
    # Associate the dev entry with a device
    self.dev_entry = dev_entry
    dev_entry.servo_device = self

    self.syscfg = config
    # Dict of Dict to map control name, function name to to tuple (params, drv)
    # Ex) _drv_dict[name]['get'] = (params, drv)
    self._drv_dict = {}

    if interfaces:
      self._manual_interfaces = True
      self._interfaces = interfaces
    else:
      self._manual_interfaces = False
      self._interfaces = servo_interfaces.INTERFACE_DEFAULTS[vendor][product]
    # list of objects (Fi2c, Fgpio) to physical interfaces (gpio, i2c) that ftdi
    # interfaces are mapped to
    self._interface_list = []
    # Whether an interface has initialized to be the proper interface
    self._interface_init = []
    self._sync_interface_lists()
    self._servod = servod

  def __repr__(self):
    return str(self)

  def __str__(self):
    return '%s (%04x:%04x) %s' % (self.template.TYPE, self.template.VID,
                                  self.template.PID, self._serial)

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
    return self.template.VID, self.template.PID, self._serial

  def is_connected(self):
    """Returns True if the device is connected."""
    return os.path.exists(self._sysfs_path)

  def get_prefix(self):
    """Get the prefix of the device."""
    return self.prefix

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

  def init_servo_interfaces(self, fault_tolerant=False):
    """Init the servo interfaces with the given interfaces.

    Args:
      fault_tolerant: If True, initialization error on an interface is logged but
                      not result in an exception. If false, initialization error on
                      any interface leads to an exception.

    Raises:
      ServoDeviceError: if unable to locate init method for particular interface.
    """
    self.clear_cached_drv()
    for i, interface_data in enumerate(self._interfaces):
      if self._interface_init[i]:
        # Ensure intialized interfaces are not reinitialized
        continue
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
      result = _interface.Build(name=name, index=i, vid=self.template.VID,
                                pid=self.template.PID, sid=self._serial,
                                interface_data=interface_data, servo_device=self)
      if isinstance(result, tuple):
        result_len = len(result)
        self._interface_list[i:(i + result_len)] = result
        self._interface_init[i:(i + result_len)] = True
      else:
        self._interface_list[i] = result
        self._interface_init[i] = True

  def set_board_and_model(self, board, model=None):
    """Set the board and model (if applicable) for this servo device.

    (1) check if interfaces need to change due to board
    (2) set board/model attributes
    (3) pull in board/model config file

    Args:
      board: board name
      model: model name

    Returns:
      True if configuration file found for board/model False otherwise
    """
    if not self._manual_interfaces:
      # Only if interfaces were determined, and not set manually, try to
      # get new interfaces from the board, otherwise, leave them be.
      try:
        interfaces = servo_interfaces.INTERFACE_BOARDS[board][self.template.VID][self.template.PID]
        for i, interface_data in enumerate(interfaces):
          if self._interfaces[i] != interface_data:
            # If an interface is overwritten ensure that it's marked as not
            # initialized regardless of previous status.
            self._interface_init[i] = False
          self._interfaces[i] = interface_data
        self._sync_interface_lists()
      except KeyError:
        # Likely adding a new board does not change interfaces. This is not
        # a fatal error.
        self._logger.debug('Cannot find interfaces for board %s.'
          ' Skip resetting the interfaces', board)
    cfg, board_id = self.syscfg.get_board_model_config(board, model)
    if cfg:
      self.syscfg.set_board_cfg(cfg)
    # |board_id| might include the |model| or not depending on whether it was used
    # to determine the board config.
    self.board = board_id
    if model and board_id and board_id.endswith(model):
      self.model = model
    if cfg:
      self.syscfg.add_cfg_file(filename=cfg)
      return True
    return False

  def _sync_interface_lists(self):
    """Ensure when interfaces are changed, bookkeeping is kept in sync."""
    # Extend the interface list if we need to.
    interfaces_len = len(self._interfaces)
    interface_list_len = len(self._interface_list)
    if interfaces_len > interface_list_len:
      self._interface_list += [None] * (interfaces_len - interface_list_len)
      self._interface_init += [False] * (interfaces_len - interface_list_len)

  def set_base_board(self, board):
    """Set the board probed from ec.

    Args:
      board: the board probed from ec (assuming this device is a dut controller)
    """
    self.base_board = board

  def reinitialize(self):
    """Reinitialize all interfaces that support reinitialization"""
    for i, interface in enumerate(self._interface_list):
      interface.reinitialize()
    # Indicate interfaces are safe to use again.
    device.connect()

  def close(self):
    """Servod turn down logic."""
    for i, interface in enumerate(self._interface_list):
      if interface and not isinstance(interface, _interface.empty.Empty):
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
      rd_val = self.syscfg.reformat_val(params, val)
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
      wr_val = self.syscfg.resolve_val(params, wr_val_str)

      drv.set(wr_val)

    # TODO(crbug.com/841097) Figure out why despite allow_none=True for both
    # xmlrpc server & client I still have to return something to appease the
    # marshall/unmarshall
    return True

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

    set_params, get_params = self.syscfg.lookup_control_params(control_name)

    for params in [get_params, set_params]:
      # |cmd| is guaranteed to be in each params.
      mode = params['cmd']
      # Get the most suitable drv given the servo instance.
      drv_prefix = self._get_servo_specific_param(params, 'drv', control_name)
      if drv_prefix == 'na':
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
      if None in [drv_prefix, interface_id]:
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
      drv_module = getattr(servo_drv, drv_prefix)
      drv_class = getattr(drv_module, string_utils.snake_to_camel(drv_prefix))
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

  def _get_servo_specific_param(self, params, param_key, control_name):
    """Get |param_key| from params by looking for servo specific params first.

    Find the candidate servos. First see if there's a more specific param_key
    that applies to this servo dev's type, before checking for the generic
    params key.

    1. [servo_type]_[params_key]
    2. [params_key]

    Args:
      params: params dictionary for a control
      param_key: identifier in the params dictionary to look for
      control_name: control name the params correspond to

    Returns:
      The best suited param value for param_key given the servo type or
      None if even the default is not defined.
    """
    candidates = ['%s_%s' % (self.template.TYPE, param_key)]
    candidates.append(param_key)
    for c in candidates:
      if c in params:
        self._logger.debug('Using %s parameter.', c)
        return params[c]
    self._logger.error('Unable to determine %s for %s', param_key, control_name)
    self._logger.error('params: %r', params)
    return None

  def clear_cached_drv(self):
    """Clear the cached drivers.

    The drivers are cached in the Dict _drv_dict when a control is got or set.
    When the servo interfaces are relocated, the cached values may become wrong.
    Should call this method to clear the cached values.
    """
    self._drv_dict = {}

  def doc_all(self):
    """Return all documenation for controls.

    Returns:
      string of <doc> text in config file (xml) and the params dictionary for
      all controls.

      For example:
      warm_reset             :: Reset the device warmly
      ------------------------> {'interface': '1', 'map': 'onoff_i', ... }
    """
    return self.syscfg.display_config()

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
    if self.syscfg.is_control(name):
      return self.syscfg.get_control_docstring(name)
    else:
      raise NameError('No control %s' % name)

  def hwinit(self, verbose, skip_controls):
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
      skip_controls: a list of controls not to hwinit. For a root hub device,
        if a control is already initialized for its children, do not initialized
        the control for this device.

    Returns:
      This function is called across RPC and as such is expected to return
      something unless transferring 'none' across is allowed. Hence adding a
      mock return value to make things simpler.
    """
    for control_name, value in self.syscfg.hwinit:
      if control_name in skip_controls:
        self._logger.debug("Skip initializing %s because it is already initialized"
          "for a child device.", control_name)
        continue
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
      if self.syscfg.is_control('active_dut_controller'):
        self.set('active_dut_controller', 'default')
    except servo_drv.active_v4_device.activeV4DeviceError as e:
      self._logger.debug('Could not set active device: %s', str(e))

    return True
  
  def get_root_hub_device(self):
    """Get the root hub device of this device, if it has one.
    
    This device might hang on another hub device.

    Returns:
      The root hub device of this device, or None if it does not have one.
    """
    root_entry = self.dev_entry.cluster_root
    if root_entry is None:
      return None
    return root_entry.servo_device

  def is_root_hub_device(self):
    """Check whether this device is a root hub device.
    
    Returns:
      True if this device is a root hub device, false otherwise.
    """
    return self.dev_entry.is_cluster_root()

  def get_child_devices(self):
    """Get the devices hanging on this device (directly or indirectly).
    
    Returns:
      A list of ServoDevice that hangs on this device directly or indirectly.
      If this device is not a root hub device, return an empty list.
    """
    child_devices = []
    if not self.is_root_hub_device():
      return child_devices
    for member in self.dev_entry.cluster_members:
      if member != self.dev_entry:
        child_devices.append(member.servo_device)
    return child_devices

  def to_json(self):
    """Serialize this device to a json string."""
    root_hub_device = self.get_root_hub_device()
    data = {"prefix" : self.prefix,
            "type" : self.template.TYPE,
            "vendor_id" : self.template.VID,
            "product_id": self.template.PID,
            "serial" : self._serial,
            "sysfs_path" : self._sysfs_path,
            "root_hub_device" : root_hub_device.prefix if root_hub_device else None,
            "child_devices": [dev.prefix for dev in self.get_child_devices()]}
    return json.dumps(data, indent=4)
