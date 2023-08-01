# Copyright 2012 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""System configuration module."""

import collections
import copy
import functools
import glob
import logging
import os
import re
import xml.etree.ElementTree


# valid tags in system config xml.  Any others will be ignored
MAP_TAG = 'map'
CONTROL_TAG = 'control'
CLOBBER_ATTR = 'clobber_ok'
CLOBBER_NEVER = 'never'
CLOBBER_PATCH = 'patch'
CLOBBER_UPDATE = 'update'
CLOBBER_FULL = 'full'
# from low to high
CLOBBER_RANK = {v: i for i, v in enumerate(
    [None, CLOBBER_NEVER, CLOBBER_PATCH, CLOBBER_UPDATE, CLOBBER_FULL])}
CONTENT_TAG = 'content'
CONTENT_ITEM_TAG = 'item'
CONTENT_ITEM_KEY_ATTR = 'key'
CONTENT_ITEM_TYPE_ATTR = 'type'
CONTENT_PARAM = 'CONTENT'
SYSCFG_TAG_LIST = [MAP_TAG, CONTROL_TAG]
ALLOWABLE_INPUT_TYPES = {'float': float, 'int': int, 'str': str}

# A control to use when set/get is explicitly not defined for a control.
UNDEF_CONTROL_DICT = {'drv': 'undefined',
                      'interface': 'servo',
                      'input_type': 'str'}

# Valid pattern for control names and aliases
IDENTIFIER_RE = re.compile(r'[a-z][a-z0-9_]+')

# pylint: disable=g-bad-exception-name
# TODO(coconutruben): figure out if it's worth it to rename this so that it
# removes the 'stutter'
class SystemConfigError(Exception):
  """Error class for SystemConfig."""


class SystemConfig(object):
  """SystemConfig Class.

  System config files describe how to talk to various pieces on the device under
  test.  The system config may be broken up into multiple file to make it easier
  to share configs among similar DUTs.  This class has the support to take in
  multiple SystemConfig files and treat them as one unified structure


  SystemConfig files are written in xml and consist of four main elements

  0. Include : Ability to include other config files

  <include>
    <name>servo_loc.xml</name>
  </include>

  NOTE, All includes in a file WILL be sourced prior to any other elements in
  the XML.

  1. Map : Allow user-friendly naming for things to abstract
  certain things like on=0 for things that are assertive low on
  actual h/w

  <map>
    <name>onoff_i</name>
    <doc>assertive low map for on/off</doc>
    <params on="0" off="1" />
  </map>

  2. Control : Bulk of the system file.  These elements are
  typically gpios, adcs, dacs which allow either control or sampling
  of events on the h/w. Controls should have a 1to1 correspondence
  with hardware elements between control system and DUT.

  <control>
    <name>warm_reset</name>
    <doc>Reset the device warmly</doc>
    <params interface="1" drv="gpio" offset="5" map="onoff_i" />
  </control>

  Some controls also use the a <content> element inside the <params> element as
  input.  This text, when present, is interpreted into an arbitrarily nested
  structure of Python dict and list objects, ultimately containing str and None
  values.  For example:

  <control>
    <name>my_control</name>
    <doc>Does cool stuff!</doc>
    <params drv="mydriver">
      <content>
        <item key="somefield">5</item>
        <item key="list_field">
          <item>one two three</item>
          <item></item>
          <item>foobar</item>
        </item>
      </content>
    </params>
  </control>

  That content would get parsed into:
    {'somefield': '5',
     'list_field': ['one two three', None, 'foobar']}

  Or:
    {'somefield': '5',
     'list_field': ['one two three', '', 'foobar']}

  It is not guaranteed whether empty <item> text results in None or '' (empty
  string).  Drivers should handle either case and not discriminate between them.

  The <content> element is allowed to directly contain text instead of nested
  elements.  For example:

  <control>
    <name>my_control</name>
    <doc>Does cool stuff!</doc>
    <params drv="mydriver">
      <content>-29.5</content>
    </params>
  </control>

  That content would get parsed into:
    '-29.5'

  Rules for <content> sections:
    * <item> is the only element permitted within <content> or <item>.
    * If one <item> in a section uses key= attribute, then all must.
    * Use of key= attribute in <item> indicates a map entry, which gets placed
      into a Python dict.
    * The behavior with duplicate keys in a map is undefined (and could be or
      become an error).
    * Use of <item> without key= attribute indicates a list.
    * The behavior if map and list <item> are mixed together in one parent
      element is undefined (and could be or become an error).
    * The behavior if any attributes not described above are used is undefined
      (and could be or become an error).
    * When <content> or <item> contains nested elements then any text content
      directly in the parent element should be whitespace-only, and is ignored.
    * The behavior with non-whitespace text alongside nested <item> elements is
      undefined (and could be or become an error).
    * There is no policy limit to how deep <item> can be nested, however there
      may be practical implementation limits, don't go nuts.

  The structure enforced by <content> / <item> is designed to be easily ported
  to other possible config file formats besides XML, and it avoids exposing
  drivers to XML.

  Public Attributes:
    control_tags: a dictionary of each base control and their tags if any
    aliases: a dictionary of an alias mapped to its base control name
    syscfg_dict: 3-deep dictionary created when parsing system files.  Its
        organized as [tag][name][type] where:
        tag: map | control
        name: string name of tag element
        type: data type of payload either, doc | get | set presently
          doc: string describing the map or control
          get: a dictionary for getting values from named control
          set: a dictionary for setting values to named control
    hwinit: list of control tuples (name, value) to be initialized in order

  Private Attributes:
    _loaded_xml_files: set of filenames already loaded to avoid sourcing XML
      multiple times.
  """

  def __init__(self):
    """SystemConfig constructor."""
    self._logger = logging.getLogger('SystemConfig')
    self._logger.debug('')
    self.control_tags = collections.defaultdict(set)
    self.aliases = {}
    self.syscfg_dict = collections.defaultdict(dict)
    self.hwinit = []
    self._loaded_xml_files = []
    self._board_cfg = None

  def find_cfg_file(self, filename):
    """Find the filename for a system XML config file.

    If the provided `filename` names a valid file, use that.
    Otherwise, `filename` must name a file in the 'data'
    subdirectory stored with this module.

    Returns the path selected as described above; if neither of the
    paths names a valid file, return `None`.

    Args:
      filename: string of path to system file ( xml )

    Returns:
      string full path of |filename| if it exists, otherwise None
    """
    if os.path.isfile(filename):
      return filename
    default_path = os.path.join(os.path.dirname(__file__), 'data')
    fullname = os.path.join(default_path, filename)
    if os.path.isfile(fullname):
      return fullname
    return None

  @staticmethod
  def tag_string_to_tags(tag_str):
    """Helper to split tag string into individual tags."""
    return tag_str.split(',')

  def get_all_cfg_names(self):
    """Return all XML config file names.

    Returns:
      A list of file names.
    """
    exclude_re = re.compile(r'servo_.*_overlay\.xml')
    pattern = os.path.join(os.path.dirname(__file__), 'data', '*.xml')

    cfg_names = []
    for name in glob.glob(pattern):
      name = os.path.basename(name)
      if not exclude_re.match(name):
        cfg_names.append(name)
    return cfg_names

  def set_board_cfg(self, filename):
    """Save the filename for the board config."""
    self._board_cfg = filename

  def get_board_cfg(self):
    """Return the board filename."""
    return self._board_cfg

  @staticmethod
  def _parse_content(content):
    """Parse a <content> structure from a control's params element.

    Args:
      content: xml.etree.ElementTree.Element - the <content> XML element
      stack: [(element, callback)] - list of 2-item tuples, each containing:
        element: xml.etree.ElementTree.Element - <content> or <item> XML element
        callback: callable(object) - This will be called exactly once, in order

    Returns:
      None or str or list or dict
    """
    if content is None:
      return None

    retval_list = []
    # [(element, callback)] - list of 2-item tuples of:
    # element: xml.etree.ElementTree.Element - <content> or <item> XML element
    # callback: callable(object) - This will be called exactly once, with the
    #     value to use for this element.
    stack = [(content, retval_list.append)]

    while stack:
      element, callback = stack.pop()
      nested = element.findall(CONTENT_ITEM_TAG)
      if not nested:
        this = element.text
      elif CONTENT_ITEM_KEY_ATTR in nested[0].attrib:
        this = {}
        for item in nested:
          key = item.attrib[CONTENT_ITEM_KEY_ATTR]
          stack.append((item, functools.partial(this.setdefault, key)))
      else:
        this = []
        for item in reversed(nested):
          stack.append((item, this.append))
      callback(this)

    assert len(retval_list) == 1
    return retval_list[0]

  def add_cfg_file(self, filename, name_prefix=None, interface_increment=0):
    """Add system config file to the system config object.

    Each design may rely on multiple system files so need to have the facility
    to parse them all.

    For example, we may have a:
    1. default for all controls that are the same for each of the
    control systems
    2. default for a particular DUT system's usage across the
    connector
    3. specific one for particular version of DUT (evt,dvt,mp)
    4. specific one for a one-off rework done to a system

    Special key parameters in config files:
      clobber_ok: signifies this control may _clobber_ an existing definition
        of the same name.  If its value is "full" then parameters from the
        clobbered control are completely thrown away, otherwise only those
        which are also specified in this control will be replaced.
      clobber_ok: Gives special instructions for how to reconcile an existing
        control definition with the same name or alias.  By default, if this
        is not specified, attempting to redefine a control is an error.
        Supported values:
          "full": This control will always be defined, and will completely
            replace any existing control with the same name or alias
          "patch": This control will update the params of an existing control,
            but this will never define a new control.
          "never": This control will be ignored if there is already a control
            under the same name or alias.  Otherwise, this will define a new
            control.
          "" (or any string not listed above): This control will update the
            params of an existing control if present, or if not, this will
            define a new control.

    NOTE, method is recursive when parsing 'include' elements from XML.

    The arguments name_prefix and interface_increment are used to support
    multiple servo micros. The interfaces of the extra servo micros, like
    the one for hammer, are relocated to higher slots. The controls of this
    extra servo micros should be shifted their interface numbers. Adding
    the name prefix avoid conflict with the main servo micro.

    Args:
      filename: string of path to system file ( xml )
      name_prefix: string to prepend to all control names
      interface_increment: number to add to all interfaces

    Raises:
      SystemConfigError: for schema violations, or file not found.
    """
    cfgname = self.find_cfg_file(filename)
    if not cfgname:
      msg = 'Unable to find system file %s' % filename
      self._logger.error(msg)
      raise SystemConfigError(msg)

    filename = cfgname
    if (filename, name_prefix, interface_increment) in self._loaded_xml_files:
      self._logger.warning('Already sourced system file (%s, %s, %d).',
                           filename, name_prefix, interface_increment)
      return
    self._loaded_xml_files.append((filename, name_prefix, interface_increment))

    self._logger.info('Loading XML config (%s, %s, %d)', filename, name_prefix,
                      interface_increment)
    root = xml.etree.ElementTree.parse(filename).getroot()
    for element in root.findall('include'):
      self.add_cfg_file(
          element.find('name').text, name_prefix, interface_increment)
    for tag in SYSCFG_TAG_LIST:
      for element in root.findall(tag):
        element_str = xml.etree.ElementTree.tostring(element)
        name = element.find('name')
        if name is not None:
          name = name.text
          if tag == CONTROL_TAG and name_prefix:
            name = name_prefix + name
        else:
          # TODO(tbroch) would rather have lineno but dumping element seems
          # better than nothing.  Utimately a DTD/XSD for the XML schema will
          # catch these anyways.
          raise SystemConfigError('%s: no name ... see XML\n%s' % (tag,
                                                                   element_str))
        doc = element.findtext('doc', default='undocumented')
        doc = ' '.join(doc.split())
        alias = element.findtext('alias')
        remap = element.findtext('remap')
        clone = element.findtext('clone')

        if remap:
          if name_prefix:
            remap = name_prefix + remap
          # Sometimes the remap control doesn't exist (e.g. fw_up in servo
          # v4).  Just ignore it and continue on.
          if name in self.syscfg_dict[tag]:
            self.syscfg_dict[tag][remap] = self.syscfg_dict[tag][name]
          continue

        # Similar to the above remap tag, but use deepcopy().
        if clone:
          if name_prefix:
            clone = name_prefix + clone
          if name in self.syscfg_dict[tag]:
            self.syscfg_dict[tag][clone] = copy.deepcopy(
                self.syscfg_dict[tag][name])
          continue

        get_dict = None
        set_dict = None
        params_list = element.findall('params')

        if tag == CONTROL_TAG:
          for p in params_list:
            if CONTENT_PARAM in p:
              raise SystemConfigError('file %r %s element %r specifies '
                                      'reserved params attribute name %r' %
                                      (filename, tag, name, CONTENT_PARAM))
            p.attrib[CONTENT_PARAM] = self._parse_content(p.find(CONTENT_TAG))

            # Make sure that if |cmd| is defined, it is correctly defined as
            # either set or get.
            if 'cmd' in p.attrib and p.attrib['cmd'] not in ('set', 'get'):
              raise SystemConfigError('%s %s cmd has to be set|get, not %r' %
                                      (tag, name, p.attrib['cmd']))

            # Modify the interface attributes.
            if 'interface' in p.attrib:
              if p.attrib['interface'] != 'servo':
                interface_id = int(p.attrib['interface'])
                p.attrib['interface'] = interface_id + interface_increment

        if len(params_list) == 2:
          assert tag != MAP_TAG, 'maps have only one params entry'
          for params in params_list:
            if 'cmd' not in params.attrib:
              raise SystemConfigError('%s %s multiple params but no cmd\n%s' %
                                      (tag, name, element_str))
            cmd = params.attrib['cmd']
            if cmd == 'get':
              if get_dict:
                raise SystemConfigError(
                    '%s %s multiple get params defined\n%s' % (tag, name,
                                                               element_str))
              get_dict = params.attrib
            else:  # |cmd| is 'set'
              # We know from above that cmd is guaranteed to be 'set' or 'get'
              if set_dict:
                raise SystemConfigError(
                    '%s %s multiple set params defined\n%s' % (tag, name,
                                                               element_str))
              set_dict = params.attrib
        elif len(params_list) == 1:
          # Some controls work for both set and get. Some controls only work
          # for one of the two, and the other is undefined. If there is only
          # one |params| defined and it does *not* define cmd, then the policy
          # is to treat it like the same dictionary for both. If it does
          # define it, then the policy is that the control is *only* valid for
          # one direction: set or get.
          # |pd| here stands for params dict
          pd = params_list[0].attrib
          if 'cmd' in pd:
            cmd = pd['cmd']
            if cmd == 'get':
              get_dict = copy.copy(pd)
              set_dict = copy.copy(UNDEF_CONTROL_DICT)
            else:  # |cmd| is 'set'
              set_dict = copy.copy(pd)
              get_dict = copy.copy(UNDEF_CONTROL_DICT)
          else:
            # |cmd| is not set. assume it's the same for both.
            get_dict = copy.copy(pd)
            set_dict = copy.copy(pd)
          if tag == CONTROL_TAG:
            # Lastly, to allow the |drv| full visibility in whether it's a set
            # or a get instance, make sure to store set and get in the dict
            # regardless of whether it was already there or has been inferred
            # here.
            get_dict['cmd'] = 'get'
            set_dict['cmd'] = 'set'
        else:
          raise SystemConfigError('%s %s has illegal number of params %d\n%s' %
                                  (tag, name, len(params_list), element_str))
        # If name_prefix was given, use it as the interface prefix. Use '' if
        # it wasn't.'
        if tag == CONTROL_TAG:
          set_dict['interface_prefix'] = name_prefix or ''
          get_dict['interface_prefix'] = name_prefix or ''

        # Save the control name to the params dicts, such that the driver can
        # refer to it.
        if tag == CONTROL_TAG:
          get_dict['control_name'] = name
          set_dict['control_name'] = name

        if tag == MAP_TAG:
          self.syscfg_dict[tag][name] = {'doc': doc, 'map_params': get_dict}
          if alias:
            raise SystemConfigError('No aliases for maps allowed')
          continue

        assert tag == CONTROL_TAG

        clobbers = []
        for ctrl_dict in get_dict, set_dict:
          clobbers.append(ctrl_dict.get(CLOBBER_ATTR))
          if clobbers[-1] is not None and clobbers[-1] not in CLOBBER_RANK:
            clobbers[-1] = CLOBBER_UPDATE
        clobber_ok = max(clobbers, key=lambda k: CLOBBER_RANK[k])

        if clobber_ok == CLOBBER_NEVER:
          if name in self.syscfg_dict[tag]:
            self._logger.debug('Quietly refusing to clobber existing %s %r' %
                               (tag, name))
            continue
        if clobber_ok == CLOBBER_PATCH:
          if name not in self.syscfg_dict[tag]:
            self._logger.debug('Ignoring clobber patch for nonexistent %s %r' %
                               (tag, name))
            continue
          self._logger.debug('Applying clobber patch to %s %r' % (tag, name))
        elif clobber_ok is None and name in self.syscfg_dict[tag]:
          raise SystemConfigError('Duplicate %s %r without %r key\n%s' %
                                  (tag, name, CLOBBER_ATTR, element_str))

        if 'init' in set_dict:
          hwinit_found = False
          # only allow one hwinit per control
          if clobber_ok is not None:
            # if we clobbered an alias, look for its hwinit under its real name
            realname = self.aliases.get(name, name)
            for i, (hwinit_name, _) in enumerate(self.hwinit):
              if hwinit_name == realname:
                self.hwinit[i] = (realname, set_dict['init'])
                hwinit_found = True
                break

          if not hwinit_found:
            self.hwinit.append((name, set_dict['init']))

        if name in self.syscfg_dict[tag]:
          assert clobber_ok is not None
          # Always update existing dicts when present, to avoid splitting
          # aliases into separate controls.
          if clobber_ok == CLOBBER_FULL:
            self.syscfg_dict[tag][name]['get_params'].clear()
            self.syscfg_dict[tag][name]['set_params'].clear()
          self.syscfg_dict[tag][name]['get_params'].update(get_dict)
          self.syscfg_dict[tag][name]['set_params'].update(set_dict)
          if doc != 'undocumented' or clobber_ok == CLOBBER_FULL:
            self.syscfg_dict[tag][name]['doc'] = doc
        else:
          self.syscfg_dict[tag][name] = {
              'doc': doc,
              'get_params': get_dict,
              'set_params': set_dict
          }

        if alias:
          # if we clobbered an alias, point our aliases to its real name
          realname = self.aliases.get(name, name)
          for aliasname in alias.split(','):
            if not IDENTIFIER_RE.fullmatch(aliasname):
              raise SystemConfigError('file %r %s element %r invalid '
                                      'alias "%s"' %
                                      (filename, tag, name, aliasname))
            if name_prefix:
              aliasname = name_prefix + aliasname
            self.syscfg_dict[tag][aliasname] = self.syscfg_dict[tag][name]
            # Also store what the alias relationship
            self.aliases[aliasname] = realname

  def finalize(self):
    """Finalize setup, Call this after no more config files will be added.

    Note: this can be called repeatedly, and will overwrite the previous
    results.

    - Sets up tags for each control, if provided
    """
    self.control_tags.clear()
    # Tags are only stored for the primary control name, not their aliases.
    base_controls = [control for control in self.syscfg_dict[CONTROL_TAG]
                     if control not in self.aliases]
    for control in base_controls:
      # Tags can be in either params.
      for params_dict in self.syscfg_dict[CONTROL_TAG][control].values():
        if 'tags' in params_dict:
          tags = SystemConfig.tag_string_to_tags(params_dict['tags'])
          for tag in tags:
            self.control_tags[tag].add(control)

  def get_controls_for_tag(self, tag):
    """Get list of controls for a given tag.

    Args:
      tag: str, tag to query

    Returns:
      list of controls with that tag, or an empty list if no such tag, or
      controls under that tag
    """
    # Checking here ensures that we do not generate an empty list (as it's a
    # default dict)
    if tag not in self.control_tags:
      self._logger.info('Tag %s unknown.', tag)
      return []
    return list(self.control_tags[tag])

  def lookup_map_params(self, name):
    """Lookup & return map parameter dictionary.

    Args:
      name: string of map name to lookup

    Returns:
      params: dictionary of map params

    Raises:
      NameError: if map name not found
    """
    if name not in self.syscfg_dict[MAP_TAG]:
      raise NameError('No map named %s. All maps:\n%s' %
                      (name, ','.join(sorted(self.syscfg_dict[MAP_TAG]))))
    return self.syscfg_dict[MAP_TAG][name]['map_params']

  def lookup_control_params(self, name):
    """Lookup & return control parameter dictionary.

    Each control has a set and get implementation. See |add_cfg_file()| for
    the policy on how those are generated and the guarantee that both always
    exist.

    Args:
      name: string of control name to lookup

    Returns:
      tuple(get params, set params) the params for each set and get

    Raises:
      NameError: if control name not found
    """
    if name not in self.syscfg_dict[CONTROL_TAG]:
      raise NameError('No control named %s. All controls:\n%s' %
                      (name,
                       ','.join(sorted(self.syscfg_dict[CONTROL_TAG]))))
    return (self.syscfg_dict[CONTROL_TAG][name]['get_params'],
            self.syscfg_dict[CONTROL_TAG][name]['set_params'])

  def get_all_controls(self):
    """Return an iterable of all controls specified.

    Returns:
      ctrls: set of all control names known to SystemConfig
    """
    return set(self.syscfg_dict[CONTROL_TAG].keys())

  def is_control(self, name):
    """Determine if name is a control or not.

    Args:
      name: string of control name to lookup

    Returns:
      boolean, True if name is control, False otherwise
    """
    return name in self.syscfg_dict[CONTROL_TAG]

  def get_control_str(self, name):
    """Generate a string that describes all information of the control.

    Args:
      name: string of control name to lookup

    Returns:
      A string representing the control
    """
    ctrl_dict = self.syscfg_dict[CONTROL_TAG]
    max_len = max(len(name) for name in ctrl_dict)
    dashes = '-' * max_len
    padded_name = '%-*s' % (max_len, '%s' % name)
    doc = '%s DOC: %s' % (padded_name, ctrl_dict[name]['doc'])
    get = '%s GET: %s' % (dashes, str(ctrl_dict[name]['get_params']))
    set = '%s SET: %s' % (dashes, str(ctrl_dict[name]['set_params']))
    return '%s\n%s\n%s' % (doc, get, set)

  def is_map(self, name):
    """Determine if name is a map or not.

    Args:
      name: string of map name to lookup

    Returns:
      boolean, True if name is map, False otherwise
    """
    return name in self.syscfg_dict[MAP_TAG]

  def get_control_docstring(self, name):
    """Get controls doc string.

    Args:
      name: string of control name to lookup

    Returns:
      doc string of the control
    """
    return self.syscfg_dict[CONTROL_TAG][name]['doc']

  def _lookup(self, tag, name_str):
    """Lookup the tag name_str and return dictionary or None if not found.

    Args:
      tag: string of tag (from SYSCFG_TAG_LIST) to look for name_str under.
      name_str: string of name to lookup

    Returns:
      dictionary from syscfg_dict[tag][name_str] or None
    """
    self._logger.debug('lookup of %s %s', tag, name_str)
    return self.syscfg_dict[tag].get(name_str)

  def resolve_val(self, params, map_vstr):
    """Resolve string value.

    Values to set the control to can be mapped to symbolic strings for better
    readability.  For example, its difficult to remember assertion levels of
    various gpios.  Maps allow things like 'reset:on'.  Also provides
    abstraction so that assertion level doesn't have to be exposed.

    Args:
      params: parameters dictionary for control
      map_vstr: string thats acceptable values are:
          an int (can be "DECIMAL", "0xHEX", 0OCT", or "0bBINARY".
          a floating point value.
          an alphanumeric which is key in the corresponding map dictionary.

    Returns:
      Resolved value as float or int or str depending on mapping & input type

    Raises:
      SystemConfigError: mapping issues found
    """
    # its a map
    err = 'Error formatting input value.'
    if 'map' in params:
      map_dict = self._lookup(MAP_TAG, params['map'])
      if map_dict is None:
        raise SystemConfigError("Map %s isn't defined" % params['map'])
      try:
        map_vstr = map_dict['map_params'][map_vstr]
      except KeyError:
        # Do not raise error yet. This might just be that the input is not
        # using the map i.e. it's directly writing a raw mapped value.
        err = "Map '%s' doesn't contain key '%s'\n" % (params['map'], map_vstr)
        err += "Try one of -> '%s'" % "', '".join(map_dict['map_params'])
    if 'input_type' in params:
      if params['input_type'] in ALLOWABLE_INPUT_TYPES:
        try:
          input_type = ALLOWABLE_INPUT_TYPES[params['input_type']]
          return input_type(map_vstr)
        except ValueError:
          err += "\n%s Input should be 'int' or 'float'." % ('Or' if 'Map' in
                                                             err else '')
      else:
        self._logger.error('Unrecognized input type.')
    # TODO(tbroch): deprecate below once all controls have input_type params
    try:
      return int(str(map_vstr), 0)
    except ValueError:
      pass
    try:
      return float(str(map_vstr))
    except ValueError:
      # No we know that nothing worked, and there was an error.
      err += (' %r canot be cast to default input type %r or fallback input '
              'type %r' % (map_vstr, 'int', 'float'))
      raise SystemConfigError(err)

  # pylint: disable=invalid-name
  # Naming convention to dynamically find methods based on config parameter
  def _Fmt_hex(self, int_val):
    """Format integer into hex.

    Args:
      int_val: integer to be formatted into hex string

    Returns:
      string of integer in hex format
    """
    return hex(int_val)

  def _Fmt_lowercase(self, val):
    """Lowercase the output

    Args:
      val: intput string

    Returns:
      lowercased input
    """
    return val.lower()

  def reformat_val(self, params, value):
    """Reformat value.

    Formatting determined via:
      1. if it has fmt param, reformat based on that
      2. if value (or value after fmt) matches a map in the param, use
         the symbolic name from the map, otherwise the (fmt) value

    Args:
      params: parameter dictionary for control
      value: value to reformat

    Returns:
      formatted string value if reformatting needed
      value otherwise

    Raises:
      SystemConfigError: errors using formatting param
    """
    # TODO(crbug.com/841097): revisit logic for value here once
    # resolution found on bug.
    if value is not None and 'map' not in params and 'fmt' not in params:
      return value
    reformat_value = str(value)
    if 'fmt' in params:
      fmt = params['fmt']
      try:
        func = getattr(self, '_Fmt_%s' % fmt)
      except AttributeError:
        raise SystemConfigError('Unrecognized format %s' % fmt)
      try:
        reformat_value = func(value)
      except Exception:
        raise SystemConfigError('Problem executing format %s' % fmt)
    if 'map' in params:
      map_dict = self._lookup(MAP_TAG, params['map'])
      if map_dict:
        map_params = map_dict['map_params']
        for keyname, val in map_params.items():
          # try treating val as a regex expression
          if params['map'].endswith('_re'):
            if re.search(val, reformat_value):
              reformat_value = keyname
              break
          # try matching it as a simple string
          elif val == reformat_value:
            reformat_value = keyname
            break
          # check for the possibility that there's need to reformat
          elif keyname == reformat_value:
            break
        else:
          if reformat_value and reformat_value != 'not_applicable':
            control = params['control_name']
            logging.warning('%s: %r not found in the param values',
                            control, reformat_value)
            logging.warning('%s: update drv to get and set values from the '
                            'param map %r', control, map_params)
    return reformat_value

  def display_config(self, tag=None, prefix=None):
    """Display human-readable values of a map or control

    Args:
      tag: 'map' or 'control' or None for all
      prefix: prefix string to print in front of control tags

    Returns:
      string to be displayed.
    """
    rsp = []
    if tag is None:
      tag_list = SYSCFG_TAG_LIST
    else:
      tag_list = [tag]
    for tag in sorted(tag_list):
      prefix_str = ''
      if tag == CONTROL_TAG and prefix:
        prefix_str = '%s.' % prefix
      rsp.append('*************')
      rsp.append('* ' + tag.upper())
      rsp.append('*************')
      max_len = max(len(name) for name in self.syscfg_dict[tag])
      max_len += len(prefix_str)
      dashes = '-' * max_len
      for name in sorted(self.syscfg_dict[tag]):
        item_dict = self.syscfg_dict[tag][name]
        padded_name = '%-*s' % (max_len, '%s%s' % (prefix_str, name))
        rsp.append('%s DOC: %s' % (padded_name, item_dict['doc']))
        if tag == MAP_TAG:
          rsp.append('%s MAP: %s' % (dashes, str(item_dict['map_params'])))
        else:
          rsp.append('%s GET: %s' % (dashes, str(item_dict['get_params'])))
          rsp.append('%s SET: %s' % (dashes, str(item_dict['set_params'])))

    return '\n'.join(rsp)

  def get_board_model_config(self, board=None, model=None):
    """Get the configuration file and board name for |board| & |model| pair.

    This essentially tries to find a configuration file for board/model first,
    before attempting to find a configuration file just for board, before
    giving up.

    Configuration filename format is servo_[board][_model]?_overlay.xml

    Args:
      board: board name
      model: model name under |board|

    Returns:
      tuple (board_config, board_id)
        board_config: the file name of the board's overlay file
        board_id: |board| or |board_model| if model was used to find an overlay
    """
    board_config = board_id = None
    if board:
      board_id = board
      # Handle differentiated model case.
      if model:
        board_id = '%s_%s' % (board_id, model)
        board_config = 'servo_%s_overlay.xml' % board_id

        if self.find_cfg_file(board_config):
          self._logger.info('Found XML overlay for model %s:%s', board, model)
        else:
          self._logger.info('No XML overlay for model %s, falling back to '
                      'board %s default', model, board)
          board_config = board_id = None

      # Handle generic board config.
      if not board_config:
        board_id = board
        board_config = 'servo_%s_overlay.xml' % board_id
        if self.find_cfg_file(board_config):
          self._logger.info('Found XML overlay for board %s', board)
        else:
          self._logger.error('No XML overlay for board %s', board)
          board_config = board_id = None

    return board_config, board_id


def test():
  """Integration test.

  TODO(tbroch) Enhance integration test and add unittest (see mox)
  """
  # pylint: disable=protected-access,raising-format-tuple,g-doc-exception
  # Test method that's likely to be removed as more unit-tests roll out.
  logging.basicConfig(
      level=logging.DEBUG,
      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
  scfg = SystemConfig()
  # TODO(tbroch) make this a comprenhensive test xml file
  scfg.add_cfg_file(os.path.join('data', 'servo.xml'))
  scfg.display_config()

  control_dict = scfg._lookup('control', 'rec_mode')
  # checking mapping functionality
  control_params = control_dict['get_params']
  control_params = control_dict['set_params']
  if 'map' in control_params:
    map_name = control_params['map']
    map_dict = scfg._lookup('map', map_name)
    if not map_dict:
      raise Exception('Unable to find map %s', map_name)

    logging.info('')
    for keyname, val in map_dict['map_params'].items():
      resolved_val = str(scfg.resolve_val(control_params, keyname))
      if resolved_val != val:
        logging.error('resolve failed for %s -> %s != %s', keyname, val,
                      resolved_val)

      # try re-mapping
      reformat_val = scfg.reformat_val(control_params, int(val))
      reformat_val = scfg.reformat_val(control_params, val)
      if reformat_val != keyname:
        logging.error('reformat failed for %s -> %s != %s', val, keyname,
                      reformat_val)


if __name__ == '__main__':
  test()
