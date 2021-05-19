# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Templates for register and functional ADC control generation."""

import collections
import copy


class ADCTemplateError(Exception):
  """Error to throw on template issues."""
  pass


class ADCTemplate(object):
  """"Base class for all templates."""

  # NOTE: subclass should implement this.
  REG_IDX = dict()

  # The default implementation. If the ADC has variable length registers,
  # implement the right logic in the subclass.
  REG_LEN = collections.defaultdict(lambda: 2)

  # Lookup tables for register capabilities. Please overwrite in subclass
  # Whether the register is read only
  REG_RO = collections.defaultdict(lambda: False)
  # Whether the register is write only
  REG_WO = collections.defaultdict(lambda: False)
  # Whether the register is no_read (after write)
  REG_NORAW = collections.defaultdict(lambda: False)
  # Whether the register uses a servod map
  REG_MAP = collections.defaultdict(lambda: None)

  # NOTE: overwrite this with a valid name in the subclass.
  ADC_TYPE = None

  # Higher level abstractions supported by the ADC. This is a dict where the
  # key is the function suffix, and the value is the function subtype
  # e.g. {'mw': 'milliwatts'}
  # NOTE: overwrite these in the subclass.
  FUNCTIONS = None
  # Functions that are read-only. By default, all functions are RO as that's the
  # common case. Individual templates can expand
  FUNCTIONS_RO = collections.defaultdict(lambda: True)
  # Tags used for specific functions. Do not overwrite in the subtype as
  # this is to tie together the system regardless of which ADCs are used.
  FUNCTIONS_TAGS = collections.defaultdict(lambda: None)
  FUNCTIONS_TAGS.update(dict(shuntmv='shuntmv', mv='bus_voltage_rail',
                             ma='current_rail', mw='power_rail'))
  # Whether a function uses a map in servod.
  FUNCTIONS_MAP = collections.defaultdict(lambda: None)
  # Templates for string formatting to produce servod control docstrings.
  # These docstrings *must* be defined for *all* functions in |FUNCTIONS|
  # They will be used by feading the symbolic rail name into them e.g.
  # |docstring_template| % 'pp3300_dx'. So they need to support that operation.
  FUNC_DOCSTRING_TEMPLATES = None

  def __init__(self, addr, channel=0):
    """Setup the basics for register and function param generation.

    Args:
      addr: the 7-bit i2c addr for the ADC
      channel: extra info, depending on the ADC on how to use this

    Raises:
      ADCTemplateError: if |ADC_TYPE| is None
      ADCTemplateError: if |FUNCTIONS| is None
      ADCTemplateError: if |FUNC_DOCSTRING_TEMPLATES| and |FUNCTIONS| have
                        disjoint keys
    """
    if self.ADC_TYPE is None:
      raise ADCTemplateError('Please overwrite ADC_TYPE for your template.')
    self._addr = addr
    self._channel = channel
    if self.FUNCTIONS is None:
      raise ADCTemplateError('Please overwrite FUNCTIONS for your template.')
    if self.FUNCTIONS.keys() != self.FUNC_DOCSTRING_TEMPLATES.keys():
      raise ADCTemplateError('FUNCTIONS and FUNC_DOCSTRING_TEMPLATES not '
                             'matching in keys for %r' % self.ADC_TYPE)

  @property
  def base_params(self):
    """Helper to get started generating the params."""
    return dict(addr=self._addr, drv='i2c_reg_drv')

  def reg_offset(self, reg):
    """Base implementation of register offset. Just return the offset.

    Args:
      reg: str, name of register

    Returns:
      |REG_IDX|[|reg|]

    Raises:
      ADCTemplateError: if |reg| not in |REG_IDX|
    """
    if reg not in self.REG_IDX:
      raise ADCTemplateError('Unknown register %r' % reg)
    return self.REG_IDX[reg]

  def reg_len(self, reg):
    """Return the register length of |reg|.

    NOTE: if the ADC does not have one size, and the user manually edits
    the |REG_LEN| it is the users responsibility to make sure that all keys
    in REG_LEN are present in REG_IDX

    Args:
      reg: str, name of register

    Returns:
      |REG_LEN|[|reg|]

    Raises:
      ADCTemplateError: if |reg| not in |REG_IDX|
    """
    if reg not in self.REG_IDX:
      raise ADCTemplateError('Unknown register %r' % reg)
    return self.REG_LEN[reg]

  def reg_read_only(self, reg):
    """Whether |reg| is marked as a |reg_read_only| register.

    Args:
      reg: str, name of register

    Returns:
      |REG_RO|[|reg|]

    Raises:
      ADCTemplateError: if |reg| not in |REG_IDX|
    """
    if reg not in self.REG_IDX:
      raise ADCTemplateError('Unknown register %r' % reg)
    return self.REG_RO[reg]

  def reg_no_read(self, reg):
    """Whether |reg| is marked as a |reg_no_read| register.

    Args:
      reg: str, name of register

    Returns:
      |REG_NORAW|[|reg|]

    Raises:
      ADCTemplateError: if |reg| not in |REG_IDX|
    """
    if reg not in self.REG_IDX:
      raise ADCTemplateError('Unknown register %r' % reg)
    return self.REG_NORAW[reg]

  def reg_write_only(self, reg):
    """Whether |reg| is marked as a |reg_write_only| register.

    Args:
      reg: str, name of register

    Returns:
      |REG_WO|[|reg|]

    Raises:
      ADCTemplateError: if |reg| not in |REG_IDX|
    """
    if reg not in self.REG_IDX:
      raise ADCTemplateError('Unknown register %r' % reg)
    return self.REG_WO[reg]

  def reg_map(self, reg):
    """Whether |reg| is has a map.

    Args:
      reg: str, name of register

    Returns:
      |REG_MAP|[|reg|]

    Raises:
      ADCTemplateError: if |reg| not in |REG_IDX|
    """
    if reg not in self.REG_IDX:
      raise ADCTemplateError('Unknown register %r' % reg)
    return self.REG_MAP[reg]

  def func_read_only(self, func):
    """Whether |func| is marked as a |func_read_only|.

    Args:
      func: str, name of function

    Returns:
      |FUNCTIONS_RO|[|func|]

    Raises:
      ADCTemplateError: if |func| not in |FUNCTIONS|
    """
    if func not in self.FUNCTIONS:
      raise ADCTemplateError('Unknown function %r' % func)
    return self.FUNCTIONS_RO[func]

  def func_map(self, func):
    """Whether |func| has a map.

    Args:
      func: str, name of function

    Returns:
      |FUNCTIONS_MAP|[|func|]

    Raises:
      ADCTemplateError: if |func| not in |FUNCTIONS|
    """
    if func not in self.FUNCTIONS:
      raise ADCTemplateError('Unknown function %r' % func)
    return self.FUNCTIONS_MAP[func]

  def func_tags(self, func):
    """Whether |func| has a tags.

    Args:
      func: str, name of function

    Returns:
      |FUNCTIONS_TAGS|[|func|]

    Raises:
      ADCTemplateError: if |func| not in |FUNCTIONS|
    """
    if func not in self.FUNCTIONS:
      raise ADCTemplateError('Unknown function %r' % func)
    return self.FUNCTIONS_TAGS[func]

  def GetRegisterParams(self, interface=2):
    """Base implementation of register param retrieval.

    Should an ADC require more complex logic, just overwrite.

    Args:
      interface: the interface on which to communicate with ADCs.

    Returns:
      dict of dicts, where each key is the register name, and the
      value is the servod params to read/write to that register

    Raises:
      ADCTemplateError: if any register is both ro and wo
    """
    reg_params = {}
    for reg in self.REG_IDX:
      p = self.base_params
      p['interface'] = interface
      # c2d2 runs on interface |4| so add that as a special one as well.
      p['c2d2_interface'] = 4
      p['offset'] = self.reg_offset(reg)
      p['reg_len'] = self.reg_len(reg)
      p['fmt'] = 'hex'
      rmap = self.reg_map(reg)
      if rmap:
        p['map'] = rmap
      if self.reg_read_only(reg) and self.reg_write_only(reg):
        raise ADCTemplateError('%r cannot be read only and write only' %
                               reg)
      if self.reg_read_only(reg):
        p['read_only'] = ''
      elif self.reg_write_only(reg):
        p['write_only'] = ''
      if self.reg_no_read(reg):
        p['no_read'] = ''
      reg_params[reg] = p
    return reg_params

  def GetFunctionalParams(self, rsense, interface='servo'):
    """Implement in subclass.

    This needs to return at least the following keys
    - mv - bus voltage reading
    - ma - current reading
    - ma - power reading
    and can return additional keys if the ADC has additional functions.

    Args:
      rsense: float, sense resistor value.
      interface: the interface on which to perform higher level functions.
                 Note that most higher level functions require access to the
                 register controls, so it's almost always servo.

    Returns:
      dict of dicts, where each key is the function suffix, and the
      value is the servod params to execute the function correctly.

    Raises:
      ADCTemplateError: when |FUNCTIONS| lookup table is undefined
    """
    output = {}
    if self.FUNCTIONS is None:
      raise ADCTemplateError('Functions need to be defined.')
    for suffix, subtype in self.FUNCTIONS.items():
      output[suffix] = dict(drv=self.ADC_TYPE, rsense=rsense,
                            interface=interface, subtype=subtype)
      fmap = self.func_map(suffix)
      if fmap:
        output[suffix]['map'] = fmap
      if self.func_read_only(suffix):
        output[suffix]['cmd'] = 'get'
      tags = self.func_tags(suffix)
      if tags is not None:
        output[suffix]['tags'] = tags
    return output


class INA219Template(ADCTemplate):
  """Simple template for INA 219 as it only has 1 channel."""

  ADC_TYPE = 'ina219'

  REG_IDX = dict(cfg=0, shv=1, busv=2, pwr=3, cur=4, cal=5)

  # Add some maps to the REG_MAP
  REG_MAP = collections.defaultdict(lambda: None)
  REG_MAP.update(dict(cal='calibrate', cfg='ina219_cfg'))

  # Supported higher level functions
  FUNCTIONS = dict(mv='millivolts', mw='milliwatts', ma='milliamps',
                   shuntmv='shuntmv')

  FUNC_DOCSTRING_TEMPLATES = {}
  FUNC_DOCSTRING_TEMPLATES['mv'] = 'Bus Voltage of %r rail in millivolts'
  FUNC_DOCSTRING_TEMPLATES['ma'] = 'Current of %r rail in milliamps'
  FUNC_DOCSTRING_TEMPLATES['mw'] = 'Power of %r rail in milliwatts'
  FUNC_DOCSTRING_TEMPLATES['shuntmv'] = 'Shunt Voltage of %r rail in millivolts'


class INA231Template(INA219Template):
  """Simple template for INA 231 as it only has 1 channel."""

  ADC_TYPE = 'ina231'

  REG_IDX = dict(cfg=0, shv=1, busv=2, pwr=3, cur=4, cal=5, msken=6, alrt=7)

  # Add some maps to the REG_MAP
  REG_MAP = collections.defaultdict(lambda: None)
  REG_MAP.update(dict(cal='calibrate', cfg='ina231_cfg'))


class INA3221Template(INA219Template):
  """Template for INA 3221 that handles the different channels."""

  ADC_TYPE = 'ina3221'

  REG_IDX = dict(cfg=0, shv=1, busv=2, msken=15)

  # Add some maps to the REG_MAP
  REG_MAP = collections.defaultdict(lambda: None)
  REG_MAP.update(dict(cal='calibrate', cfg='ina3221_cfg'))

  def reg_offset(self, reg):
    """INA3221 has channel dependent offsets for busv and shv reg.

    Args:
      reg: str, name of register

    Returns:
      |REG_IDX|[|reg|]

    Raises:
      ADCTemplateError: if |reg| not in |REG_IDX|
      ADCTemplateError: if |self._channel| is None
    """
    if reg not in self.REG_IDX:
      raise ADCTemplateError('Unknown register %r' % reg)
    if self._channel is None:
      raise ADCTemplateError('Channel info required on INA 3221.')
    idx = self.REG_IDX[reg]
    if reg in ['busv', 'shv']:
      idx += self._channel * 2
    return idx


class PAC1934Template(ADCTemplate):
  """Template for PAC 1934 that handles the different channels."""

  ADC_TYPE = 'pac1934'

  REG_IDX = dict(refresh=0, ctrl=1, busv=0xf, cur=0x13, pwr=0x17,
                 refresh_v=0x1f, ctrl_act=0x21, neg_pwr_act=0x23)

  # Add 'refresh' shorthand for the refresh registers.
  REG_MAP = copy.copy(ADCTemplate.REG_MAP)
  REG_MAP.update(dict(refresh='refresh', refresh_v='refresh'))

  REG_LEN = collections.defaultdict(lambda: 2)
  REG_LEN.update(dict(refresh=0, refresh_v=0, pwr=4, neg_pwr_act=1,
                      ctrl=1, ctrl_act=1))

  REG_RO = collections.defaultdict(lambda: False)
  # These registers are all read only.
  REG_RO.update(dict(busv=True, pwr=True, cur=True, neg_pwr_act=True))

  REG_WO = collections.defaultdict(lambda: False)
  # Refresh is only used to write to it.
  REG_WO.update(dict(refresh=True, refresh_v=True))

  # Refresh is only used to write to it.
  REG_NORAW = collections.defaultdict(lambda: False)
  REG_NORAW.update(dict(refresh=True, refresh_v=True))

  # Functions supported by the pac family.
  FUNCTIONS = dict(mv='millivolts', mw='milliwatts', ma='milliamps',
                   res='resolution')
  # Supply the resolution map
  FUNCTIONS_MAP = collections.defaultdict(lambda: None)
  FUNCTIONS_MAP['res'] = 'resolution'
  # Mark relevant functions as r/w.
  FUNCTIONS_RO = copy.copy(ADCTemplate.FUNCTIONS_RO)
  FUNCTIONS_RO['res'] = False
  # Docstring templates for the functions.
  FUNC_DOCSTRING_TEMPLATES = {}
  FUNC_DOCSTRING_TEMPLATES['mv'] = 'Bus Voltage of %r rail in millivolts'
  FUNC_DOCSTRING_TEMPLATES['ma'] = 'Current of %r rail in milliamps'
  FUNC_DOCSTRING_TEMPLATES['mw'] = 'Power of %r rail in milliwatts'
  FUNC_DOCSTRING_TEMPLATES['res'] = 'Resolution of %r rail'

  def reg_offset(self, reg):
    """PAC ADC specific offset logic.

    Args:
      reg: str, name of register

    Returns:
      |REG_IDX|[|reg|]

    Raises:
      ADCTemplateError: if |reg| not in |REG_IDX|
      ADCTemplateError: if |self._channel| is None
    """
    if reg not in self.REG_IDX:
      raise ADCTemplateError('Unknown register %r' % reg)
    if self._channel is None:
      raise ADCTemplateError('Channel info required on PAC 1934.')
    idx = self.REG_IDX[reg]
    if reg in ['busv', 'cur', 'pwr']:
      # These are offset depending on which channel the user is trying to read.
      idx += self._channel
    return idx


class PAC19nextTemplate(PAC1934Template):
  """Template for PAC 19next that handles the different channels."""

  ADC_TYPE = 'pac19next'

  REG_IDX = dict(refresh=0, ctrl=1, busv=0xf, cur=0x13, pwr=0x17,
                 neg_pwr_fsr=0x1d, refresh_v=0x1f, ctrl_act=0x21,
                 neg_pwr_fsr_act=0x22)

  REG_LEN = collections.defaultdict(lambda: 2)
  REG_LEN.update(dict(refresh=0, refresh_v=0, pwr=4))

  REG_RO = collections.defaultdict(lambda: False)
  # These registers are all read only.
  REG_RO.update(dict(busv=True, pwr=True, cur=True, neg_pwr_fsr_act=True))


# A map to find the correct template.
lookup = {}
lookup['ina219'] = INA219Template
lookup['ina231'] = INA231Template
lookup['ina3221'] = INA3221Template
lookup['pac1934'] = PAC1934Template
lookup['pac19next'] = PAC19nextTemplate


def GetTemplate(name):
  """Return the template for ADC type |name|.

  Args:
    name: str, ADC template name

  Returns:
    ADCTemplate subclass corresponding to |name|.

  Raises:
    ADCTemplateError: if |name| is unknown.
  """
  if name not in lookup:
    raise ADCTemplateError('ADC type %r unknown.' % name)
  return lookup[name]
