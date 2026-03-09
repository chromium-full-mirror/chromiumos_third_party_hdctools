# Servo Devices FW Release Process

# Objective

This document aims to describe process and necessary tools to release new firmware for Servo devices across the ChromeOS landscape.

# Background

Servos are critical equipment in our fleet and need to work reliably with all boards we support, in different environments, including: fleet, developers, partners. That is why we want to be extremely careful in servo new firmware release process.

# Get firmware binary

- servo_v4p1
    - we are using EC ToT, so get specific file/dir from [EC branch builder](https://luci-scheduler.appspot.com/jobs/chromeos/firmware-ec-postsubmit)
    - when FW image is qualified please cut off EC main branch and create specific branch for release, e.g. http://b/362215509
    - in case of fast-track we currently building locally from release branch with CL cherry-picked (TODO: need to work on instruction for creating fully functional branch&builder)
- servo_v4, servo_micro, c2d2
    - we are using servo branch, so get specific file/dir from [servo branch builder](https://luci-scheduler.appspot.com/jobs/chromeos/firmware-servo-12768.B-branch)


# Firmware preparation and validation instructions

Please start with manual verification on desk. That's important part before moving forward.
You can find instructions how to update device firmware on specific device doc pages.

- [servo_v4p1](https://chromium.googlesource.com/chromiumos/third_party/hdctools/+/HEAD/docs/servo_v4p1.md#updating-firmware)
- [servo_v4](https://chromium.googlesource.com/chromiumos/third_party/hdctools/+/HEAD/docs/servo_v4.md#updating-firmware)
- [servo_micro](https://chromium.googlesource.com/chromiumos/third_party/hdctools/+/HEAD/docs/servo_micro.md#updating-firmware)
- [c2d2](https://chromium.googlesource.com/chromiumos/third_party/hdctools/+/HEAD/docs/c2d2.md#updating-firmware)

Second stage is verification in fleet after initial binaries deployment.

## Manual testing

Goal is to manually ensure basic functionality of servo device with new FW on desk.

This includes: (a) testing servo itself, (b) testing compatibility with DUT(s).
**At least 2 different servo units and 3 different DUT boards should be used.**

For details see separate document [here](servo_release_manual_testing.md)


## Preparing and deploying binary to cloud

After we manually verified binary we need to pack FW into archive, send it to [cloud bucket](https://pantheon.corp.google.com/storage/browser/chromeos-localmirror/distfiles) and make it available to public. You can use you below script to do it for you.

Requirements:
 - gsutil + gcloud auth login

Script calls:
- for servo_v4p1 - path to build artifacts directory

```
./prepare_binary.sh /path/to/build/artifacts/servo_v4p1
```

- for others - path to build artifacts directory and version string (as we can't get it from artifacts)

```
./prepare_binary.sh /home/hajec/Downloads/servo_v4 servo_v4_v2.4.83-5e9611ca0c
```

You should see output like this:
```
Copying file://servo_v4p1_v2.0.24152-0b36eb51a.tar.xz [Content-Type=application/x-tar]...
- [1 files][ 57.1 KiB/ 57.1 KiB]
Operation completed over 1 objects/57.1 KiB.

Updated ACL on gs://chromeos-localmirror/distfiles/servo_v4p1_v2.0.24152-0b36eb51a.tar.xz

Done! Created servo_v4p1_v2.0.24152-0b36eb51a.tar.xz and uploaded to https://pantheon.corp.google.com/storage/browser/_details/chromeos-localmirror/distfiles/servo_v4p1_v2.0.24152-0b36eb51a.tar.xz
```
## Deploying binary to fleet

We should deploy NEW files to fleet only on ALPHA(or DEV in case of servo_micro/c2d2) channel, once FW is validated in fleet, we can slowly roll out changes to all devices and modify STABLE(default) channel.

Note:
Currently fleet SW architecture allows for only one FW channel per setup, so all connected servos use the same channel. E.g. we have setup with DUT+servo_micro+servo_v4 and we are rolling out new FW for servo_micro, so we are going to change channel to DEV. In that case servo_v4 in that setup is going to receive also FW that is under DEV channel. To reduce interference when releasing new FW for servo_v4pX under ALPHA for uservo/c2d2 there should be same image as stable and vice versa DEV for servo_v4pX should always follow STABLE.

In fleet firmware is shared via labstation image, so we need to modify specific Ebuild:

1. Update `~/chromiumos/src/third_party/chromiumos-overlay/sys-firmware/servo-firmware/servo-firmware-0.0.1.ebuild`

    Change string under specific channel and device you want to modify to new version.
2. Update shortcut link to the ebuild release by renaming and incrementing the version.

    `servo-firmware-0.0.1-r14.ebuild 🠒 servo-firmware-0.0.1-r15.ebuild`
3. You need to update the manifest file by running in chroot:

     ```ebuild servo-firmware-0.0.1.ebuild manifest```

    which will compute the new hashes (relative path to ebuild file required)
4. For patch verification run:

    `sudo emerge servo-firmware`

    This will to update your local copy in chroot. Then run servo_updater inside chroot with new binary. Verify in device console that `version` shows expected new version.

5. Prepare CL and send to review, if needed cherry-pick this specific CL on branch that is going to be used in nearest labstation release cycle. Also CP to other branches that are already created, to have these files in all next releases.

    - [CL example](https://chromium-review.googlesource.com/c/chromiumos/overlays/chromiumos-overlay/+/5349499)
    - [CP example](https://chromium-review.googlesource.com/c/chromiumos/overlays/chromiumos-overlay/+/5349500)


## Deploying binary to other users (dockerized servod users)

We aim to synchronize deploying images in fleet and to other users (via docker). However these tow process are independent and different with schedule, so sometimes we need to be accordingly flexible.

1. Update `~/chromiumos/src/third_party/hdctools/dockerfiles/servo_firmware_provision.py`

    Change string under specific channel and device you want to modify to new version.

2. For patch versification run:

    `build-servod`

    and then run servo_updater with locally built docker image:

    `servo_updater --updater_channel local -- -b [BOARD] -c [FW_CHANNEL]`

3. Prepare CL and send to review. Note that these changes will land in servod:latest in few hours after patch is merged and in serod:beta servod:release with release schedule (once a month). If you need these changes to land sooner please contact with current servod release owner to respin beta/release image.

    - [CL example](https://chromium-review.googlesource.com/c/chromiumos/third_party/hdctools/+/5824630)

## Testing FW in fleet

There is dedicated [pool](https://chromeos-swarming.appspot.com/botlist?c=id&d=asc&f=label-pool%3Aservo_verification&k=label-pool&s=id) of servos and labstations only for their testing - regression rack. You can find there ~20 different DUT boards connected to test compatibility of changes across as large sample as possible.

Labstations in that dedicated pool should automatically receive update to ToT every few days, therefore before mentioned above CLs land on production, they would be earlier available there. After making sure that these devices have new image with new servo FW available you can proceed with testing. `servo_LabstationVerification` tests are also automatically scheduled, so you can use these results. However here we are showing a way for self scheduling these tests to be more coherent.

Requirements:
- [get_servos_list](get_servos_list.md) script and its dependencies working
- [fleet_rollout](fleet_rollout.md) script and its dependencies working
- [crosfleet](https://g3doc.corp.google.com/company/teams/chrome/ops/chromeos/chromeos-infra/test_platform/internal/tools/crosfleet.md?cl=head#installation-and-updates) tool installed

Instructions:

- 1st run tests on current FW to spot potential flakiness
```
./get_servos_list.py --servo-type servo_v4p1 --stage tests
./schedule_tests.py --csv-file ./tests_servo_v4p1_list_debug.csv
```
You can see status and then results via: http://go/my-crosfleet

- 2nd roll out new FW on regression rack and repeat testing
```
./fleet_rollout.py --channel ALPHA --select from-csv --csv-file tests_servo_v4p1_list.csv

# make sure these servos received the update with, it should take less then 30min:
./fleet_rollout.py --monitor_fw_version servo_v4p1_v2.0.24152-0b36eb51a --select from-csv --csv-file tests_servo_v4p1_list.csv

./schedule_tests.py --csv-file ./tests_servo_v4p1_list_debug.csv
```

References: [labstations release](go/labstation_super_doc#labstation-release)

# Slow rollout

Once image is:
 - manually validated
 - available to different users under ALPHA channel
 - validated in-fleet (tested on regression rack)

we can begging rolling it out on fleet devices and in stages.

On every stage we monitor devices health looking for potential regressions.

Once 100% devices in fleet receive new FW and we do not see any regressions we can call FW new STABLE.

For detailed instructions see [roll out guide](servo_release_roll_out_guide.md).

# Monitoring

There is special dashboard created for health monitoring of:
- [servo_v4p1](https://dashboards.corp.google.com/_9bea027d_4408_4edc_b7f6_21c558608e5d)
- [servo_v4](https://dashboards.corp.google.com/_66bde26e_ee25_4b6c_94f9_b3522aa23663)
- [servo_micro](https://dashboards.corp.google.com/edit/_c4c4972e_1427_46a1_b2a2_611481f6a800)
- [c2d2](https://dashboards.corp.google.com/_346fde6b_8af2_47a6_bee3_63256cfb0cdb)

This dashboard provides head-to-head statistics of STABLE and ALPHA (or DEV) channels also with special view per board/model/fleet pool.
