# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# Servod Test Plan: Watchdog Disconnect via PD Role Swap

This plan verifies that the `servod` watchdog successfully detects the sudden removal of a child device (CCD/GSC) and cleanly exits the daemon.
It triggers a logical disconnection by forcing a USB-C Power Delivery role swap, which drops the data connection to the DUT.

```bash
# 1. Verify we are initially connected to the GSC/CCD
dut-control cr50_version || dut-control gsc_version

# 2. Force a disconnect by dropping the PD data role (acting as a sink)
dut-control servo_pd_role:snk

# 3. Wait for the watchdog polling interval (typically 1-3 seconds)
sleep 5

# 4. Attempt to query the daemon. If the watchdog worked correctly, 
# the daemon should have exited, and this command should FAIL (return non-zero).
# We use '!' to invert the exit code so the test PASSES when dut-control FAILS.
! dut-control serialname
```
