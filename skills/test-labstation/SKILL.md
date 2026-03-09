---
name: test-labstation
description: "Use this skill to build, flash, and test a labstation image using either a single DUT or a multi-DUT setup via a CSV list. Use whenever the user asks to test a labstation, deploy hdctools to a labstation, or run labstation tests on hardware."
---

# test-labstation

This skill guides you through building, flashing, and testing a ChromeOS labstation. Labstations are bare-metal devices (no Docker) that require specific upstart and servod testing procedures.

## Required Information (CRITICAL)
If the user requests a labstation test but does not provide the necessary parameters, you **MUST ask the user** for the missing information before proceeding.

Gather the following:
1. **Labstation Board Type:** (e.g., `fizz`, `brask`)
2. **Labstation Hostname/IP:** (e.g., `labstation.obair.xyz`)
3. **Test Mode:** Single-DUT or Multi-DUT test.
4. **DUT Information:**
   * **For Single-DUT:** The DUT `board`, `model`, and the `servo serial number`.
   * **For Multi-DUT:** A CSV list of `board,model,serial`.

**Discovery Tip:** Use `src/third_party/hdctools/tests/hardware/discover.py --backend ssh --host <HOSTNAME> --out discovered_duts.csv` to find connected serial numbers on the target labstation.

## Execution Steps

### 1. Fast Path: Deploying only `hdctools` (Recommended)
If you only need to test local `hdctools` modifications, **do not build a full image**. Building a full OS image takes 40+ minutes. Instead, deploy just the `hdctools` package to the existing system:

```bash
# Start working on the package locally
cros workon --board=<BOARD>-labstation start hdctools

# Build only the hdctools package
cros build-packages --board=<BOARD>-labstation hdctools

# Deploy directly to the labstation
cros deploy --no-ping ssh://<HOSTNAME> hdctools
```
*Note: Always use `--no-ping` with `cros deploy` or `cros flash` if the host is behind a reverse proxy tunnel (e.g., `*.obair.xyz`).*

### 2. Slow Path: Full Image Build & Flash
If the user explicitly requests a full image build, or you need to update the base OS entirely:

```bash
~/chromiumos/chromite/bin/setup_board --board=<BOARD>-labstation
cros build-packages --board=<BOARD>-labstation --accept-licenses=@CHROMEOS
cros build-image --board=<BOARD>-labstation test
cros flash --no-ping ssh://<HOSTNAME> src/build/images/<BOARD>-labstation/latest/chromiumos_test_image.bin
```

### 3. Run Bare-Metal Servod Tests
Use the provided shell scripts in `src/third_party/hdctools/tests/hardware/labstation/` to validate the daemon.

**For Single-DUT:**
```bash
scp -o StrictHostKeyChecking=no src/third_party/hdctools/tests/hardware/labstation/test_single.sh root@<HOSTNAME>:/tmp/test_single.sh
ssh -o StrictHostKeyChecking=no root@<HOSTNAME> "bash /tmp/test_single.sh -b <DUT_BOARD> -m <DUT_MODEL> -s <SERIAL> -p 9999"
```

**For Multi-DUT:**
1. Create `duts.csv` locally.
2. SCP `src/third_party/hdctools/tests/hardware/labstation/test_concurrency.sh` and `duts.csv` to `/tmp/` on the labstation.
3. Run `ssh -o StrictHostKeyChecking=no root@<HOSTNAME> "bash /tmp/test_concurrency.sh /tmp/duts.csv"`.

**Troubleshooting Upstart Failures:**
If `servod` fails to start and the logs (`/var/log/servod_<PORT>.STARTUP.log` or `latest.DEBUG`) show "No device interface (Servo Micro, C2D2, or CCD) connected", the hardware controller check is failing. You can manually patch the test script to pass `REC_MODE=1` to the upstart command (e.g., `start servod PORT=${PORT} REC_MODE=1`) to force it to bypass the controller check for testing purposes.

### 4. Generate Report
Once the test script completes, extract the output. Save this output into a Markdown file. 

**Important Guidelines for the Report:**
- **Filename Format:** The report MUST be named `report_<BOARD>-labstation_<YYYY-MM-DD>.md` (e.g., `report_brask-labstation_2026-03-01.md`).
- **Location:** Save it in the project directory.
- **Format:** Use Markdown tables and code blocks so it can easily be copied/pasted. Ensure the DUT matrix (showing which ports bound to which serials) is clearly displayed.
