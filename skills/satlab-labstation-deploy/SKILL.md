# Satlab with External Physical Labstation: Architecture, Deployment, and Testing

<description>
This skill provides comprehensive instructions on setting up a Satlab environment with an external, physical Labstation (for ChromeOS hardware testing), strategies for staggered mass deployments, avoiding USB initialization storms, and executing tests via the Swarming queue.
</description>

## Table of Contents
1. [Core Architecture and Networking](#core-architecture-and-networking)
2. [Prerequisites and Kernel Quirks](#prerequisites-and-kernel-quirks)
3. [Registering and Unregistering DUTs (UFS)](#registering-and-unregistering-duts-ufs)
4. [Deployment Challenges and Hardware Limits](#deployment-challenges-and-hardware-limits)
5. [The Concurrency Guard Pattern (Safe Deployments)](#the-concurrency-guard-pattern-safe-deployments)
6. [Executing Tests (Crosfleet & Satlab)](#executing-tests-crosfleet--satlab)
7. [Common Failure Modes and Debugging](#common-failure-modes-and-debugging)

---

## 1. Core Architecture and Networking

In this topology, instead of relying on the local Satlab Docker `servod` container, a physical Labstation (`192.168.231.x`) is used to control multiple Servo V4.1 interfaces connected to DUTs.

*   **Satlab Host:** Handles DNS, Swarming (`drone-agent`), and UFS scheduling. Runs at `192.168.100.x`.
*   **Labstation:** A dedicated, physical machine running `servod_core` and `servod_data` per DUT. Runs at `192.168.231.x`.

### Network Routing (In-Memory)
Because Swarming tasks run inside a Docker container on the Satlab host (`192.168.100.x`), the Labstation *must* have a route back to the Satlab devserver to download ChromeOS images.

**Required Labstation Route (Run on Labstation):**
```bash
ip route add 192.168.100.0/24 via 192.168.231.1
```

### DNS Configuration
The Swarming container relies entirely on the Satlab host's DNS to resolve target IP addresses. If you change a DUT or Labstation IP address, the Swarming task will ping the old stale IP and fail.

**Update DNS Records (Run on Satlab Host):**
```bash
satlab update dns -host <LABSTATION_HOSTNAME> -address <LABSTATION_IP>
satlab update dns -host <DUT_HOSTNAME> -address <DUT_IP>
```

---

## 2. Prerequisites and Kernel Quirks

A single physical Labstation has a finite amount of CPU cores and a single XHCI USB 3.0 root controller. When chaining multiple Servo V4.1s (which contain internal GenesysLogic hubs), you **must** apply kernel quirks to prevent USB bus deadlocks.

**Required Labstation GRUB/Boot Quirks:**
```
usbcore.quirks=05e3:0625:k xhci-hcd.quirks=524288
```
Without these, a mass deployment will trigger a fatal `error -110 ETIMEDOUT` storm in `dmesg`, causing the USB hardware to vanish entirely until a hard power-cycle.

---

## 3. Registering and Unregistering DUTs (UFS)

### Adding/Registering a DUT (Via Satlab CLI)
To explicitly force Swarming to use the physical Labstation instead of the Satlab Docker container, you must register the DUTs with `-servod-docker ""` via the `satlab` CLI.

```bash
satlab add dut \
  -name <SATLAB_ID>-host1 \
  -board brya \
  -model banshee \
  -address <DUT_IP> \
  -asset <ASSET_TAG> \
  -servo-serial <SERVO_SERIAL> \
  -servo-host <LABSTATION_HOSTNAME>:<PORT> \
  -servod-docker ''
```

### Unregistering/Deleting a DUT (Via Shivas)
To remove a DUT from UFS or force the orchestration layer to drop stuck Swarming bots, use `shivas`. You must run this on the Satlab host and provide the service account JSON key:

```bash
shivas delete dut \
  -namespace os \
  -service-account-json /home/satlab/keys/pubsub-key-do-not-delete.json \
  <SATLAB_ID>-host1
```

### Deploying/Adding a DUT from a JSON Payload
If you have a previously exported JSON configuration, you can use `shivas` directly to trigger a deployment:
```bash
shivas add dut \
  -f payload.json \
  -namespace os \
  -service-account-json /home/satlab/keys/pubsub-key-do-not-delete.json
```

---

## 4. Deployment Challenges and Hardware Limits

When attempting to deploy an entire 10-device rack simultaneously, you will encounter two major physical and infrastructure bottlenecks:

1.  **The Initialization Storm (Hardware Collapse):** 10 Swarming tasks starting `servod` concurrently will flood the Labstation XHCI bus with hardware probing packets (EC, Cr50, Servo Micro checks). This crashes the USB controller and spikes the 4-core Labstation CPU Load Average above 30.0.
2.  **The I/O Storm (Swarming Timeout):** Writing 10x 3GB OS images to USB sticks concurrently saturates disk bandwidth, dropping speeds to < 1 MB/s. Swarming has a hard-coded **50-minute timeout** for the `servo_download_image_to_usb` step. Devices stuck in the saturated I/O queue will hit this timeout and fail.

---

## 5. The Concurrency Guard Pattern (Safe Deployments)

To safely deploy 10 devices, the physical Labstation must only process **3 concurrent operations** at any given time.

### Implementation: Staggered Queuing
When doing mass deployments, you must batch your `shivas add` commands.

**Example Staggering Script (Run on Satlab Host):**
```bash
# Deploy in batches of 3, separated by 25-minute sleeps to avoid the 50m timeout
for host in <SATLAB_ID>-host1 <SATLAB_ID>-host2 <SATLAB_ID>-host3; do
    shivas delete dut -namespace os -service-account-json /home/satlab/keys/pubsub-key-do-not-delete.json $host
    sleep 5
    shivas add dut -f payload.json -namespace os -service-account-json /home/satlab/keys/pubsub-key-do-not-delete.json
done

# Wait for 3GB USB downloads to finish before queuing the next batch
sleep 1500 

for host in <SATLAB_ID>-host4 <SATLAB_ID>-host5 <SATLAB_ID>-host6; do
    # ...
```

### Future-Proofing: OS-Level Concurrency Locks
Labstation OS images should be built with an execution wrapper (e.g., `labstation_ready_for_deploy`) that utilizes a file descriptor lock (`flock`) to artificially gate `servod` startup and `image_downloader` actions to 3 concurrent processes. 

---

## 6. Executing Tests (Crosfleet & Satlab)

Once the DUTs are safely deployed and booted into their ChromeOS images, tests are queued to Swarming via the Satlab host.

**Warning on Missing CLI Tools:** 
If executing automated scripts in the background, remember that `crosfleet` and `satlab` commands may not be in the local `$PATH`. Use SSH to execute them directly on the Satlab instance with absolute paths.

**Queueing standard BVT and FAFT Suites (Run on Satlab Host):**
```bash
# Phase 1: BVT (Build Verification)
/usr/local/bin/crosfleet run suite -board brya -model banshee -suite bvt-inline -pool satlab -milestone 147 -build 16610.11.0 -dims "dut_name=<SATLAB_ID>-host1"

# Phase 2: FAFT (Firmware Auto Test - Heavy EC/BIOS Serial IPC traffic)
/usr/local/bin/satlab run -board brya -model banshee -suite faft_ec -pool satlab -milestone 147 -build 16610.11.0 -dims "dut_name=<SATLAB_ID>-host1"
```

*Note: FAFT tests aggressively reset the DUT's Embedded Controller (EC). Do not be alarmed if the DUTs start emitting loud, continuous BIOS warning beeps during execution.*

---

## 7. Common Failure Modes and Debugging

### A. USB Drives Not Formatting / Swarming Download Failure
If the `image_downloader` fails because it cannot find the block device:
1. Ensure the Labstation has switched the mux to itself, not the DUT:
   ```bash
   dut-control -p <PORT> image_usbkey_direction:servo_sees_usbkey
   ```
2. Verify the physical flash drive exists via `lsblk`.

### B. Hardware "Vanishing" from Labstation
If `lsusb` shows a sudden drop in connected servos or `servodtool` throws `Device with serial <X> not found`:
*   **Cause:** The USB XHCI controller has electrically crashed (`error -110` in `dmesg`).
*   **Fix:** The Labstation must be physically power-cycled. Software restarts of `servod` will not recover a crashed root hub. Stagger future deployments to prevent recurrence.

### C. Test Payload "Enumeration Error"
If a test immediately fails in Swarming with `enumeration error: no test found for suite "cts_setup"`:
*   **Cause:** The specific suite payload does not exist for the ChromeOS milestone/build combination you specified.
*   **Fix:** Check that the correct milestone and build ID were passed to the `satlab run` command, or verify the suite is supported on that branch.

### D. Servod Logging Races
If `servod` crashes entirely with a `FileExistsError` related to `latest.DEBUG`:
*   **Cause:** A known regression in the Fission architecture (`servod_core` and `servod_data` racing to create a symlink in a shared log directory).
*   **Fix:** Ensure the Labstation is flashed with a modern OS image where this logging IPC race condition is patched.
