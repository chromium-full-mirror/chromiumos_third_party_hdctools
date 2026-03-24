# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import json

from servo.common.utils import json_utils
from servo.drv import hw_driver


class selectControlError(Exception):
    """Exception class for selectControl."""


class selectControl(hw_driver.HwDriver):
    """Add support for choosing which control to use.

    There may be multiple ways to control the dut. Add a driver to select which
    control to use. This may be used to select between using a servo hardware
    signal and a ccd signal. Different tests may need to verify ccd control or
    hardware control.

    To use this create a control CONTROL_NAME_select. Use that to select the
    control uses to get/set CONTROL_NAME.
    ex setting cold_reset_select to ec_reset will make servo use ec_reset to
    get/set the cold_reset value.
    """

    __SELECT_SUFFIX = "_select"

    def _drv_init(self):
        """Driver specific initializer."""
        # Maps don't translate correctly when the selected control changes. Ignore
        # the maps. servo.get(selected_control) will handle the mapping.
        if "map" in self._params:
            del self._params["map"]

        super()._drv_init()

        if not json.loads(self._driver_client.GetSelectedControls().response):
            self._driver_client.InitSelectedControls()
        servo_type = self._params.get("device_type", "")
        self.__prefix = (servo_type + ".") if servo_type else ""

    def _Set_select(self, val):
        """Set the control to use."""
        if not val:
            return
        # Look up the servo specific init. 'servo_init' is used to
        # initialize flex devices.
        # 'ccd_init' is used to initialize ccd devices.
        if val == "servo_specific":
            servo_type = self._params.get("device_type", "").partition("_")[0]
            servo_init = servo_type + "_init"
            val = self._params[servo_init]
        control_key = self._get_control_key()
        self._logger.info("%r -> %r", control_key, val)
        val_pb = json_utils.wrap_value(val)
        self._driver_client.SetSelectedControls(
            control_name=control_key, control_value=val_pb
        )

    def _Get_select(self):
        """Get the control value."""
        control_key = self._get_control_key()
        if control_key not in json.loads(
            self._driver_client.GetSelectedControls().response
        ):
            self._Set_select(self._params["init"])
        rv = json.loads(self._driver_client.GetSelectedControls().response).get(
            control_key, ""
        )
        if rv:
            self._logger.debug("using %r for %r", rv, control_key)
        return rv

    def _Get_control(self):
        """Get the value from the selected control."""
        selected_control = self._get_selected_control()
        return self._servod_get(self.__prefix + selected_control)

    def _Set_control(self, value):
        """Set the selected control to value."""
        selected_control = self._get_selected_control()
        return self._servod_set(self.__prefix + selected_control, value)

    def _get_control_key(self):
        """Get the base control name."""
        control_name = self._params.get("control_name", "")
        if not control_name:
            raise selectControlError("control_name not found")
        return self.__prefix + control_name

    def _get_selected_control(self):
        """Return the control being used."""
        control_name = self._params.get("control_name", "")
        return self._servod_get(self.__prefix + control_name + self.__SELECT_SUFFIX)
