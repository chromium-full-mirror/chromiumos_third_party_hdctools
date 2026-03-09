# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# Servod Test Plan: Firmware Auto-update Emulation

This test plan emulates the hardware-level interactions of the `firmware.FWAutoupdate` Tast test suite. It is designed to validate `servod`'s stability and correctness when subjected to the high-frequency reboot and control cycles typical of firmware regression testing.

## Prerequisites

1.  **Hardware setup:** A DUT connected to a Servo (v4/v4.1 + CCD or Micro).
2.  **Suitable Test Build:** This test plan assumes the DUT is running a test-signed image. If specific firmware versions are being tested, ensure they are available on the DUT or staged for update.
3.  **GSC State:** Ensure CCD is open and testlab is enabled if using a GSC-based connection.

## Phase 1: Initialization & Environment Check

Perform initial discovery and set the environment for firmware testing.

```bash
# Disable UART capture to avoid buffer interference during heavy logging
dut-control ec_uart_capture:off

# Discovery and Status
dut-control servo_type devices gsc_ccd_level gsc_testlab

# Ensure DUT is accessible and lid is open
dut-control lid_open:yes

# Verify EC communication
dut-control supports_cros_ec_communication
dut-control ec_uart_cmd:version
```

## Phase 2: Firmware Update Preparation

Simulate the state transitions required before a firmware update triggers.

```bash
# Set PD data role to DFP (standard for many firmware flows)
dut-control dut_pd_data_role:DFP

# Disable Firmware Write Protect
dut-control fw_wp_state:force_off

# Remove watchdogs to prevent unexpected container exits during resets
dut-control watchdog_remove:ccd_cr50
dut-control ccd_keepalive_en:on
dut-control watchdog_remove:servo_v4p1
```

## Phase 3: Cold Reboot & Network Toggle

Emulate a cold reboot cycle accompanied by Ethernet power toggling (simulating a labstation/environment transition).

```bash
# Trigger Cold Reset
dut-control power_state:reset

# Toggle Ethernet power (simulates network environment change during reboot)
dut-control dut_eth_pwr_en:off
dut-control dut_eth_pwr_en:on

# Verify PD role after reboot
dut-control dut_pd_data_role:DFP
```

## Phase 4: Multiple Warm Reboot Cycles

Perform a series of warm reboots. Firmware tests often do this to verify that the RW firmware correctly hands off or persists across soft resets.

```bash
# Cycle 1
dut-control power_state:warm_reset
dut-control dut_eth_pwr_en:off
dut-control dut_eth_pwr_en:on
# Wait for boot
sleep 10
dut-control dut_pd_data_role:DFP

# Cycle 2
dut-control power_state:warm_reset
dut-control dut_eth_pwr_en:off
dut-control dut_eth_pwr_en:on
# Wait for boot
sleep 10
dut-control dut_pd_data_role:DFP
```

## Phase 5: GSC Factory Reset (Optional/Advanced)

If emulating `ac_rw` or advanced GSC firmware update tests, perform a factory reset of the GSC state.

```bash
# Trigger GSC Factory Reset
dut-control gsc_uart_cmd:"ccd reset factory"

# Restore Write Protect (if testing update-to-locked transition)
dut-control fw_wp_state:force_on

# Final Cold Reset to apply state
dut-control power_state:reset
```

## Phase 6: Verification

```bash
# Confirm EC and Servo are still healthy
dut-control supports_cros_ec_communication servo_type
```

## Phase 7: Labstation Health Check (Regression Check)

The `firmware.FWAutoupdate` test can sometimes cause high serial console noise or PTY instability on the host Labstation. Verify that the system logs are not being flooded with respawn errors.

```bash
# On the Labstation (host), check dmesg for console-ttyS0 noise
dmesg | grep "console-ttyS0" | tail -n 20
```

*Expected Result:* No recent "terminated with status 1" or "respawning" messages during the reboot cycles.

## Notes for Users

*   **Firmware Versions:** To truly emulate `FWAutoupdate`, you may need to manually flash an older firmware version before running this plan, and then verify the version change at the end using `dut-control ec_uart_cmd:version`.
*   **Timing:** The `sleep` commands are approximate. In a real Tast test, the agent polls for SSH connectivity.
