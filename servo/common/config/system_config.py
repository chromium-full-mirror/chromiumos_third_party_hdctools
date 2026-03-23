# Copyright 2012 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""System configuration module."""

import collections
import functools
import glob
import logging
import os
import pathlib
import re
from xml.dom import minidom
import xml.etree.ElementTree

from . import config_resolver


# valid tags in system config xml.  Any others will be ignored
MAP_TAG = config_resolver.MAP_TAG
CONTROL_TAG = config_resolver.CONTROL_TAG
CLOBBER_ATTR = config_resolver.CLOBBER_ATTR
CLOBBER_NEVER = config_resolver.CLOBBER_NEVER
CLOBBER_PATCH = config_resolver.CLOBBER_PATCH
CLOBBER_FULL = config_resolver.CLOBBER_FULL
CONTENT_TAG = "content"
CONTENT_ITEM_TAG = "item"
INTERFACE_ALIAS_TAG = "interface_alias"
CONTENT_ITEM_KEY_ATTR = "key"
CONTENT_ITEM_TYPE_ATTR = "type"
CONTENT_PARAM = config_resolver.CONTENT_PARAM
SYSCFG_TAG_LIST = [MAP_TAG, CONTROL_TAG, INTERFACE_ALIAS_TAG]
ALLOWABLE_INPUT_TYPES = {"float": float, "int": int, "str": str}

# A control to use when set/get is explicitly not defined for a control.
UNDEF_CONTROL_DICT = config_resolver.UNDEF_CONTROL_DICT

# Valid pattern for control names and aliases
IDENTIFIER_RE = re.compile(r"[a-z][a-z0-9_]+")


# TODO(coconutruben): figure out if it's worth it to rename this so that it
# removes the 'stutter'
class SystemConfigError(Exception):
    """Error class for SystemConfig."""


class SystemConfig:
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
        self._logger = logging.getLogger("SystemConfig")
        self.control_tags = collections.defaultdict(set)
        self.interface_aliases = {}
        self.syscfg_dict = collections.defaultdict(dict)
        self.aliases = {}
        self.hwinit = []
        self._resolver = config_resolver.ConfigResolver(
            self.syscfg_dict, self.aliases, self.hwinit
        )
        self._loaded_xml_files = set()
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
        default_path = os.path.join(
            pathlib.Path(__file__).parent.parent.parent.resolve(), "data"
        )
        fullname = os.path.join(default_path, filename)
        if os.path.isfile(fullname):
            return fullname
        return None

    @staticmethod
    def tag_string_to_tags(tag_str):
        """Helper to split tag string into individual tags."""
        return tag_str.split(",")

    def get_all_cfg_names(self):
        """Return all XML config file names.

        Returns:
          A list of file names.
        """
        exclude_re = re.compile(r"servo_.*_overlay\.xml")
        pattern = os.path.join(os.path.dirname(__file__), "data", "*.xml")

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

    def _check_controls_for_drv(self):
        """Check that every control has a driver configured.

        Raises:
          SystemConfigError: A control is missing get or set driver configuration.
        """
        for name, control_dict in sorted(self.syscfg_dict[CONTROL_TAG].items()):
            for cmd, key in ("get", "get_params"), ("set", "set_params"):
                if "drv" not in control_dict[key]:
                    raise SystemConfigError(
                        '%s %r cmd="%s" has no driver configured (drv= attribute)'
                        % (CONTROL_TAG, name, cmd)
                    )

    def add_cfg_file(self, name_prefix, filename):
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
              "" (or any string not listed above): DEPRECATED, DO NOT USE in new
                control definitions!  https://issuetracker.google.com/287541200
                tracks removal of this option.  With clobber_ok="" this control
                will update the params of an existing control if present, or
                will define a new control if there isn't one to update.

        NOTE, method is recursive when parsing 'include' elements from XML.

        Args:
          name_prefix: string to prepend to all control names
          filename: string of path to system file ( xml )

        Raises:
          SystemConfigError: for schema violations, or file not found.
        """
        cfgname = self.find_cfg_file(filename)
        if not cfgname:
            msg = "Unable to find system file %s" % filename
            self._logger.error(msg)
            raise SystemConfigError(msg)

        filename = cfgname
        if (name_prefix, filename) in self._loaded_xml_files:
            self._logger.warning(
                "Already sourced system file (%r, %r).", filename, name_prefix
            )
            return
        self._loaded_xml_files.add((name_prefix, filename))
        self._logger.info("Loading XML config (%r, %r)", filename, name_prefix)

        # set of tuples representing config entities seen already in this file
        seen_entities = set()  # {(str, str)} - set of (tag, name) tuples

        root = xml.etree.ElementTree.parse(filename).getroot()
        for element in root.findall("include"):
            self.add_cfg_file(name_prefix, element.find("name").text)

        for tag in SYSCFG_TAG_LIST:
            for element in root.findall(tag):
                element_str = xml.etree.ElementTree.tostring(element)
                name = element.find("name")
                if name is None:
                    # TODO(tbroch) would rather have lineno but dumping element seems
                    # better than nothing.  Ultimately a DTD/XSD for the XML schema will
                    # catch these anyways.
                    raise SystemConfigError(
                        "%s: no name ... see XML\n%s" % (tag, element_str)
                    )

                name = name.text
                doc = element.findtext("doc", default="undocumented")
                doc = " ".join(doc.split())
                alias = element.findtext("alias")

                this_entity = tag, name
                if this_entity in seen_entities:
                    raise SystemConfigError(
                        "config file %r contains redundant or conflicting definitions "
                        "for %s %r" % (filename, tag, name)
                    )
                seen_entities.add(this_entity)

                if tag == INTERFACE_ALIAS_TAG:
                    alias_val = element.findtext("id")
                    if not name or not alias_val:
                        raise SystemConfigError(
                            "interface_alias needs both 'name' and 'id'"
                        )
                    self.interface_aliases[name] = alias_val
                    continue

                params_list = element.findall("params")

                if tag == CONTROL_TAG:
                    for p in params_list:
                        if CONTENT_PARAM in p.attrib:
                            raise SystemConfigError(
                                "file %r %s element %r specifies "
                                "reserved params attribute name %r"
                                % (filename, tag, name, CONTENT_PARAM)
                            )
                        p.attrib[CONTENT_PARAM] = self._parse_content(
                            p.find(CONTENT_TAG)
                        )

                        # Make sure that if |cmd| is defined, it is correctly defined as
                        # either set or get.
                        if "cmd" in p.attrib and p.attrib["cmd"] not in ("set", "get"):
                            raise SystemConfigError(
                                "%s %s cmd has to be set|get, not %r"
                                % (tag, name, p.attrib["cmd"])
                            )

                        # Modify the interface attributes.
                        if "interface" in p.attrib:
                            if p.attrib["interface"] != "servo":
                                try:
                                    p.attrib["interface"] = int(p.attrib["interface"])
                                except ValueError:
                                    pass

                try:
                    self._resolver.add_entity(
                        tag,
                        name,
                        doc,
                        alias,
                        [p.attrib for p in params_list],
                        filename,
                        element_str,
                    )
                except config_resolver.ConfigError as e:
                    raise SystemConfigError(str(e)) from e

                if tag == CONTROL_TAG and name in self.syscfg_dict[tag]:
                    # After resolution, ensure interface_prefix is set on both params.
                    # This handles cases where one was undefined and got the default
                    # UNDEF_CONTROL_DICT.
                    get_p = self.syscfg_dict[tag][name]["get_params"]
                    set_p = self.syscfg_dict[tag][name]["set_params"]
                    get_p["interface_prefix"] = name_prefix
                    set_p["interface_prefix"] = name_prefix

                if alias:
                    for aliasname in alias.split(","):
                        aliasname = aliasname.strip()
                        if not IDENTIFIER_RE.fullmatch(aliasname):
                            raise SystemConfigError(
                                "file %r %s element %r invalid "
                                'alias "%s"' % (filename, tag, name, aliasname)
                            )

    def finalize(self):
        """Finalize setup, Call this after no more config files will be added.

        Note: this can be called repeatedly, and will overwrite the previous
        results.

        - Sets up tags for each control, if provided
        """
        self._check_controls_for_drv()
        self.control_tags.clear()
        for control in self.syscfg_dict[CONTROL_TAG]:
            # Tags are only stored for the primary control name, not their aliases.
            if control not in self.aliases:
                # Tags can be in either params.
                for params_dict in self.syscfg_dict[CONTROL_TAG][control].values():
                    if "tags" in params_dict:
                        tags = SystemConfig.tag_string_to_tags(params_dict["tags"])
                        for tag in tags:
                            if tag not in self.control_tags:
                                self.control_tags[tag] = set()
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
            self._logger.info("Tag %s unknown.", tag)
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
            raise NameError(
                "No map named %s. All maps:\n%s"
                % (name, ",".join(sorted(self.syscfg_dict[MAP_TAG])))
            )
        return self.syscfg_dict[MAP_TAG][name]["map_params"]

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
            raise NameError(
                "No control named %s. All controls:\n%s"
                % (name, ",".join(sorted(self.syscfg_dict[CONTROL_TAG])))
            )
        get_params = dict(self.syscfg_dict[CONTROL_TAG][name]["get_params"])
        set_params = dict(self.syscfg_dict[CONTROL_TAG][name]["set_params"])

        if (
            "interface" in get_params
            and get_params["interface"] in self.interface_aliases
        ):
            get_params["interface"] = self.interface_aliases[get_params["interface"]]

        if (
            "interface" in set_params
            and set_params["interface"] in self.interface_aliases
        ):
            set_params["interface"] = self.interface_aliases[set_params["interface"]]

        return (get_params, set_params)

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
        dashes = "-" * max_len
        padded_name = "%-*s" % (max_len, "%s" % name)
        doc_str = "%s DOC: %s" % (padded_name, ctrl_dict[name]["doc"])
        get_str = "%s GET: %s" % (dashes, str(ctrl_dict[name]["get_params"]))
        set_str = "%s SET: %s" % (dashes, str(ctrl_dict[name]["set_params"]))
        return "%s\n%s\n%s" % (doc_str, get_str, set_str)

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
        return self.syscfg_dict[CONTROL_TAG][name]["doc"]

    def _lookup(self, tag, name_str):
        """Lookup the tag name_str and return dictionary or None if not found.

        Args:
          tag: string of tag (from SYSCFG_TAG_LIST) to look for name_str under.
          name_str: string of name to lookup

        Returns:
          dictionary from syscfg_dict[tag][name_str] or None
        """
        self._logger.debug("lookup of %s %s", tag, name_str)
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
        err_msg_parts = []
        is_map_error = False

        if "map" in params:
            map_dict = self._lookup(MAP_TAG, params["map"])
            if map_dict is None:
                raise SystemConfigError("Map %s isn't defined" % params["map"])
            try:
                map_vstr = map_dict["map_params"][map_vstr]
            except KeyError:
                # Do not raise error yet. This might just be that the input is not
                # using the map i.e. it's directly writing a raw mapped value.
                is_map_error = True
                err_msg_parts.append(
                    "Invalid input %r. It is not a valid map key for '%s' "
                    "(Try one of: '%s')."
                    % (map_vstr, params["map"], "', '".join(map_dict["map_params"]))
                )

        if "input_type" in params:
            if params["input_type"] in ALLOWABLE_INPUT_TYPES:
                try:
                    input_type = ALLOWABLE_INPUT_TYPES[params["input_type"]]
                    return input_type(map_vstr)
                except ValueError as e:
                    if is_map_error:
                        err_msg_parts.append(
                            "Additionally, it cannot be cast to the specified "
                            "input_type '%s'." % params["input_type"]
                        )
                    else:
                        err_msg_parts.append(
                            "Input %r must be of type '%s'."
                            % (map_vstr, params["input_type"])
                        )
                    raise SystemConfigError(" ".join(err_msg_parts)) from e
            else:
                self._logger.error("Unrecognized input type.")

        # TODO(tbroch): deprecate below once all controls have input_type params
        try:
            # If it's a float that's equivalent to an int, convert it to int.
            # This is common with gRPC Value (number_value is double).
            fval = float(str(map_vstr))
            if fval == int(fval):
                return int(fval)
            return fval
        except ValueError:
            pass
        try:
            return int(str(map_vstr), 0)
        except ValueError:
            pass
        try:
            return float(str(map_vstr))
        except ValueError as e:
            # Now we know that nothing worked, and there was an error.
            if is_map_error:
                err_msg_parts.append(
                    "Additionally, it cannot be cast to a raw int or float."
                )
            else:
                err_msg_parts.append(
                    "Input %r cannot be cast to default input type 'int' "
                    "or fallback input type 'float'." % map_vstr
                )
            raise SystemConfigError(" ".join(err_msg_parts)) from e

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
          val: input string

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
        if value is not None and "map" not in params and "fmt" not in params:
            return value
        reformat_value = str(value)
        if "fmt" in params:
            fmt = params["fmt"]
            try:
                func = getattr(self, "_Fmt_%s" % fmt)
            except AttributeError as e:
                raise SystemConfigError("Unrecognized format %s" % fmt) from e
            try:
                reformat_value = func(value)
            except Exception as e:
                raise SystemConfigError("Problem executing format %s" % fmt) from e
        if "map" in params:
            map_dict = self._lookup(MAP_TAG, params["map"])
            if map_dict:
                map_params = map_dict["map_params"]
                for keyname, val in map_params.items():
                    # try treating val as a regex expression
                    if params["map"].endswith("_re"):
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
                    if reformat_value and reformat_value != "not_applicable":
                        control = params["control_name"]
                        logging.warning(
                            "%s: %r not found in the param values",
                            control,
                            reformat_value,
                        )
                        logging.warning(
                            "%s: update drv to get and set values from the "
                            "param map %r",
                            control,
                            map_params,
                        )
        return reformat_value

    def dump_to_xml(self, filename):
        """Dump the parsed system configuration to an XML file.

        Args:
          filename: string of the file to save to.
        """

        root = xml.etree.ElementTree.Element("root")

        # Dump maps
        if MAP_TAG in self.syscfg_dict:
            for name in sorted(self.syscfg_dict[MAP_TAG]):
                # Only iterate over primary names, not aliases
                if name in self.aliases:
                    continue
                item_dict = self.syscfg_dict[MAP_TAG][name]
                map_elem = xml.etree.ElementTree.SubElement(root, MAP_TAG)
                xml.etree.ElementTree.SubElement(map_elem, "name").text = name
                if item_dict.get("doc") and item_dict["doc"] != "undocumented":
                    xml.etree.ElementTree.SubElement(map_elem, "doc").text = item_dict[
                        "doc"
                    ]

                aliases = [a for a, r in self.aliases.items() if r == name]
                if aliases:
                    xml.etree.ElementTree.SubElement(map_elem, "alias").text = ",".join(
                        sorted(aliases)
                    )

                params_elem = xml.etree.ElementTree.SubElement(map_elem, "params")
                for k, v in sorted(item_dict["map_params"].items()):
                    if k != "interface_prefix":
                        params_elem.set(k, str(v))

        # Dump controls
        if CONTROL_TAG in self.syscfg_dict:
            for name in sorted(self.syscfg_dict[CONTROL_TAG]):
                # Only iterate over primary names, not aliases
                if name in self.aliases:
                    continue
                item_dict = self.syscfg_dict[CONTROL_TAG][name]
                ctrl_elem = xml.etree.ElementTree.SubElement(root, CONTROL_TAG)
                xml.etree.ElementTree.SubElement(ctrl_elem, "name").text = name
                if item_dict.get("doc") and item_dict["doc"] != "undocumented":
                    xml.etree.ElementTree.SubElement(ctrl_elem, "doc").text = item_dict[
                        "doc"
                    ]

                aliases = [a for a, r in self.aliases.items() if r == name]
                if aliases:
                    xml.etree.ElementTree.SubElement(ctrl_elem, "alias").text = (
                        ",".join(sorted(aliases))
                    )

                get_p = item_dict["get_params"]
                set_p = item_dict["set_params"]

                params_list = []
                if get_p == set_p:
                    params_list = [get_p]
                else:
                    if get_p.get("drv") != "undefined":
                        params_list.append(get_p)
                    if set_p.get("drv") != "undefined":
                        params_list.append(set_p)

                for p_dict in params_list:
                    p_elem = xml.etree.ElementTree.SubElement(ctrl_elem, "params")
                    for k, v in sorted(p_dict.items()):
                        # We might want to keep cmd, control_name, etc.
                        if k == "cmd" and len(params_list) == 1:
                            continue
                        if k in ["control_name", "interface_prefix"]:
                            continue
                        if k == CONTENT_PARAM:
                            # Handling the content param serialization
                            content_elem = xml.etree.ElementTree.SubElement(
                                p_elem, CONTENT_TAG
                            )
                            if isinstance(v, dict):
                                for ck, cv in sorted(v.items()):
                                    item_elem = xml.etree.ElementTree.SubElement(
                                        content_elem, CONTENT_ITEM_TAG
                                    )
                                    item_elem.set(CONTENT_ITEM_KEY_ATTR, str(ck))
                                    item_elem.text = str(cv)
                                    # Very basic type inference for reverse parsing
                                    if isinstance(cv, int):
                                        item_elem.set(CONTENT_ITEM_TYPE_ATTR, "int")
                                    elif isinstance(cv, float):
                                        item_elem.set(CONTENT_ITEM_TYPE_ATTR, "float")
                                    else:
                                        item_elem.set(CONTENT_ITEM_TYPE_ATTR, "str")
                            continue
                        p_elem.set(k, str(v))

        rough_string = xml.etree.ElementTree.tostring(root, "utf-8")
        reparsed = minidom.parseString(rough_string)

        pretty_xml = reparsed.toprettyxml(indent="  ")
        # Remove extra blank lines
        pretty_xml = os.linesep.join([s for s in pretty_xml.splitlines() if s.strip()])

        with open(filename, "w", encoding="utf-8") as f:
            f.write(pretty_xml)

    def display_config(self, tag_param=None, prefix=None):
        """Display human-readable values of a map or control

        Args:
          tag: 'map' or 'control' or None for all
          prefix: prefix string to print in front of control tags

        Returns:
          string to be displayed.
        """
        rsp = []
        if tag_param is None:
            tag_list = SYSCFG_TAG_LIST
        else:
            tag_list = [tag_param]
        for tag in sorted(tag_list):
            if not self.syscfg_dict[tag]:
                continue
            prefix_str = ""
            if tag == CONTROL_TAG and prefix:
                prefix_str = "%s." % prefix
            rsp.append("*************")
            rsp.append("* " + tag.upper())
            rsp.append("*************")
            max_len = max(len(name) for name in self.syscfg_dict[tag])
            max_len += len(prefix_str)
            dashes = "-" * max_len
            for name in sorted(self.syscfg_dict[tag]):
                item_dict = self.syscfg_dict[tag][name]
                padded_name = "%-*s" % (max_len, "%s%s" % (prefix_str, name))
                rsp.append("%s DOC: %s" % (padded_name, item_dict["doc"]))
                if tag == MAP_TAG:
                    rsp.append("%s MAP: %s" % (dashes, str(item_dict["map_params"])))
                else:
                    rsp.append("%s GET: %s" % (dashes, str(item_dict["get_params"])))
                    rsp.append("%s SET: %s" % (dashes, str(item_dict["set_params"])))

        return "\n".join(rsp)

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
                board_id = "%s_%s" % (board_id, model)
                board_config = "servo_%s_overlay.xml" % board_id

                if self.find_cfg_file(board_config):
                    self._logger.info("Found XML overlay for model %s:%s", board, model)
                else:
                    self._logger.info(
                        "No XML overlay for model %s, falling back to "
                        "board %s default",
                        model,
                        board,
                    )
                    board_config = board_id = None

            # Handle generic board config.
            if not board_config:
                board_id = board
                board_config = "servo_%s_overlay.xml" % board_id
                if self.find_cfg_file(board_config):
                    self._logger.info("Found XML overlay for board %s", board)
                else:
                    self._logger.error("No XML overlay for board %s", board)
                    board_config = board_id = None

        return board_config, board_id

    def get_available_models(self, board):
        """Get all available models for a given board.

        Args:
          board: board name

        Returns:
          list of model names
        """
        if not board:
            return []
        default_path = os.path.join(
            pathlib.Path(__file__).parent.parent.parent.resolve(), "data"
        )
        pattern = os.path.join(default_path, "servo_%s_*_overlay.xml" % board)
        files = glob.glob(pattern)
        models = []
        prefix = "servo_%s_" % board
        suffix = "_overlay.xml"
        for f in files:
            basename = os.path.basename(f)
            if basename.startswith(prefix) and basename.endswith(suffix):
                model = basename[len(prefix) : -len(suffix)]
                models.append(model)
        return sorted(models)
