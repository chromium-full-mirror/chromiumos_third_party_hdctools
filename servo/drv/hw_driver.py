# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Base class for servo drivers."""
import logging
import weakref

VALID_IO_TYPES = ['PU', 'PP']


class HwDriverError(Exception):
  """Exception class for HwDriver."""


def _get_io_type(params):
  """Retrieve IO driver type.

  Valid driver types are:
    PU == Pull-up
    PP == Push-pull

  Returns: string either 'PP' or 'PU'

  Raises: HwDriverError if:
     io type is invalid
     controls width > 1
  """
  if 'od' in params:
    width = params.get('width', 1)
    if width > 1:
      raise HwDriverError('Open drain not implemented for widths != 1')
    io_type = params['od'].upper()
    if io_type not in VALID_IO_TYPES:
      raise HwDriverError("Unrecognized io type (param 'od') %s" % io_type)
    return io_type
  return False


class HwDriver(object):
  """Base class for all hardware drivers."""

  # The list of params that an overlay needs to specific for the drv to be
  # effective. By default, that list is empty, though a drv implementation
  # can simply overwrite them.
  # Should a drv require different params for set and get, make sure that
  # 1. the drv uses the type specific |REQUIRED_GET_PARAMS| and
  # |REQUIRED_SET_PARAMS| and
  # 2. the overlay contains the right 'cmd' for each of them, or follows the cmd
  # convention for single-params controls.
  # If both set and get use the same required params, simplify define one and
  # set the other to that definition.
  REQUIRED_GET_PARAMS = []
  REQUIRED_SET_PARAMS = []

  def __init__(self, interface, params):
    """Driver constructor.

    Args:
      interface: FTDI interface object to handle low-level communication to
          control
      params: dictionary of params needed to perform operations on gpio driver

          params dictionary can have k=v pairs necessary to communicate with the
          underlying hardware.  Notables are:
            width: integer of width of the control in bits.
                Default: 1
            offset: integer of position of bit(s) with respect to lsb.
                Default: 0
            map: name string of map dictionary to use for unmapping / remapping
            fmt: function name string to call to format the result.

         Additional param keys will be described in sub-class drivers.

    Attributes:
      _logger: logger object.  May be accessed via sub-class
      _complement: a weak reference to the complement drv e.g. the controls'
                   set implementation if this is a get implementation.
      _interface: interface object.  May be accessed via sub-class
      _params: parameter dictionary.  May be accessed via sub-class
      _io_type: String of io type or False if not explicitly assigned.
    """
    self._logger = logging.getLogger(type(self).__name__)
    self._logger.debug('')
    self._complement = None
    self._interface = interface
    self._params = params
    # Check whether all required params are provided. if 'cmd' is in params,
    # use a type-specific |REQUIRED_PARAMS| e.g. set or get. If not, use the
    # generic one.
    cmd = self._params['cmd']
    if cmd == 'get':
      req_params = self.REQUIRED_GET_PARAMS
    elif cmd == 'set':
      req_params = self.REQUIRED_SET_PARAMS
    # The cmd is invalid here, raise an error. While this doesn't necessarily
    # cause an issue, we do not want config files laying around that misuse
    # cmd.
    else:
      raise HwDriverError("'cmd' param %r unknown. Use 'set' or 'get'" %
                          (cmd,))
    for a in req_params:
      # Empty |req_params| leads to no checks being performed.
      if a not in self._params:
        raise HwDriverError('Required param %r not in params' % (a,))
    # |set| cmd might define choices that show what are valid choices to be
    # set.
    self._choices = None
    if 'choices' in self._params:
      self._choices = self._params['choices'].split(',')
      self._logger.debug('Valid input choices: %s', self._choices)
    self._io_type = _get_io_type(params)

  def __str__(self):
    """Return a string representation of this drv."""
    return '%s[%s](%s)' % (self._params['control_name'],
                           type(self).__name__, self._mode())

  def __repr__(self):
    """Return same as __str__()"""
    return str(self)

  def _is_set(self):
    """Whether the |self| is a driver instance for 'set'.

    Returns:
      True if 'cmd' is 'set'
    """
    return self._mode() == 'set'

  def _is_get(self):
    """Whether the |self| is a driver instance for 'get'.

    Returns:
      True if 'cmd' is 'get'
    """
    return self._mode() == 'get'

  def _mode(self):
    """Mode of this drv, either 'set' or 'get'.

    Returns:
      contents of self._params['cmd']
    """
    return self._params['cmd']

  def set_complement(self, complement_drv):
    """set |complement_drv| to this drv's complement and vice-versa

    Args:
      complement_drv: this control drv's complement

    Raises:
      HwDriverError: if |complement_drv| and |self| have the same mode (set,get)
      HwDriverError: if |complement_drv| or |self| already have a complement
    """
    # pylint: disable=protected-access
    # Access required as the goal is to link both the classes.
    if complement_drv._mode() == self._mode():
      raise HwDriverError('Cannot set %r as the complement of %r.' %
                          (complement_drv, self))

    # Note: this policy can be changed if necessary, but for now it seems safer
    # to enforce that complements are set once. There is no known reason so far
    # to have a complement drv dynamically change at runtime after the first
    # time it is set. If this is changed in the future, consider that we do
    # not want to have open loops i.e. if a complement is cleaned up, it needs
    # to be cleaned up from both sides.
    for d in [self, complement_drv]:
      if d._complement is not None:
        # |d._complement| is a weakref. Casting it to a string before passing it
        # to %r ensures it prints the actual object class and not that it's
        # a weakref.
        raise HwDriverError('drv %r already has a complement: %r' %
                            (d, str(d._complement)))

    self._complement = weakref.proxy(complement_drv)
    complement_drv._complement = weakref.proxy(self)
    # |self._complement| is a weakref. Casting it to a string before passing it
    # to %r ensures it prints the actual object class and not that it's a
    # weakref.
    self._logger.debug('Set drvs %r and %r as each others complements.',
                       self, str(self._complement))

  def _get_complement(self):
    """Return the complement drv.

    Returns:
      self._complement i.e. the complement drv. Can be None if not set yet.
    """
    return self._complement

  def _check_input(self, value):
    """Check whether |value| is a valid input.

    If |self._choices| is defined, then |value| has to be in one of those
    choices.

    Note: the comparison here is done after casting value to a string.

    Args:
      value: value to check

    Raises:
      HwDriverError: if |self._choices| is defined and str(|value|) is not in it
    """
    if self._choices and str(value) not in self._choices:
      raise HwDriverError('%r not a valid input choice' % value)

  def _set(self, logical_value):
    """Set the control to |logical_value| or delegate to subtype

    If the driver is deemed worthy of more complication, this method will
    dispatch to the subclasses "_Set_%s" % params['subtype'] method.

    TODO(tbroch) logical_value will need float support for DAC's

    Args:
      logical_value: Integer value to write to hardware.

    Returns:
      Value from subclass method.

    Raises:
      HwDriverError: If unable to locate subclass method.
      NotImplementedError: There's no subtype param and _set() unimplemented
        in the subclass.
    """
    if 'subtype' in self._params:
      fn_name = '_Set_%s' % self._params['subtype']
      if not hasattr(self, fn_name):
        raise HwDriverError('Finding set function %s' % (fn_name,))
    else:
      raise NotImplementedError('Set should be implemented in subclass.')
    return getattr(self, fn_name)(logical_value)

  def set(self, logical_value):
    """Set hardware control to a particular value.

    In the case of simpler drivers, a single 'set' method is
    implemented in the subclass.

    This function is a safety wrapper around _set() to check that
    |lt ogical_value| is a valid choice before passing it down if valid choices
    have been defined.

    If a (simple) driver desires more safety, by checking that input values
    are valid, it can implement '_set' rather than 'set'. The only difference
    is that before dispatching to '_set', the input value will be checked to
    ensure it valid.

    Args:
      logical_value: Integer value to write to hardware.

    Returns:
      Value from _set()
    """
    self._logger.debug('logical_value = %s', logical_value)
    self._check_input(logical_value)
    return self._set(logical_value)

  def get(self):
    """Get control value and return it

    In the case of simpler drivers, a single 'get' method is
    implemented in the subclass.  If however the driver is deemed
    worthy of more complication, this method will dispatch to the
    subclasses "_Get_%s" % params['subtype'] method.

    Returns:
      Value from subclass method.

    Raises:
      HwDriverError: If unable to locate subclass method.
      NotImplementedError: There's no subtype param and get method
        wasn't implemented in the subclass.
    """
    self._logger.debug('')
    if 'subtype' in self._params:
      fn_name = '_Get_%s' % self._params['subtype']
      if hasattr(self, fn_name):
        return getattr(self, fn_name)()
      else:
        raise HwDriverError('Finding get function %s' % fn_name)
    else:
      raise NotImplementedError('Get method should be implemented in subclass.')

  def _create_logical_value(self, hw_value):
    """Create logical value using mask & offset.

    logical_value = (hw_value & mask) >> offset

    In MOST cases, subclass drivers should use this for data coming back from
    get method.

    Args:
      hw_value: value to convert to logical value

    Returns:
      integer in logical representation
    """
    (offset, mask) = self._get_offset_mask()
    if offset is not None:
      fmt_value = (hw_value & mask) >> offset
    else:
      fmt_value = hw_value
    return fmt_value

  def _create_hw_value(self, logical_value):
    """Create hardware value using mask & offset.

    hw_value = (logical_value << offset) & mask

    In MOST cases, subclass drivers should use this for data going to value
    argument in set method.

    Args:
      logical_value: value to convert to hardware value

    Returns:
      integer in hardware representation

    Raises:
      HwDriverError: when logical_value would assert bits outside the mask
    """
    (offset, mask) = self._get_offset_mask()
    if offset is not None:
      hw_value = (logical_value << offset)
      if hw_value != (hw_value & mask):
        raise HwDriverError('format value asserts bits outside mask')
    else:
      hw_value = logical_value
    return hw_value

  def _get_offset_mask(self):
    """Retrieve offset and mask.

    Subclasses should use to obtain &| create these ints from param dict

    Returns:
      tuple (offset, mask) where:
        offset: integer offset or None if not defined in param dict
        mask: integer mask or None if offset not defined in param dict
      For example if width=2 and offset=4 then mask=0x30

    """
    if 'offset' in self._params:
      offset = int(self._params['offset'])
      if 'width' not in self._params:
        mask = 1 << offset
      else:
        mask = (pow(2, int(self._params['width'])) - 1) << offset
    else:
      offset = None
      mask = None
    return (offset, mask)
