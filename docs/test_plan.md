# Servod Test Plan

This document outlines the comprehensive testing strategy for `servod`. It is intended for use by developers and automated agents to ensure the stability and correctness of the servo framework.

## 1. Overview

Testing `servod` involves several layers, from low-level unit tests of individual drivers to high-level end-to-end (E2E) tests involving real hardware.

## 2. Testing Layers

### 2.2 Unit Testing
Unit tests are located in `servo/tests/unit`. They use `pytest` and mock hardware interfaces to test logic in isolation.

**How to run:**
```bash
(HOST) $ run-servod-tests servo/tests/unit
```

### 2.3 End-to-End (E2E) Testing
E2E tests verify the entire stack, from `dut-control` to the hardware drivers. These tests can run against simulated hardware or real devices.

**How to run against simulated hardware:**
```bash
(HOST) $ run-servod-tests servo/tests/e2e
```

### 2.4 Hardware-in-the-Loop (HIL) Testing
HIL testing requires a real Servo device and a DUT (Device Under Test). This is the most realistic test but requires manual setup.

**Setup Requirements:**
- A Servo device (e.g., Servo V4, V4.1) connected to the host.
- A DUT (e.g., Brya Banshee) connected to the Servo.
- Docker installed and configured on the host.

## 3. Remote Testing via Test Orchestra

The `test_orchestra` infrastructure allows running tests on remote local machines that have hardware attached.

### 3.1 Orchestrator
The orchestrator service manages job queues and collects results. It is located in `development_environment/test_orchestrator`.

### 3.2 Local Agent
The `local_agent.py` runs on the machine with physical hardware. It polls the orchestrator for jobs, executes them, and reports back.

## 4. Regression Testing against Golden Build

To ensure no regressions, tests should be run against both the current local build and the "golden" release build.

**Release Channel Images:**
The "golden" build is typically available in the release channel. You can find the image name in the release pipeline or use the latest stable tag:
`us-docker.pkg.dev/chromeos-hw-tools-dev/servod/servod:release`

## 5. Test Areas

## 6. HIL Test Suites (Brya Banshee)

These suites are used to verify the refactored codebase against a "golden" release build.

### 6.1 Identity & Connectivity (Basic Checks)
| Control | Expected Value |
| :--- | :--- |
| `servo_fw_version` | Match Hardware |
| `ec_board` | `banshee` |
| `ec_chip` | `npcx_uut` |
| `servo_type` | `servo_v4p1_with_ccd_cr50` (or similar) |

### 6.2 Power Sequencing
**Note:** Order matters for these tests.
1. `power_state:off` -> Verify `ec_system_powerstate` is G3 or S5.
2. `power_state:on` -> Verify `ec_system_powerstate` is S0.
3. `power_state:rec` -> Verify DUT enters recovery mode.

### 6.3 Hardware Interface
1. `cold_reset:on` followed by `cold_reset:off`.
2. `warm_reset:on` followed by `warm_reset:off`.
3. `pwr_button:press` -> Verify power state change.

### 6.4 Telemetry (Tolerance-based)
These values are compared between the Local Build and the Golden Build. Discrepancies > 10% should be investigated.
- `ppvar_vbat_mv` (Voltage)
- `ppvar_vbat_ma` (Current)
- `avg_ppvar_vbat_ma`

## 7. Automated HIL Execution (Test Orchestra)

Instead of using raw HTTP endpoints, use the `submit_test.py` wrapper script to queue tests and parse the results automatically.

To run the full suite:

```bash
# Local Build
./development_environment/test_orchestrator/submit_test.py \
    --board brya --model banshee \
    --image us-docker.pkg.dev/chromeos-hw-tools-dev/servod-scratch/servod:haddowk \
    --cmds ec_board cold_reset warm_reset ppvar_vbat_mv

# Golden Build
./development_environment/test_orchestrator/submit_test.py \
    --board brya --model banshee \
    --channel release \
    --image us-docker.pkg.dev/chromeos-hw-tools-dev/servod/servod:release \
    --cmds ec_board cold_reset warm_reset ppvar_vbat_mv
```

## 8. Manual Testing Plan
For areas not covered by remote orchestration:
- **`servodtool` CLI:** Manually run `servodtool device -s <serial>` and `servodtool instance list` on the host.
- **`dut-power`:** Manually run `dut-power` for 60 seconds to verify power graph generation.
- **Physical Disconnect:** Physically unplug the Servo while `servod` is running and verify the Watchdog triggers a clean shutdown.
