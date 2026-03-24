# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from servo.drv import hw_driver


class usbkeyAvailability(hw_driver.HwDriver):
    """Driver to ensure USB key availability on the DUT."""

    def _set(self, value):
        if value == "off":
            # No-op to disable, caller handles restore of src mode if necessary
            return

        if (
            not self._servod_has_control("root.dut_connection_type")
            or self._servod_get("root.dut_connection_type") != "type-c"
        ):
            return

        is_ro = False
        try:
            if self._servod_has_control("ec_active_copy"):
                ec_copy = self._servod_get("ec_active_copy")
                if isinstance(ec_copy, str) and "active_ro" in ec_copy:
                    is_ro = True
        except Exception as e:
            self._logger.debug("Failed to check ec_active_copy: %s", e)

        board = "unknown"
        try:
            if self._servod_has_control("ec_board"):
                board = self._servod_get("ec_board")
        except Exception as e:
            self._logger.debug("Failed to get ec_board: %s", e)

        if is_ro and board != "grunt":
            # Chromeboxes and PDC DUTs don't need servo_pd_role:snk
            is_chromebox = self._params.get("is_chromebox", "no") == "yes"
            is_pdc_dut = self._servod_has_control("pdc_ccd_keepalive_en")

            if not is_chromebox and not is_pdc_dut:
                # Attempt to set servo power role to sink, which usually works for all Type-C
                # to enumerate the USB key in RO mode.
                if self._servod_has_control("servo_pd_role"):
                    try:
                        self._servod_set("servo_pd_role", "snk")
                        self._logger.debug(
                            "Set servo_pd_role to snk for USB availability"
                        )
                        return
                    except Exception as e:
                        self._logger.debug("Failed to set servo_pd_role to snk: %s", e)

        # Fallback to pd data swap if snk fails, or for grunt
        if self._servod_has_control("dut_pd_data_role"):
            try:
                self._servod_set("dut_pd_data_role", "DFP")
                self._logger.debug("Set dut_pd_data_role to DFP as fallback")
            except Exception as e:
                self._logger.debug("Failed to set DUT's role to DFP: %s", e)
