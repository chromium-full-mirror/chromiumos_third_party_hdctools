---
name: test-labstation
description: "Use this skill to build, flash, and test a labstation image using either a single DUT or a multi-DUT setup via a CSV list. It handles building a generic labstation board (e.g., fizz, brask), flashing it to a specific hardware device via ssh, and running bare-metal servod tests (test_servod.sh for single DUTs, test_multidut_servod.sh for multiple DUTs). Use whenever the user asks to test a labstation or run labstation tests on hardware with multiple servos."
---

# test-labstation

This skill guides you through building, flashing, and testing a ChromeOS labstation image. Labstations are bare-metal devices (no Docker) that require specific upstart and servod testing procedures.

## Required Information (CRITICAL)
If the user requests a labstation test but does not provide the necessary parameters, you **MUST ask the user** for the missing information before proceeding. Do not assume or hallucinate serial numbers. 

Gather the following:
1. **Labstation Board Type:** (e.g., `fizz`, `brask`)
2. **Labstation Hostname/IP:** (e.g., `labstation.obair.xyz`)
3. **Test Mode:** Ask if they want to run a Single-DUT or Multi-DUT test.
4. **DUT Information:**
   * **For Single-DUT:** The DUT `board`, `model`, and the `servo serial number`.
   * **For Multi-DUT:** A CSV list (or you can assemble it) of `board,model,serial` for all connected devices.

**Discovery Tip:** If the user does not know the serial numbers connected to their labstation, offer to discover them by running the following command against their provided labstation host:
`src/third_party/hdctools/servo/tests/hardware/discover.py --backend ssh --host <HOSTNAME> --out discovered_duts.csv`

## Execution Steps

### 1. Build the Labstation Image
Build the packages and the test image for the specified labstation board.

```bash
cros build-packages --board=<BOARD>-labstation
cros build-image --board=<BOARD>-labstation test
```

### 2. Flash the Labstation Device
Flash the newly built image to the target labstation. Add `--no-ping` as needed to bypass connection checks.

```bash
cros flash --no-ping --board=<BOARD>-labstation ssh://<HOSTNAME> src/build/images/<BOARD>-labstation/latest/chromiumos_test_image.bin
```

### 3. Run Bare-Metal Multi-DUT Tests
Since labstations do not run Docker, we use the `test_multidut_servod.sh` script from the `hdctools` repository to test multiplexing the upstart service and preventing cross-talk between multiple daemons.

**Step 3a. Create the CSV locally**
Create a `duts.csv` file in your workspace containing the board, model, and serial number combinations provided by the user.

**Step 3b. Copy the test script and the CSV to the labstation**
```bash
scp -o StrictHostKeyChecking=no src/third_party/hdctools/servo/tests/hardware/labstation/test_concurrency.sh root@<HOSTNAME>:/tmp/test_multidut_servod.sh
scp -o StrictHostKeyChecking=no duts.csv root@<HOSTNAME>:/tmp/duts.csv
```

**Step 3c. Execute the multi-DUT test script**
```bash
ssh -o StrictHostKeyChecking=no root@<HOSTNAME> "bash /tmp/test_multidut_servod.sh /tmp/duts.csv"
```

### 4. Generate Report
Once the test script completes, extract the output (especially the isolation checks and telemetry execution passes). Save this output into a Markdown file. 

**Important Guidelines for the Report:**
- **Filename Format:** The report MUST be named `report_<BOARD>-labstation_<YYYY-MM-DD>.md` (e.g., `report_brask-labstation_2026-03-01.md`). Get the current date using the `date` command or system context.
- **Location:** Save it in the project directory.
- **Format:** Use Markdown tables and code blocks so it can easily be copied/pasted into a Google Doc. Ensure the Multi-DUT matrix (showing which ports bound to which serials) is clearly displayed.
