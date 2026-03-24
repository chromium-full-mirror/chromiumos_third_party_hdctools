# Copyright 2019 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

from servo.drv import hw_driver


class macro(hw_driver.HwDriver):
    """A special driver to implement virtual controls by macro.

    This driver supports controls that act as shorthand for calling a series of
    underlying controls.  The underlying controls and their values are specified
    per macro control value.

    Macros controls are configured using <contents> in the <params> XML element.

    Example:

    <control>
      <name>my_control</name>
      <doc>Does cool stuff!</doc>
      <params drv="macro">
        <content>
          <item key="get_controls">
            <item>subcontrol0</item>
            <item>subcontrol2</item>
          </item>
          <item key="macro_map">
            <item key="on">
              <item>subcontrol0:on</item>
              <item>sleep:5</item>
              <item>subcontrol1:18</item>
              <item>subcontrol2:on</item>
              <item>subcontrol3:cmd0 arg1 arg2 arg3</item>
              <item>subcontrol3:cmd1 arg1</item>
            </item>
            <item key="off">
              <item>subcontrol2:off</item>
              <item>subcontrol0:off</item>
              <item>subcontrol3:reset</item>
            </item>
          </item>
        </content>
      </params>
    </control>

    With that macro control, when my_control:on is set the following controls will
    be set, in order:
      subcontrol0:on
      sleep:5
      subcontrol1:18
      subcontrol2:on
      subcontrol3:cmd0 arg1 arg2 arg3
      subcontrol3:cmd1 arg1

    When my_control:off is set the following controls will be set, in order:
      subcontrol2:off
      subcontrol0:off
      subcontrol3:reset

    When getting the value of my_control...
      * When get_controls is *not* specified, then the values of all controls used
        in any of the macro_map values will be examined.
      * When get_controls *is* specified, like in this example, only those
        controls' values will be examined (subcontrol0 and subcontrol2 in this
        example).
      * If the examined controls' values all match the specified values for a
        macro_map entry, then that macro value ("on" or "off" in this example)
        will be returned as the value.
      * If the control values match for multiple macro_map entries, one of them
        will be returned, but it is currently undefined which will be.
      * If none of the macro_map entries matches, then "unknown" will be returned.
      * If a control doesn't exist, then it is ignored for this purpose.
      * If a control returns "not_applicable" then it is ignored for this purpose.
      * At least one control must be examined and match for a macro_map value to
        be returned.

    *** DEPRECATED CONFIGURATION FORMAT BELOW, DO NOT USE IN NEW CONTROLS ***

    This driver allows defining new states by parameters, in format
    `set_value_${value}`. For example, a state 'on' is defined by parameter name
    'set_value_on'. Its value should be a list of controls to set, in
    `${control}:${state}` format. For example, 'spi2_verf:pp1800 spi_buf_en:on'.

    If parameter 'get_controls' is set, the value must be a list of controls that
    will be evaluated to decide final state. This can be useful if you must ignore
    few write-only controls. If 'get_controls' is not set, it will default to the
    list of all controls in 'set_value_*' parameters.

    TODO(https://issuetracker.google.com/253349276): Migrate all uses of
    deprecated get_controls and set_value_${value} params attributes to use the
    new <content> format, then remove support for the attributes.
    """

    _STATE_UNKNOWN = "unknown"

    def _drv_init(self):
        """Driver specific initializer."""
        super()._drv_init()
        str_prefix = "set_value_"

        self._states = {}
        for key, value in self._params.items():
            if key.startswith(str_prefix):
                macro_val = key[len(str_prefix) :]
                self._states[macro_val] = [item.split(":", 1) for item in value.split()]

        get_ctrls = self._params.get("get_controls")
        self._get_controls = None if get_ctrls is None else set(get_ctrls.split())

        mconf = self._params["CONTENT"]
        if mconf is None:
            return

        get_ctrls = mconf.get("get_controls")
        if get_ctrls is not None:
            if self._get_controls is not None:
                raise hw_driver.HwDriverError(
                    '"get_controls" must only be specified in a control params once, '
                    "either as an attribute or in <content>, but not in both places.  "
                    "self._params=%r" % (self._params,)
                )
            self._get_controls = set(map(str, get_ctrls))

        macro_map = mconf.get("macro_map")
        if macro_map is not None:
            if self._states:
                raise hw_driver.HwDriverError(
                    "Macro values must only be specified in one part of the control "
                    "params, either as attributes (deprecated) or in <content>, but "
                    "not in both places.  self._params=%r" % (self._params,)
                )
            for macro_val, value in macro_map.items():
                self._states[macro_val] = [str(item).split(":", 1) for item in value]

    def _set(self, new_state):
        """Transit to a new state."""
        state_name = str(new_state)
        if state_name not in self._states:
            raise hw_driver.HwDriverError(
                "Invalid state: %r  Supported states: %r"
                % (state_name, sorted(self._states))
            )

        for control, state in self._states[state_name]:
            if not self._servod_has_control(control):
                logging.info(
                    "Ignore setting non-exist control '%s' to '%s'.", control, state
                )
                continue
            self._servod_set(control, state)

    def _get(self):
        """Checks and returns current state."""
        if self._get_controls is not None and not self._get_controls:
            return self._STATE_UNKNOWN

        cached = {}

        def get_value(ctrl):
            if ctrl in cached:
                return cached[ctrl]
            value = self._servod_get(ctrl)
            cached[ctrl] = value
            return value

        for name, rules in self._states.items():
            # 'rules' is a list of (control, state) tuples.
            # To match, at least one control must be in self._get_controls.
            matched = 0
            for control, state in rules:
                if self._get_controls is not None and control not in self._get_controls:
                    continue
                if not self._servod_has_control(control):
                    continue
                if get_value(control) == "not_applicable":
                    continue
                if get_value(control) != state:
                    break
                matched += 1
            else:
                if matched:
                    return name

        return self._STATE_UNKNOWN
