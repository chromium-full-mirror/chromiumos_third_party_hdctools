# Quickstart Guide: Hardware-in-the-Loop (HIL) Testing

This guide provides the simplest way for a new test operator to validate `servod` against physical hardware.

---

## 🏗️ Method A: Testing on Local Hardware (Docker)
Use this if you have Servos plugged directly into your laptop or a local gLinux machine.

### 1. Prepare your Test Machine
On your local machine (connected to the hardware), run the bootstrapper to set up the connection back to your Cloudtop:
```bash
./bootstrap_agent.sh <YOUR_CLOUDTOP_HOSTNAME>
```
*Leave this terminal running. It will poll for test jobs.*

### 2. Discover your Hardware
On your **Cloudtop**, automatically generate the list of connected Servos:
```bash
./src/third_party/hdctools/tests/hardware/discover.py --backend local --out my_duts.csv
```

### 3. Run the Test
On your **Cloudtop**, fire off the parallel tests:
```bash
./run_multidut_orchestrator.sh my_duts.csv
```
*View your results in `orchestrator_report_*.txt` files.*

---

## 🧪 Method B: Testing on a Labstation (SSH)
Use this if you are testing hardware already deployed in a lab rack.

### 1. Discover the Labstation Hardware
On your **Cloudtop**, probe the remote labstation to see what is plugged in:
```bash
./src/third_party/hdctools/tests/hardware/discover.py --backend ssh --host <LABSTATION_IP> --out lab_duts.csv
```

### 2. Run the Labstation Suite
Still on your **Cloudtop**, run the automated bare-metal test:
```bash
scp lab_duts.csv root@<LABSTATION_IP>:/tmp/duts.csv
ssh root@<LABSTATION_IP> "bash /tmp/test_multidut_servod.sh /tmp/duts.csv"
```
*Results will be printed to your console and saved as `report_*.md`.*

---

## 🛠️ Common Fixes
*   **"No Servo Micro/CCD detected"**: Hardware cable is loose or needs flipping.
*   **"No data sent from PTY"**: The Chromebook EC is stuck. Hard-reset the DUT.
*   **"Permission Denied"**: Ensure your SSH keys are added (`ssh-add`).

**Need more detail?** See the full [Labstation Testing Guide](labstation_testing.md).


---


# Labstation Bare-Metal Testing Guide

## 1. Overview
Labstations run physical, bare-metal instances of `servod` directly via Upstart (unlike standard test servers which use Docker). This guide explains how to validate `servod` deployments on labstations, ensuring both single-DUT functionality and multi-DUT concurrency (ensuring no cross-talk or resource starvation).

If you are using Gemini, you can simply ask: **"Run the test-labstation skill"** and the agent will guide you through this process automatically.

## 2. Prerequisites & Discovery
To run these tests, you must know:
1. **Labstation Board Name:** (e.g., `fizz`, `brask`)
2. **Labstation Hostname/IP:** (e.g., `labstation.obair.xyz`)
3. **DUT Details:** The board, model, and Servo serial number(s) connected to the labstation.

**💡 Pro-Tip: Discovering Connected Servos**
If you do not know the serial numbers of the servos connected to a labstation, you can SSH into the labstation and list them:
```bash
ssh -o StrictHostKeyChecking=no root@<LABSTATION_HOST> "lsusb -v | grep -i iSerial"
```

## 3. Workflow: Single-DUT Testing

Use this to validate that a single instance of `servod` can successfully initialize, bind to a device, and stream telemetry.

### 3.1 Build and Flash
```bash
cros build-packages --board=<BOARD>-labstation
cros build-image --board=<BOARD>-labstation test
cros flash --no-ping --board=<BOARD>-labstation ssh://<HOSTNAME> src/build/images/<BOARD>-labstation/latest/chromiumos_test_image.bin
```

### 3.2 Execute Test Script
Copy the test script to the labstation and execute it:
```bash
scp -o StrictHostKeyChecking=no src/third_party/hdctools/tests/hardware/labstation/test_single.sh root@<HOSTNAME>:/tmp/test_servod.sh
ssh -o StrictHostKeyChecking=no root@<HOSTNAME> "bash /tmp/test_servod.sh -b <DUT_BOARD> -m <DUT_MODEL> -s <SERVO_SERIAL> -p 9999"
```

## 4. Workflow: Multi-DUT Concurrency Testing

Use this to validate that multiple `servod` daemons can multiplex on the same host, assigning unique gRPC ports, without causing USB cross-talk.

### 4.1 Prepare the CSV payload
Create a file locally named `duts.csv` with the following format (no headers):
```csv
brya,banshee,SERVOV4P1-C-2210050067
brya,banshee,SERVOV4P1-C-23091212643
```

### 4.2 Execute Test Script
```bash
scp -o StrictHostKeyChecking=no src/third_party/hdctools/tests/hardware/labstation/test_concurrency.sh root@<HOSTNAME>:/tmp/test_multidut_servod.sh
scp -o StrictHostKeyChecking=no duts.csv root@<HOSTNAME>:/tmp/duts.csv
ssh -o StrictHostKeyChecking=no root@<HOSTNAME> "bash /tmp/test_multidut_servod.sh /tmp/duts.csv"
```

## 5. Troubleshooting Test Failures
* **"No Servo Micro, C2D2, or CCD detected"**: The `servod` daemon started, but could not see the downstream Chromebook interface. Try flipping the USB-C cable physically connected to the DUT.
* **"No DUT plugged into servo"**: The Type-C cable is completely disconnected or the DUT is entirely powered off/dead.
* **"Log file not found at /var/log/servod_XXXX/latest.DEBUG"**: The Upstart daemon failed to spawn entirely. Check `/var/log/messages` on the labstation for raw Upstart failures.
