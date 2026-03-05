<!--Copyright 2023 The ChromiumOS Authors
Use of this source code is governed by a BSD-style license that can be
found in the LICENSE file. -->

# Servo Firmware Update Process in Google ChromeOS Fleet

Note this document is intended for Google internal use, the tools and documents this
document links to are restricted to and useful for Googlers only.

# Objective

To be able to roll out servo firmware updates in the chromeos fleet we need to be able
to update a certain number of new servos to the new firmware, monitor and then increase
the number of servos that are using the new firmware until the update is fully rolled
out.

This document details the mechanism of updating servos in the chrome os fleet and
monitoring if they have actually updated. Out of scope of this document is the process
of selecting DUT’s for update and the criteria deciding if a new servo firmware is
working, what channels to use and when to move from a non stable channel back to stable.

# Requirements

The new servo firmware must be in the current labstation release in one of the channels
other than stable. Assuming you know what firmware channel you are updating to you can
check this file ([link](https://chromium.googlesource.com/chromiumos/third_party/hdctools/+/refs/heads/main/dockerfiles/servo_firmware_provision.py#10)) to look for the channel for the right servo device.

To run the tools you will need:

- A gLinux instance.
- A security key configured for SSH ([link](https://support.google.com/techstop/answer/12796659?sjid=9417562964595548830-NA))
- Setup ssh access to devices in the fleet ([link](go/chromeos-lab-ssh))
- Shivas tool installed ([link](https://g3doc.corp.google.com/company/teams/chrome/ops/fleet/software/teams/fleet-automation/inventory/unified-fleet-system/tooling/shivas-installation.md?cl=head)), make sure `shivas whoami` works.
- Write access to the “ma” update list spreadsheet [here](https://docs.google.com/spreadsheets/d/11f6EIuF1UpA1y6L2jsuLe9mPfh05e6uZU5TTBqDaZSs/edit?resourcekey=0-EmWH8U3P7tWkBVwOANNFpA#gid=0)
- [Code](fleet_rollout.py) for the servo firmware tool

# Background

In essence the process of updating a DUT is simple. You just need to:

Update the fleet database for that device to select a new channel

```
shivas update dut -name <hostname> -servo-fw-channel DEV
```

Schedule a repair job for that host, as part of the repair process it will check that
the correct servo firmware is present and if not update the firmware.

```
shivas  repair <hostname>
```

However repair jobs expire after 10 minutes so you may need to keep running repair jobs
on DUT that do not update in that time. This can happen if there are long running test
jobs on a busy DUT.

# Tooling

A simple script that helps perform servo updates at scale is available [here](fleet_rollout.py).

## Install

It's part of a hdctool checkout, and you can either use it from there directly
or copy it somewhere more suitable (e.g. some directory in your $PATH).

The script uses a F1 database table to enumerate the DUT’s to act on. The contents of
that table are controlled by the spreadsheet [here](https://docs.google.com/spreadsheets/d/11f6EIuF1UpA1y6L2jsuLe9mPfh05e6uZU5TTBqDaZSs/edit?resourcekey=0-EmWH8U3P7tWkBVwOANNFpA#gid=0).

The spreadsheet has just 1 tab and 1 column, fill in the hostnames you want the script
to act on. Then go to this [link](https://plx.corp.google.com/pipelines/workflow/plx_importer_wf_766f4055_e65b_4e9f_a628_2f3472c94859?m=view) and press the “Run Now”
button, which will update the database with whatever is in the spreadsheet. It might
take about 5 minutes.

Pressing the “Run Now” button will take all the values from the spreadsheet and put them
in the database table. That table is used as the list of DUT to act on both for the
script and for the monitoring dashboard, so they will both be updated \
 \
Note that the script is safe for DUT’s that have already been updated, so you can extend
the list in the spreadsheet and run the script to update the channel, DUT’s that have already
been updated will be ignored and so will not cause any issue.

```
usage: fleet_rollout.py [-h] [--channel {ALPHA,BETA,DEV,STABLE}] [--repair_if_not_updated REPAIR_IF_NOT_UPDATED] [--all {servo_v4,servo_v4p1}]

options:
  -h, --help            show this help message and exit
  --channel {ALPHA,BETA,DEV,STABLE}
                        What FW channel to update to.
  --repair_if_not_updated REPAIR_IF_NOT_UPDATED
                        Run repair on devices if they firmware does not match the supplied firmware version
  --all {servo_v4,servo_v4p1}
                        What servo to update
```

Running:

```
fleet_rollout.py
```

With no arguments will result in a csv formatted output of the status of the DUT/servo
fw details in a table. DUT hostname, shivas channel, shivas firmware version are the
three columns. It is easy to copy paste this into a spreadsheet and use conditional
formatting to see what anomalies need to be fixed.

```
./fleet_rollout.py
chromeos8-row11-rack2-host47,SERVO_FW_ALPHA,servo_v4p1_v2.0.20646-1fb66a343
chromeos8-row11-rack2-host10,SERVO_FW_ALPHA,servo_v4p1_v2.0.20646-1fb66a343
chromeos8-row11-rack2-host37,SERVO_FW_ALPHA,servo_v4p1_v2.0.20646-1fb66a343
chromeos8-row11-rack2-host13,SERVO_FW_ALPHA,servo_v4p1_v2.0.20646-1fb66a343
```

This is useful for monitoring the status - how many of the servos have actually updated
to the new firmware and if any shivas db entries have regressed to STABLE ( this happens
if the device is removed/replaced in the lab )

Running

```
fleet_rollout.py --channel ALPHA
```

Will change the channel for each device to ALPHA in shivas if it is not already at that
value. If the entry in shivas is updated then a repair job for the device will also be
scheduled.

Running

```
fleet_rollout.py --repair_if_not_updated <firmware version>
```

Will check the servo firmware version for each DUT, if the fw version does not match the
string specified in the arguments it will schedule a repair job for that DUT.

You can find the firmware version for the channel you are expecting by looking at this
file
[link](https://chromium.googlesource.com/chromiumos/third_party/hdctools/+/refs/heads/main/dockerfiles/servo_firmware_provision.py#10)

# Known Issues

- You need to type gcert and follow the prompts to touch your security key. You will
  have to do this every 19 hours or so. \
  If it expires you will see a message like :

```

  Traceback (most recent call last): File
  "/usr/local/google/home/haddowk/fw_update_scripts/./fleet_rollout.py", line 129, in
  <module> main(sys.argv) File
  "/usr/local/google/home/haddowk/fw_update_scripts/./fleet_rollout.py", line 119, in
  main for hostname in get_hostnames()[1:]: File
  "/usr/local/google/home/haddowk/fw_update_scripts/./fleet_rollout.py", line 17, in
  get_hostnames subprocess.check_output( File "/usr/lib/python3.10/subprocess.py", line
  421, in check_output return run(\*popenargs, stdout=PIPE, timeout=timeout, check=True,
  File "/usr/lib/python3.10/subprocess.py", line 526, in run raise
  CalledProcessError(retcode, process.args, subprocess.CalledProcessError: Command
  '('f1-sql', '--csv_output')' returned non-zero exit status 126.

```


*   Repair jobs expire after 10 minutes.  Use the `repair_if_not_updated` option on `fleet_rollout.py `to schedule new repair jobs.


# Manually Updating Servos

If you need to update a servo manually this is my process:

Run:

```
shivas get dut <hostname>
```

Look for the labstation associated with that hostname

```
ssh root@<labstation>
```

Check the version of labstation


```
cat /etc/lsb-release
```

check what value in  CHROMEOS\_RELEASE\_CHROME\_MILESTONE make sure it is what you expect.

See if the device is visible via USB

```
lsusb -v | grep iSerial | grep SERVO
```

Look for the serial number that was returned by shivas

Make sure that servo is not busy with something else

```
ps aux | grep <serial number>
```

Make sure there is no servod running for this serial number.

Run the updater

```
servodtool device -s <serial number> reboot servo_updater -b servo_v4p1 -s
<serial number> -c <channel>
```

# Disclaimer
- This script and instructions are provided as-is and may require modifications to fit your specific use case.
- Always exercise caution when performing firmware updates on production devices.
- Ensure you understand what you are doing and have recovery plan in place.
