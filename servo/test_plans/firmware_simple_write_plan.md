# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# Servod Test Plan: Firmware Simple Write

This test plan is a "smoke test" designed to verify the write (SET) paths for firmware-related endpoints. It sequentially executes state changes extracted from all complex firmware test plans to ensure the routing and execution logic within `servod` is functional.

## Prerequisites

1.  **Hardware setup:** A DUT connected to a Servo.
2.  **Servod State:** `servod` must be running.
3.  **Warning:** Executing these commands will rapidly change hardware states (power, write protection, multiplexers). It may leave the DUT in an unexpected state.

## Phase 1: Sequential State Writes

These commands execute the set operations.

```bash
dut-control arb_key:tab
dut-control atmega_rst:off
dut-control atmega_rst:on
dut-control ccd_keepalive_en:on
dut-control cold_reset:off
dut-control cold_reset:on
dut-control ctrl_d:tab
dut-control ctrl_u:tab
dut-control default_cold_reset:off
dut-control default_cold_reset:on
dut-control dut_eth_pwr_en:off
dut-control dut_eth_pwr_en:on
dut-control dut_pd_data_role:DFP
dut-control ec_uart_capture:off
dut-control ec_uart_capture:on
dut-control ec_uart_cmd:battery
dut-control ec_uart_cmd:chan
dut-control ec_uart_cmd:kbpress
dut-control ec_uart_cmd:reboot
dut-control ec_uart_cmd:version
dut-control ec_uart_multicmd:apshutdown
dut-control ec_uart_regexp:None
dut-control enter_key:tab
dut-control fw_wp_state:force_off
dut-control fw_wp_state:force_on
dut-control gsc_fw_wp_atboot_state:force_off
dut-control gsc_fw_wp_atboot_state:force_on
dut-control gsc_testlab:open
dut-control gsc_uart_capture:off
dut-control gsc_uart_capture:on
dut-control gsc_uart_cmd:ap_ro_verify
dut-control gsc_uart_cmd:ccd
dut-control gsc_uart_cmd:ecrst
dut-control gsc_uart_cmd:version
dut-control gsc_uart_regexp:None
dut-control image_usbkey_direction:dut_sees_usbkey
dut-control image_usbkey_mux:dut_sees_usbkey
dut-control image_usbkey_mux:servo_sees_usbkey
dut-control image_usbkey_pwr:off
dut-control image_usbkey_pwr:on
dut-control init_keyboard:on
dut-control init_usb_keyboard:off
dut-control init_usb_keyboard:on
dut-control lid_open:yes
dut-control power_key:1.200000
dut-control power_key:press
dut-control power_key:short_press
dut-control power_state:off
dut-control power_state:on
dut-control power_state:rec
dut-control power_state:reset
dut-control power_state:warm_reset
dut-control pwr_button_hold:1200
dut-control second_usbkey_direction:servo_sees_usbkey
dut-control servo_dts_mode:on
dut-control servo_pd_role:snk
dut-control servo_pd_role:src
dut-control servo_uart_cmd:cc
dut-control servo_uart_cmd:fakedisconnect
dut-control servo_uart_cmd:pd
dut-control servo_uart_cmd:usbc_action
dut-control servo_uart_regexp:None
dut-control sleep:0.05
dut-control usb3_pwr_en:off
dut-control usb3_pwr_en:on
dut-control usb_keyboard_enter_key:press
dut-control warm_reset:off
dut-control warm_reset:on
dut-control watchdog_remove:ccd_cr50
dut-control watchdog_remove:ccd_gsc
dut-control watchdog_remove:ccd_gsc_nt
dut-control watchdog_remove:servo_v4p1
```
