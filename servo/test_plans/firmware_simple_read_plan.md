# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# Servod Test Plan: Firmware Simple Read

This test plan is a simple "smoke test" designed to verify that all firmware-related read (GET) endpoints are functional on the current hardware setup. It executes a single, comprehensive batch read of the states extracted from all complex firmware test plans.

## Prerequisites

1.  **Hardware setup:** A DUT connected to a Servo.
2.  **Servod State:** `servod` must be running and actively managing the DUT.

## Phase 1: Exhaustive State Read

This command polls the state of all identified firmware controls. It validates that the endpoints exist, do not crash servod, and can successfully return a value (even if that value is 'not applicable' for the specific board).

```bash
dut-control \
    bottom_usbkey_mux \
    bottom_usbkey_pwr \
    charger_attached \
    devices \
    dut_connection_type \
    ec_active_copy \
    ec_feat \
    ec_system_powerstate \
    ec_uart_capture \
    ec_uart_cmd \
    ec_uart_stream \
    fw_wp_state \
    gsc_ccd_level \
    gsc_testlab \
    gsc_uart_capture \
    gsc_uart_cmd \
    gsc_uart_stream \
    image_usbkey_dev \
    image_usbkey_mux \
    image_usbkey_pwr \
    servo_class \
    servo_pd_role \
    servo_type \
    servo_uart_cmd \
    supports_cros_ec_communication \
    usb3_pwr_en \
    ccd_gsc.watchdog_ccd_connected
```
