# Copyright 2016 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from servo.drv import fw_wp_state


class fwWpServoflex(fw_wp_state.FwWpStateDriver):
    """Driver for fw_wp_state for boards connecting servoflex's."""

    def _drv_init(self):
        """Driver specific initializer."""
        super()._drv_init()
        self._fw_wp_vref = self._params.get("fw_wp_vref", "pp1800")
        self._is_open_drain = self._params.get("open_drain", "no") == "yes"
        # Keep GSC WP in sync with the flex WP. Must define gsc_fw_wp_state
        self._sync_gsc_wp = self._params.get("sync_gsc_wp", "no") == "yes"
        if self._is_open_drain:
            assert self._fw_wp_vref == "off", "Dangerous! Should set vref to off."

        # Get the control prefix, like 'hammer_', if it is a base control.
        control_name = self._params.get("control_name", "")
        assert control_name.endswith("fw_wp_state"), "Should be fw_wp_state control"

    def _set_gsc_wp(self, state):
        """Set the ccd firmware write-protect state."""
        if self._sync_gsc_wp:
            self._servod_set("gsc_fw_wp_state", state)

    def _force_off(self):
        """Force the firmware to not write-protected through flex and ccd."""
        # Disable GSC WP before disabling flex WP to avoid triggering a GSC reset
        # due to WP mismatch.
        self._set_gsc_wp(self._STATE_FORCE_OFF)
        self._main_servo_force_off()

    def _force_on(self):
        """Force the firmware to write-protected through flex and ccd."""
        # Try to enable ccd WP whenever the flex cable WP is enabled to avoid
        # triggering a GSC reset due to WP mismatch.
        self._main_servo_force_on()
        self._set_gsc_wp(self._STATE_FORCE_ON)

    def _main_servo_force_on(self):
        """Force the firmware to write-protected through the flex cable."""
        if self._is_open_drain:
            self._servod_set("fw_wp_od", "on")
        else:
            self._servod_set("fw_wp_vref", self._fw_wp_vref)
            self._servod_set("fw_wp_en", "on")
            self._servod_set("fw_wp", "on")

    def _main_servo_force_off(self):
        """Force the firmware to not write-protected through the flex cable."""
        if self._is_open_drain:
            self._servod_set("fw_wp_od", "off")
        else:
            self._servod_set("fw_wp_vref", self._fw_wp_vref)
            self._servod_set("fw_wp_en", "on")
            self._servod_set("fw_wp", "off")

    def _main_reset(self):
        """Reset the main servo WP signal."""
        if self._is_open_drain:
            self._servod_set("fw_wp_od", "off")
        else:
            self._servod_set("fw_wp_en", "off")

    def _reset(self):
        """Reset the firmware write-protection state to the system value."""
        self._set_gsc_wp(self._STATE_RESET)
        self._main_reset()

    def _get_state(self):
        """Get the firmware write-protection state."""
        if self._is_open_drain:
            fw_wp_od = self._servod_get("fw_wp_od") == "on"
            # Can't differentiate between a forced value or an original value;
            # return it a forced value which is more compliant with the tests.
            return self._STATE_FORCE_ON if fw_wp_od else self._STATE_FORCE_OFF
        else:
            fw_wp_en = self._servod_get("fw_wp_en") == "on"
            fw_wp = self._servod_get("fw_wp") == "on"
            if fw_wp_en:
                return self._STATE_FORCE_ON if fw_wp else self._STATE_FORCE_OFF
            else:
                return self._STATE_ON if fw_wp else self._STATE_OFF
