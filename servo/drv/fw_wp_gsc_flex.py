# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from servo.drv import fw_wp_servoflex


class fwWpGscFlex(fw_wp_servoflex.fwWpServoflex):
    """fw_wp_state driver to control WP with the GSC. Reset servo WP signal"""

    def _drv_init(self):
        """Driver specific initializer."""
        super()._drv_init()
        self._sync_gsc_wp = True
        # True if GSC is the only WP driver.
        self._gsc_only = self._params.get("gsc_only", "no") == "yes"

    def _main_reset(self):
        """Reset the main servo WP signal."""
        # If GSC is the only WP driver, there's no main wp signal to reset.
        if self._gsc_only:
            return
        super()._main_reset()

    def _force_off(self):
        """Force the firmware to not write-protected through GSC."""
        # Reset the servo flex WP signal, so it doesn't contend with GSC
        self._main_reset()
        # Use GSC to drive WP
        self._servod_set("gsc_fw_wp_state", self._STATE_FORCE_OFF)

    def _force_on(self):
        """Force the firmware to write-protected through GSC."""
        # Reset the servo flex WP signal, so it doesn't contend with GSC
        self._main_reset()
        # Use GSC to drive WP
        self._servod_set("gsc_fw_wp_state", self._STATE_FORCE_ON)

    def _get_state(self):
        """Get the firmware write-protection state."""
        return self._servod_get("gsc_fw_wp_state")
