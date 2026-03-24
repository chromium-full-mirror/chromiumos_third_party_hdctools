# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from servo.data.drv import hw_driver


class usbkeyAvailability(hw_driver.HwDriver):
    """Driver to ensure USB key availability on the DUT."""

    def _set(self, value):
        self._logger.info("ensure_usbkey_available: processing value=%s", value)
        if value == "off":
            # No-op to disable, caller handles restore of src mode if necessary
            return

        if (
            not self._servod_has_control("root.dut_connection_type")
            or self._servod_get("root.dut_connection_type") != "type-c"
        ):
            self._logger.info("Not a Type-C connection, skipping role swap")
            return

        board = "unknown"
        try:
            if self._servod_has_control("ec_board"):
                board = self._servod_get("ec_board")
                self._logger.info("Detected board: %s", board)
        except Exception as e:
            self._logger.debug("Failed to get ec_board: %s", e)

        if board != "grunt":
            # Chromeboxes and PDC DUTs don't need servo_pd_role:snk
            is_chromebox = self._params.get("is_chromebox", "no") == "yes"
            is_pdc_dut = self._servod_has_control("pdc_ccd_keepalive_en")

            if not is_chromebox and not is_pdc_dut:
                # Attempt to set servo power role to sink, which usually works for all Type-C
                # to enumerate the USB key.
                # Try root prefix first (standard for Servo v4.1), then no prefix
                for ctrl in ["root.servo_pd_role", "servo_pd_role"]:
                    if self._servod_has_control(ctrl):
                        try:
                            self._servod_set(ctrl, "snk")
                            self._logger.info("Set %s to snk for USB availability", ctrl)
                            break
                        except Exception as e:
                            self._logger.error("Failed to set %s to snk: %s", ctrl, e)

        # Force PD data swap to DFP on the DUT side
        if self._servod_has_control("dut_pd_data_role"):
            try:
                self._servod_set("dut_pd_data_role", "DFP")
                self._logger.info("Set dut_pd_data_role to DFP")
            except Exception as e:
                self._logger.error("Failed to set DUT's role to DFP: %s", e)
        else:
            self._logger.error("No suitable role swap control found")
