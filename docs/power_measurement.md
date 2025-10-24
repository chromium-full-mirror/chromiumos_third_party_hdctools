# Chrome OS Power Measurement

This document details how developers can use hardware tools like Servo and
Sweetberry and software tools within [`dev-util/hdctools`][8] and other repos to
measure power on a Chrome OS device (DUT, device under test).

[TOC]

## Hardware to measure power

### Servo

Servo-like devices, including Servo V2, Servo V4, Micro Servo and Suzy-Qable,
can be used to measure power on the DUT with Analog-to-Digital Converters (ADCs)
on the board. For simplicity, this doc refers to them as just "Servo" devices.

See [Servo][5] for more information on Servo.

### Sweetberry

Sweetberry or Servo INA adapter can be used when there are no ADCs on
the DUT. Sweetberry is the preferred method. A hardware rework on the DUT is
often required to place sense resistors on the power rails and to attach 'Medusa
style' header (HIROSE DF13A-40DP-1.25V(55)) to the sense resistors and ground.

See [Sweetberry Configuration][6] for more information on Sweetberry.

## Bridging hardware and software

### Create configuration file

Servo and Sweetberry can measure power on the DUT, but they have no awareness of
what power rails are being measured, or what size the sense resistors are.
Therefore, a configuration file is necessary to provide information about the
hardware setup. This configuration file is usually manually created by an
engineer and is fed into the power measurement software tool later.

File format: `.py`

See [INA Configuration Files][1] for instructions on how to write the
configuration file.

There are some slight differences between configuration files for Servo and that
for Sweetberry. See [this example][2] for configuration for Servo.

There are two ways to write Sweetberry configuration files. See
[`servo_sweetberry_rails_addr.py`][3] and [`servo_sweetberry_rails_pins.py`][4].

## Generate configuration files for software tool

To test changes servod docker need to be build locally. To do that run:

```bash
(HOST) build-servod
```

Then you need run local docker image using -c flag:

```bash
(HOST) start-servod -c local [...]
```

To verify that you have generated configuration files successfully run servo container
in sleep mode and open its bash:

```bash
(HOST) start-servod -c local --sleep -n check
(HOST) docker exec -it check-docker_servod bash
(INSIDE DOCKER) ls ./usr/local/lib/python3.13/dist-packages/servo/data/
```

Note: adjust python version when necessary.

## Software tool to measure power

If introduced custom changes build servod and start-servod with the local build:

```bash
(HOST) $ build-servod

# For setup with on-board INA chip
(HOST) $ start-servod -c local -p $PORT_NUMBER --board $BOARD -- --config $CONFIG_FILE.xml

# For setup with sweetberry only
(HOST) $ start-servod -c local -p $PORT_NUMBER -- --config $CONFIG_FILE.xml
```

Note that `$CONFIG_FILE.xml` is generated in the previous step. Both `dut-power`
and `dut-control` are servod clients that talk to servod and fetch power data
from the Servo or Sweetberry.

You have to explicitly set $PORT_NUMBER to run servod-based tast test, such as
meta.PowerServodWrapper, which by defaults uses 9999.

### Unlock CCD

If the current-sensor data is to be read out from USB-C interface (CCD), the
GSC must be configured to forward the I2C current sensor bus to the SBU (USB)
interface. You can check whether this is already the case by running `ccd` in
GSC console:

```bash
>> ccd
	State: Locked
	Password: none
	Flags: 0x000000
	Capabilities: 0000000000000000
	UartGscRxAPTx   Y 0=Default (Always)
	UartGscTxAPRx   Y 0=Default (Always)
	UartGscRxECTx   Y 0=Default (Always)
	UartGscTxECRx   - 0=Default (IfOpened)
	FlashAP         - 0=Default (IfOpened)
	FlashEC         - 0=Default (IfOpened)
	OverrideWP      - 0=Default (IfOpened)
	RebootECAP      - 0=Default (IfOpened)
	GscFullConsole  - 0=Default (IfOpened)
	UnlockNoReboot  Y 0=Default (Always)
	UnlockNoShortPP Y 0=Default (Always)
	OpenNoTPMWipe   - 0=Default (IfOpened)
	OpenNoLongPP    - 0=Default (IfOpened)
	BatteryBypassPP Y 0=Default (Always)
	Unused          Y 0=Default (Always)
	I2C             - 0=Default (IfOpened)
	FlashRead       Y 0=Default (Always)
	OpenNoDevMode   Y 0=Default (Always)
	OpenFromUSB     Y 0=Default (Always)
	OverrideBatt    - 0=Default (IfOpened)
	APROCheckVC     - 0=Default (IfOpened)
```

`I2C` flag will be set to `(Always)` if this bus can be accessed via CCD.
`(IfOpened)` means the bus is inaccessible by default.

To unlock the I2C bus, run `ccd open` and follow the instructions printed on
the console. `ccd reset factory` will save these flags into GSC's non-volatile
memory, so that the unlocked state will be retained. You can revert back to
locked mode with `ccd reset` (usually required before device leaves the
factory).

### dut-power

Recommended, for users who only want measurements in power.

```bash
(HOST) $ dut-power -- [arguments]

# Example arguments for setup with sweetberry only
(HOST) $ dut-power -- --vbat-rate 0 -t 5
```

`dut-power` queries the selected servod to read power measurements from the
Servo or Sweetberry. See `dut-power -h` for setting arguments. `dut-power` works
with both Servo and Sweetberry. It packs configuring the ADCs, reading data,
calculating statistics, and saving to file into one command.

dut-power organizes results into a directory 'power_measurements' in a temp
directory (without TMPDIR in the env, this just defaults to '/tmp'). In there,
each board receives its own directory, and each measurement its own directory
within those. Measurements are labeled by their powerstate and timestamp.

The board name and powerstate are queried from the DUT's EC, though this might
fail, either due to EC communication issues, or because the user is using a
servo device that is not a dut controller e.g. sweetberry. In those cases, they
default to 'unknown' for board, and 'S?' for the powerstate.


Alternatively, they can be provided as command line arguments. If provided
through the command line, they overwrite the EC values (we do not attempt to
even read them)

```
dut-power --powerstate S0ix --board volteer -t 30 -w 10 -p 9998
```
This would read power wait for 10s before reading power for 30s through servod
running at port `9998` and store the result at
`/tmp/power_measurements/volteer/S0ix_20210210-162609/`


Lastly, the board name can also be provided through the environment variable
`BOARD`. To summarize the priorities of how the boardname is determined
(descending priorities)
1. command-line argument
2. querying `ec_board` through servod
3. using `BOARD` environment variable
4. using `'unknown'`

e.g.

```
/tmp/power_measurements/volteer/S0_20201116-162609/
/tmp/power_measurements/unknown/S?_20201116-163909/
```

### dut-control

For power users, provides more info than power.

`dut-control` can collect power measurements from both EC and on-board ADCs.

#### EC

`dut-control` can query battery power via EC’s connection (I2C) to the battery,
namely `ppvar_vbat`. On newer devices, same data averaged over 1 minute can be
queried by `avg_ppvar_vbat`.

#### On-board ADCs

`dut-control` can query power rails specified in the configuration file.

#### Types of information

`dut-control` can query power, bus voltage and current for all rails above, and
additionally shunt voltage for on-board ADCs.

#### Configure the ADCs

The on-board ADCs can be configured to more accurately measure power depending
on the size of the sense resistors and shunt voltage across the sense resistors.
Choose from the follow quick configs:

Config                    | Context
------------------------- | ---------------------------------------
`regular_power`           | S0 measurements
`regular_power_no_hw_avg` | S0 measurements w/out avg (for debug)
`low_power`               | < S0 measurements
`low_power_no_hw_avg`     | < S0 measurements w/out avg (for debug)

#### Examples

1.  Create helper variable, without `ppvar_vbat`.

```bash
(HOST) $ mv=$(dut-control -- bus_voltage_rails | cut -f 2 -d: | tr -d ',')
(HOST) $ ma=$(dut-control -- current_rails | cut -f 2 -d: | tr -d ',')
(HOST) $ mw=$(dut-control -- power_rails | cut -f 2 -d: | tr -d ',')
(HOST) $ cfg_reg=$(echo $mv | sed 's/_mv/_cfg_reg/g')
```

2.  Configure on-board ADCs (everytime after running `servod`).

```bash
(HOST) $ for cfg in $cfg_reg ; do dut-control -- $cfg:regular_power $cfg; done
```

    Or

```bash
(HOST) $ for cfg in $cfg_reg ; do dut-control -- $cfg:low_power $cfg; done
```

3.  Measure each power rail once.

```bash
(HOST) $ dut-control -- $mv
(HOST) $ dut-control -- $ma
(HOST) $ dut-control -- $mw
```

    And

```bash
(HOST) $ dut-control -- avg_ppvar_vbat_mw
(HOST) $ dut-control -- avg_ppvar_vbat_ma
(HOST) $ dut-control -- avg_ppvar_vbat_mw
```

    Or

```bash
(HOST) $ dut-control -- ppvar_vbat_mv
(HOST) $ dut-control -- ppvar_vbat_ma
(HOST) $ dut-control -- ppvar_vbat_mw
```

4.  Measure power for 1 second 30 times.

```bash
(HOST) $ dut-control -- -t 30 -z 1000 $mw | grep @@ | cut -b 6-
```

### powerlog

See [Sweetberry USB power monitoring][7].

[1]: ./ina.md
[2]: ../servo/data/nami_rev1_inas.py
[3]: ../servo/data/servo_sweetberry_rails_addr.py
[4]: ../servo/data/servo_sweetberry_rails_pins.py
[5]: ./servo.md
[6]: ./sweetberry.md
[7]: https://chromium.googlesource.com/chromiumos/platform/ec/+/HEAD/extra/usb_power/powerlog.README.md
[8]: https://chromium.googlesource.com/chromiumos/third_party/hdctools/+/HEAD
