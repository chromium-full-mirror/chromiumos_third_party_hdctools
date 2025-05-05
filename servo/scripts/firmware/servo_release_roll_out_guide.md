# HW tools roll-out guide


Make sure you prepared the environment:
- gcert
- f1-sql working
- shivas installed and logged in

We are going to use 2 internal tools, for their details you can read following docs:
- [get_servos_list](get_servos_list.md) - defines stages (what DUTs we are going to update) and gives you ready to use list
- [fleet_rollout](fleet_rollout.md) - wrapper around shivas tool, which allow us to actually update devices in fleet

Go to directory `~/chromiumos/src/third_party/hdctools/servo/scripts/firmware`.

**Important, remember to:**
 - keep generated files alive until the end of release,
 - adjust servo_type, channel and file names in commands below for specific to release process (for servo_micro or c2d2 you should also use stages like first-ocd, second-ocd)

**For 1st stage run:**
```
./get_servos_list.py --servo-type servo_v4p1 --stage first
./fleet_rollout.py --servo-type servo_v4p1 --channel ALPHA --select from-csv --csv-file first_servo_v4p1_list.csv
```

You can expect some per hostname errors from shivas. Sometimes database from which we are taking duts list is not yet synced with real state so then when we try to modify/read these duts with shivas we see errors as these devices are no longer available. Just ignore it unless the scale is significant (more then few percents of the list).

This commands change servo FW channel in UFS but then repair job is responsible to actually update servos. This command also schedules repair job. It runs in closest possible time - so instantly when DUT is idle or just after current test/job on DUT finishes. Sometimes tests are super long and due to lab workflow, scheduled repair time outs as resources are not available for too long in such cases. Therefore there is need to monitor and reschedule repair, usually once or twice in 24h after roll-out.

**Monitor rollout:**
```
./fleet_rollout.py --servo-type servo_v4p1 --monitor_fw_version servo_v4p1_v2.0.24152-0b36eb51a --select from-csv --csv-file first_servo_v4p1_list.csv
```
**Reschedule repairs:**
```
./fleet_rollout.py --servo-type servo_v4p1 --repair_if_not_updated servo_v4p1_v2.0.24152-0b36eb51a --select from-csv --csv-file first_servo_v4p1_list.csv
```

Some devices may seem to be not updated even after few repair reschedules, it may be worth investigating, but in most cases these are just broken setups that needs manual repairs. This can be also ignored when we are seeing small number of such problems.

After all devices receive new FW, monitor devices health using specific dashboard. **If any problem spotted you can roll back FW with command as below:**
```
./fleet_rollout.py --servo-type servo_v4p1 --repair_if_not_updated servo_v4p1_v2.0.24152-0b36eb51a --select from-csv --csv-file first_servo_v4p1_list.csv
```

**To roll back all devices with ALPHA channel back to STABLE use:**
```
./get_servos_list.py --servo-type servo_v4p1 --stage all-alpha
./fleet_rollout.py --servo-type servo_v4p1 --channel STABLE --select from-csv --csv-file all-alpha_servo_v4p1_list.csv
```

**Then after ~week of monitoring ALPHA devices in field proceed with 2nd stage of roll-out:**
```
./get_servos_list.py --servo-type servo_v4p1 --stage second
./fleet_rollout.py --servo-type servo_v4p1 --channel ALPHA --select from-csv --csv-file second_servo_v4p1_list.csv
```

**Then after another ~week of monitoring and proceed with updating all devices in fleet:**
```
./get_servos_list.py --servo-type servo_v4p1 --stage all-stable
./fleet_rollout.py --servo-type servo_v4p1 --channel ALPHA --select from-csv --csv-file all-stable_servo_v4p1_list.csv
```

After all stages or potential rollback always remember about monitoring/rescheduling with `--repair_if_not_updated` / `--monitor_fw_version` flags.


**In the end we can change STABLE to clean up process:**
- 1st create and land proper CLs
    - modify FW under STABLE channel to new one
    - leave FW under ALPHA without changes (need to be the same as new stable)
- When above CL lands on labstation in closest labstation release cycle
    - revert the devices FW channel in UFS back to STABLE from ALPHA:

```
./get_servos_list.py --servo-type servo_v4p1 --stage all-alpha
./fleet_rollout.py --servo-type servo_v4p1 --channel STABLE --change_channels_only --select from-csv --csv-file all-alpha_servo_v4p1_list.csv
```


Note: this change should not lead to any actual action, as devices would already have proper FW installed, just logical clean-up in UFS.
