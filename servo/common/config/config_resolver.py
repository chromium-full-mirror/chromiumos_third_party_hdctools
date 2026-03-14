# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Shared logic for resolving servo system configuration entities."""

import collections
import copy
import logging


# valid tags in system config xml.
MAP_TAG = "map"
CONTROL_TAG = "control"
CLOBBER_ATTR = "clobber_ok"
CLOBBER_NEVER = "never"
CLOBBER_PATCH = "patch"
CLOBBER_FULL = "full"
CONTENT_PARAM = "CONTENT"

# A control to use when set/get is explicitly not defined for a control.
UNDEF_CONTROL_DICT = {"drv": "undefined", "interface": "servo", "input_type": "str"}


class ConfigError(Exception):
    """Error class for ConfigResolver."""


class ConfigResolver:
    """Logic to resolve and clobber servo configuration entities."""

    def __init__(self, syscfg_dict=None, aliases=None, hwinit=None):
        """Constructor.

        Args:
            syscfg_dict: 3-deep dictionary organized as [tag][name][type]
            aliases: dictionary of an alias mapped to its base control name
            hwinit: list of control tuples (name, value) to be initialized
        """
        self.syscfg_dict = syscfg_dict
        if self.syscfg_dict is None:
            self.syscfg_dict = collections.defaultdict(dict)
        self.aliases = aliases
        if self.aliases is None:
            self.aliases = {}
        self.hwinit = hwinit
        if self.hwinit is None:
            self.hwinit = []
        self._logger = logging.getLogger("ConfigResolver")

    def add_entity(
        self, tag, name, doc, alias, params_list, filename=None, element_str=""
    ):
        """Add a configuration entity (control or map).

        Args:
            tag: 'control' or 'map'
            name: name of the entity
            doc: documentation string
            alias: alias string (comma separated)
            params_list: list of attribute dictionaries for params
            filename: source filename for error reporting
            element_str: string representation of the XML element for error reporting

        Raises:
            ConfigError: if there are resolution conflicts or errors.
        """
        get_dict = None
        set_dict = None
        get_is_defined = True
        set_is_defined = True

        if len(params_list) == 2:
            if tag == MAP_TAG:
                raise ConfigError(
                    "maps have only one params entry: %s %s" % (tag, name)
                )
            for params in params_list:
                if "cmd" not in params:
                    raise ConfigError(
                        "%s %s multiple params but no cmd\n%s"
                        % (tag, name, element_str)
                    )
                cmd = params["cmd"]
                if cmd == "get":
                    if get_dict:
                        raise ConfigError(
                            "%s %s multiple get params defined\n%s"
                            % (tag, name, element_str)
                        )
                    get_dict = params
                else:  # |cmd| is 'set'
                    if set_dict:
                        raise ConfigError(
                            "%s %s multiple set params defined\n%s"
                            % (tag, name, element_str)
                        )
                    set_dict = params
        elif len(params_list) == 1:
            pd = params_list[0]
            if "cmd" in pd:
                cmd = pd["cmd"]
                if cmd == "get":
                    get_dict = copy.copy(pd)
                    set_dict = copy.copy(UNDEF_CONTROL_DICT)
                    set_is_defined = False
                else:  # |cmd| is 'set'
                    set_dict = copy.copy(pd)
                    get_dict = copy.copy(UNDEF_CONTROL_DICT)
                    get_is_defined = False
            else:
                get_dict = copy.copy(pd)
                set_dict = copy.copy(pd)
            if tag == CONTROL_TAG:
                get_dict["cmd"] = "get"
                set_dict["cmd"] = "set"
        else:
            raise ConfigError(
                "%s %s has illegal number of params %d\n%s"
                % (tag, name, len(params_list), element_str)
            )

        if tag == CONTROL_TAG:
            get_dict["control_name"] = name
            set_dict["control_name"] = name

        if tag == MAP_TAG:
            if alias:
                raise ConfigError("No aliases for maps allowed: %s" % name)
            self.syscfg_dict[tag][name] = {"doc": doc, "map_params": get_dict}
            return

        clobber_vals = set()
        if get_is_defined:
            clobber_vals.add(get_dict.get(CLOBBER_ATTR))
        if set_is_defined:
            clobber_vals.add(set_dict.get(CLOBBER_ATTR))

        if not clobber_vals:
            clobber_ok = None
        elif len(clobber_vals) == 1:
            clobber_ok = clobber_vals.pop()
        else:
            raise ConfigError(
                "config file %r %s %r has conflicting %s= values between "
                'cmd="get" and cmd="set"' % (filename, tag, name, CLOBBER_ATTR)
            )

        if clobber_ok == CLOBBER_NEVER:
            if name in self.syscfg_dict[tag]:
                self._logger.debug(
                    "Quietly refusing to clobber existing %s %r", tag, name
                )
                return
        if clobber_ok == CLOBBER_PATCH:
            if name not in self.syscfg_dict[tag]:
                self._logger.debug(
                    "Ignoring clobber patch for nonexistent %s %r", tag, name
                )
                return
            self._logger.debug("Applying clobber patch to %s %r", tag, name)
        elif clobber_ok is None and name in self.syscfg_dict[tag]:
            clobber_ok = CLOBBER_FULL

        if "init" in set_dict:
            hwinit_found = False
            if clobber_ok is not None:
                realname = self.aliases.get(name, name)
                for i, (hwinit_name, unused_) in enumerate(self.hwinit):
                    if hwinit_name == realname:
                        self.hwinit[i] = (realname, set_dict["init"])
                        hwinit_found = True
                        break

            if not hwinit_found:
                self.hwinit.append((name, set_dict["init"]))

        if name in self.syscfg_dict[tag]:
            if clobber_ok == CLOBBER_FULL:
                self.syscfg_dict[tag][name]["get_params"].clear()
                self.syscfg_dict[tag][name]["set_params"].clear()
            self.syscfg_dict[tag][name]["get_params"].update(get_dict)
            self.syscfg_dict[tag][name]["set_params"].update(set_dict)
            if doc != "undocumented" or clobber_ok == CLOBBER_FULL:
                self.syscfg_dict[tag][name]["doc"] = doc
        else:
            self.syscfg_dict[tag][name] = {
                "doc": doc,
                "get_params": get_dict,
                "set_params": set_dict,
            }

        if tag == CONTROL_TAG:
            if "drv" not in self.syscfg_dict[tag][name]["get_params"]:
                raise ConfigError(
                    'control %r cmd="get" has no driver configured (drv= attribute)'
                    % (name,)
                )
            if "drv" not in self.syscfg_dict[tag][name]["set_params"]:
                raise ConfigError(
                    'control %r cmd="set" has no driver configured (drv= attribute)'
                    % (name,)
                )

        if alias:
            realname = self.aliases.get(name, name)
            for aliasname in alias.split(","):
                aliasname = aliasname.strip()
                self.syscfg_dict[tag][aliasname] = self.syscfg_dict[tag][name]
                self.aliases[aliasname] = realname
