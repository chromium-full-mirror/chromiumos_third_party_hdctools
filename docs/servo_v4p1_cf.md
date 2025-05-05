# Servo V4.1 Care & Feeding

Googlers: There's an [internal doc](https://docs.google.com/document/d/1jIOpmZ2RWCck5MeSzgk1IdifYJJmfIXdojFbq8gQZnw/edit) with a few more setup routines that we couldn't free (yet).

[TOC]

## Quick Start: basic use

Minimum configuration is:

1. USBIF Certified USB3 (type-C to C or type-A to C) cable from the host (e.g. Linux workstation) to ServoV4p1 ‘Host’ port.
2. (_Optional_) Connect a power supply to the ‘Servo Power’ Port if you plan to support high power servo loads. This is typically needed if the host port is 900mA only and you have multiple, high current devices attached directly to Servo’s USB A type ports.
3. Connect the power supply to the ‘DUT Power’ port
4. Connect ServoV4p1 “pigtail” (captive USB type-C) to the Chromebook/box (aka DUT == Device Under Test).
5. (_Optional_) Connect the video cable to the Mini DisplayPort connector if used.

## Current Status

Servod support for Servo v4.1 is mostly working!

* See: [CL:2155412](https://crrev.com/c/2155412) ([a20217d](https://chromium.googlesource.com/chromiumos/third_party/hdctools/+/a20217d81a2921dab7fde6226906f1e71dac3f54)).
* Follow [b/154436412](https://issuetracker.google.com/154436412)

## Required Reworks

* Case screw heads are T6 hex
* None yet for released models.

## Known Issues and Workarounds

Bugs are listed in buganizer, but here are some known issues and workarounds for significant issues:

### Alternate Servo Power port won’t negotiate above 5V (all versions)

Workaround: Limit power to host cable supply or supply dumb high voltage and manually toggle servo power input

## READ ME FIRST

### Update your firmware!

* Use “servo_updater” to get baseline version
* May also use FW from “[Known-good EC Firmware](#known-good-ec-firmware)” section.

Update to default firmware:
Update your CHROOT (!!!)
(chroot) $ update_chroot

Run servo to "default" fw
```bash
(HOST) $ servo_updater -- -b servo_v4p1
```

### Do I need to flash my EC?

It’s recommended to use the latest code available.

### How do I check my current firmware version?

Open the servo console (/dev/ttyUSB0):

```
    > version
    Chip:    stm stm32f07x
    Board:   0
    RO:      servo_v41_v2.0.3735+440cf71e0
    RW:      servo_v41_v2.0.3735+440cf71e0
    Build:   servo_v41_v2.0.3735+440cf71e0
            2020-04-01 10:21:17 sam@sam-XPS-8920
```
(example of ServoV4.1 EC Console as of 5-14-20)


## Known-good EC Firmware  {#known-good-ec-firmware}

Prebuilt images for the EC images are collected [here](https://drive.google.com/corp/drive/folders/1xbu57f8aFw2C-inW3c0w3q0OuMX2HkhI)


* Use [servo_v4p1_v2.0.7721-8af602eee[DVT-factory].bin](https://drive.google.com/file/d/1Y8ZQDhtmZT9Ldjt4I0FRtu405BQiDl7X/view) for DVT
    * jdabros@ (April 15, 2021)
    * Image is affected by rather annoying b/181930164
    * Until implement and upstream fix, particular order of plugging cables is recommended:
        * 1. Host connection
        * 2. (Optional) Servo Power
        * 3. DUT Power
        * 4. DUT
        * 5. (Optional) DisplayPort

Update to specific version:

```bash
(HOST) $ servo_updater -f <STM filename> -- -b servo_v4p1 -v --force
```

## Building the EC (chroot)

You don‘t need to do this unless you’re developing Servo v4.1 firmware.

Servo v4 code lives in the [EC](https://chromium.googlesource.com/chromiumos/platform/ec) and [hdctools](https://chromium.googlesource.com/chromiumos/third_party/hdctools) codebase(s). It can be built as follows:

1. Build the firmware

```bash
(chroot) $ cd ~/chromiumos/src/platform/ec/
(chroot) $ ~/chromiumos/src/platform/ec $ make BOARD=servo_v4p1 -j8
```

ec.bin appears in ~/chromiumos/src/platform/ec/build/servo_v4p1/ec.bin

2. Flash the firmware to the ServoV4.1

```bash
(HOST) $ servo_updater -f ~/chromiumos/src/platform/ec/build/servo_v4p1/ec.bin -- -b servo_v4p1 -v
```

3. **Profit!**


If you instead build in (~/chromiumos/src/third_party/hdctools) some (?) files will be here:


```bash
(chroot) $ cd ~/chromiumos/src/third_party/hdctools/servo_mfg/binfiles
```

### Flash custom-built firmware to ServoV4p1


```bash
(HOST) $ servo_updater -f ~/chromiumos/src/platform/ec/build/servo_v4p1/ec.bin -- -board servo_v4p1 -v --force
```

### CCD not working out-of-box

SnkDTS mode (CCD) is not enabled on ServoV4.1 in out-of-box firmware, unlike ServoV4.
You need to run `cc <snkdts|srcdts> <cc1|cc2>` in ServoV4.1 EC console to get it working.

```bash
(gLinux) $ sudo apt-get install minicom
(gLinux) $ sudo minicom -D /dev/ttyUSB<tab> (to see 0… 1..2)
(minicom) $ v<enter> (to see MCU name)
<Ctrl+A, let go, Z> (to see help) <Ctrl+A, let go, Q> (to quit)
	0 = (usually) ServoV4.1 STM32
	3 = (usually) DUT GSC
	4 = (usually) DUT AP
	5 = (usually) DUT EC

You can also use /dev/serial/by-id/. Example:
/dev/serial/by-id/usb-Google_Inc._Servo_V41_G2001070035-if00-port0
```

## Flashing the EC (STM32F072)

### Does my ServoV4.1 have blank firmware loaded?

* Connect [**HOST**] to a host.
* Check whether the **RED User LED** in uServo corner blinks and Servo is powered (Second Red LED lit near host port). A blinking User LED has firmware loaded.


### Updating from the host (servo_updater)

Note: [servod](servod.md) must not be running to update the firmware.

The latest firmware is available in the chroot at:

    ~/chromiumos/chroot/usr/share/servo_updater/firmware/servo_v4p1.stable.bin

As of 25-04-02: servo_v4p1.bin -> servo_v4p1_v2.0.24152-0b36eb51a.bin

And within docker image release:

```bash
(HOST) $ servo_updater --updater_channel [local|latest|beta|release] -- -b servo_v4p1 -p
```

To update run:

```bash
(HOST) $ servo_updater -f <STM filename> -- -b servo_v4p1 -v --force
```

### [EXPERTS ONLY] Updating from Raw (flash_ec)

* EVT boards and later support DFU mode without any rework.
* The Boot0/DFU switch near the host connector needs to switched <span style="text-decoration:underline;">before power up</span> into the position where the Blue LED will be lit in order to put the system in DFU mode.


```bash
(chroot) $ ./util/flash_ec --board=servo_v4p1 --image <filename>
```

## Power Configurations (Feed your Servo!)

The Servo is a self or bus powered hub, but too many peripherals can overload the Servo power supply. There are many configurations and peripherals, but the following table can be used to provide guidance for a starting point. Not all possible configurations are listed below; users may need to test their system, and specifics will vary...

Supported configurations below will be limited by the Servo power supply, whether from host USB cable or from the Servo Power connector; combinations listed are not software enforced inside the servo.  If your setup requires more power, the simplest option may be to attach a 3A supply to the ‘Servo Power’ port.

### Possible Configurations

With a USB2 connection to the host, available power (500mA/5V) restricts you to use either uServo or Ethernet, but not both. Likewise, you can either use one switchable USB port or the DisplayPort interface.

A USB3 connection to the host provides additional power (900mA/5V), so three devices can be powered sufficiently out of uServo, Ethernet and flash drives at the two switchable USB ports.
With USB C at this power rating you can also use the DisplayPort connection.

USB C or BC1.2 at 1.5A/5V provides even more options, with flash drives at both switchable USB ports, DisplayPort, uServo and Ethernet at the same time.

Higher powered USB C modes increase the power that can be supplied to the USB ports.

The DisplayPort connection can be either DP2 HBR2 with USB3 or DP4 HBR2.

### Command Cheatsheet

"Knight's Tour" Demo: Run from Servo EC console to test all features

```
<connect charger>
reboot
cc unplug
pd dump 3
usbc dp on		(Need miniDP-to-DP cable, hdmi adapter or "headless dongle")
usbc up 0
usbc prswap 01
cc pdsrc
usbc up 1
usbc prswap 11
usbc up 0
cc unplug
adc
cc replug cc2
pd 1 swap vconn
```

### TL;DR: USBC Commands

```
cc help
cc
       [off|on] or [unplug|replug] or (pd)(src|snk|drp)(dts) or [emca|nonemca]
       and/or [cc1|cc2]
on|off 			"Unplug servo @ DUT"
plug|unplug 		"Unplug servo @ Cable" (eMarked cable left in DUT)
(pd)(___)(dts)		Enable any mode in any PD-enabled state
emca|nonemca 	Fake an eMarker cable to DUT [only in non-DTS modes]
cc1|cc2		Set polarity or "active CC line"
gpioget
gpioset <gpio> [0 | 1 | IN]
adc				show ADC readings
reboot
cc_dac [1 | 2]   [mV in decimal | on | off]           "turn on CC DAC drive at a voltage"
pd 1 swap [power | vconn | data]
pd 1 [hard | soft]
```

### [TL;DR: DP commands](https://chromium-review.googlesource.com/c/chromiumos/platform/ec/+/2143936)

```
usbc dp help
usbc dp [on|off] [enable|disable]
usbc dp pins [C|D|CD]
usbc dp mf [0|1]
usbc_action dp plug [0|1]
usbc prswap [00|01|10|11]	Allow [10] SRC2SNK or [01] SNK2SRC power role swaps
usbc fastboot [0|1]		Route Host to DUT wen ServoV4 is DFP [ServoA disabled]

"5v|12v|20v|dev|pol0|pol1|drp|dp|chg x(x=voltage)|"
"drswap [1|0]|prswap [10|01|11|00]|up [0|1]|fastboot [0|1]",

```

### Miscellaneous commands

```
cc pdsnk [cc1|cc2]
If ServoV4p1 has no power, disables debug for Sink mode
 DTS = AUX used for CCD = Will give warning if you try to EnterMode
pd 1 hard
to hard_reset DUT + apply changes since last connect
i2cxfer r 1 0x12 0x12
0x44 [68]
Show how many lane is negotiated (snooped from DPCD)
Bit [4:0] is the lane count. So the above example is "4-lane"

```

## CC DAC Circuitry

This section describes how to drive specific analog voltages on the DUT CC interface.

Each DUT channel includes a precision, high drive buffer that can force specific voltages onto either DUT CC1 or CC2 line.  This may be helpful to override any unexpected pull up/down configurations to force ICs sensing the CC lines into a better state.

When unused, the DACs go high impedance, and they disconnect via mux from the normal CC traffic.

| Parameter | Condition | Min | Typ | Max |
| --------- | --------- | --- | --- | --- |
| Output Accuracy | Ivbus = 0, Icc1, Icc2 = 0<br> 0V&lt;= CC DAC &lt;= PP3300 | | ±3mV | ±12mV |
| Output Minimum | Ivbus = 0, Icc1, Icc2 = 0<br> 0V&lt;= CC DAC &lt;= PP3300 | | 3mV | 10mV |
| Output Maximum (with accuracy) | Ivbus = 0, Icc1, Icc2 = 0<br> 0V&lt;= CC DAC &lt;= PP3300<br> PP3300= 3.300V | 3.300| | ~3.35 |
| Output Maximum (no accuracy guarantee) | | | 3.7 | 3.8 |
| Current Limiting | 0V&lt;= CC DAC &lt;= 5.25 V | ±150mA? | ±300mA | |
| Slew Rate | | | 1.2V/usec | |
| Output Impedance | Includes captive cable | | 0.9 Ohms | ~2.0 ohms |

The outputs are current limited, protected from over current or shorts, and also thermally protected.  In any fault case, the affected channel will disconnect itself from the CC net.  Faults will generate an interrupt with a warning.

Here are helpful commands:

```
cc_dac on <1|2>
cc_dac [1 | 2] [on |off]                          “ turn on/off a single channel”
cc_dac [1 | 2] [mV in decimal | on | off ]        “Set CC DAC drive at a voltage”
```

Turning on a channel clears any fault

If the user wishes to access the DACs directly, it may be simpler to use console access through the ttyUSB0 path

```
i2cxfer w16 1 0x48 0x8 0x0080
```
This writes out a 2.5V (mid scale, 0x8000) to CC_DAC1 (0x49 address for DAC2); note that byte order is swapped in 16 bit value.  DAC should already be enabled for `cc_dac 1 on`

## Programming the Atmel ATMEGA32U4 {#programming-the-atmel-atmega32u4}

This is rare; the factory should have programmed this.  You can verify whether this has happened by connecting the Servo v4.1 to the DUT and from the DUT prompt, type `lsusb`.

When blank, the Atmel device is listed this way from `lsusb`

```
Bus xxx Device yyy: ID 03eb:2ff4 Atmel Corp. atmega32u4 DFU bootloader
```

When programmed correctly, here is the intended listing from `lsusb`

```
Bus xxx Device yyy: ID 03eb:2042 Atmel Corp. LUFA Keyboard Demo Application
```

If you cannot detect the Atmel device from the DUT, it is likely held in reset.  To correct this, do a read - modify - write with this data byte (0bxxxx xx1x) to the onboard register in the GPIO expander (TI TCA6416). This is done by these commands from the host console window:

```
>i2cxfer r 1 0x21 0
0xac [174]
>i2cxfer w 1 0x21 2 0xae
```

Note that data byte is changed from 0xac to 0xae.  Side note - the expander read port is 0, and the associated write port is 2.

The Atmega32u4 device has the same functionality as was used on Servo v4, so the same hex image will be shared between versions.

1. Before programming this device it is necessary to install dfu-programmer on the host computer you must install the dfu-programmer tool first. Inside chroot this can be done with `# sudo emerge dfu-programmer`.
2. Navigate to the directory where dfu-programmer file is located
    1. Something like `~/chromiumos/chroot/usr/bin` outside the chroot
    2. `~/chromiumos/chroot/usr/bin` inside the chroot
3. Attach both DUT and host ports on the servo to the host computer USB ports. Crouton can also be used as a programmer when attached to the DUT USB-C cable.
4. If the Atmel part is not blank, erase the Atmega32u4  (possibly w/o the `--force`): `# sudo ./dfu-programmer atmega32u4 erase --force`
5. Program the blank device.  The Keyboard.hex file & location are from a standard chromium installation.  The format is `# sudo ./dfu-programmer <device> flash <image>`

A specific example outside the chroot: `# sudo ./dfu-programmer atmega32u4 flash ~/chromiumos/src/third_party/hdctools/servo_mfg/binfiles/Keyboard.hex`

And from within the chroot: `# sudo ./dfu-programmer atmega32u4 flash ~/chromiumos/src/third_party/hdctools/servo_mfg/binfiles/Keyboard.hex`

Note: the Atmega32u4 can also be programmed using the script found inside the chroot at src/third_party/hdctools/servo_mfg/mfg_servo_v4.py.

## Testing DisplayPort

Need some changes to enable DP alternative mode. One can download the prebuilt Image from [here](https://drive.google.com/corp/drive/folders/1xbu57f8aFw2C-inW3c0w3q0OuMX2HkhI) (the one with filename “dp_enabled”) or use the ToT build from 05/20/20.

The image is configured to disable DTS-mode (CCD) and enable DP alt-mode.

You can also disable this by typing `cc [pdsnk|src|drp] cc1`

Better to plug some >5V power adapter to the servo v4.1 “DUT POWER” port; otherwise, the PD communication is by default disabled.

The supported pin assignments are C and D. The multi-function preference is default disabled. So after negotiating with DUT, the C assignment (4-lane DP) is expected to be selected.

The HPD pass-through is implemented. When hot-plugging the DP cable from the DP port, the DUT is able to notice the HPD change. Some console messages will be shown, like:

```
> [1215.242295 HPD: 0]
[1216.836650 HPD: 1]
[1216.837022 HPD IRQ]
```

Console commands to change the DP config

```
> usbc dp enable
DP alt-mode: enable

> usbc dp help
Usage: usbc_action dp [enable|disable|pins|mf_pref|plug]

> usbc dp pins
Pins: CD

> usbc dp mf    # default is 4-lane DP (MF-pref is disabled)
MF pref: 0
```

Select 2-lane DP (and 2-lane USB SS), by enabling MF-pref:

```
> usbc dp mf 1
MF pref: 1
```

Need to reattach the Type-C cable from DUT to make the config active (renegotiate a PD contract). Or use the command to emulate the reattachment:

```
> cc off       # detach
…

> cc src       # attach, a message will show PinCfg:D is selected
…

[175.940532 PinCfg:D]
```


Flip the CC direction electrically

```
> cc src cc2
```
or

```
> cc src cc1   # which is default
```

Show how many lanes are negotiated (snooped from DPCD):

```
> i2cxfer r 1 0x12 0x12

0x44 [68]
```

Bit [4:0] is the lane count. So the above example is “4-lane”.


## Debugging with the STM SWD Interface

The STM can be used with a variety of ARM debuggers using connector J8 SW CLK/DIO port.  Note that most debuggers have 0.1” headers and the servo V4.1 has a 0.05” header for J8.

Here are some ways to connect to various debuggers:

ST ST-Link/V2 or ST-Link/V2 (2x10 0.1” header):

* Attach bundled 20 position 0.05” IDC ribbon cable to [Adafruit JTAG to SWD Adapter](https://www.adafruit.com/product/2094)
* Attach Adapter to 10 position 0.025” IDC ribbon cable to J8 on Servo v4.1
    * Samtec FFSD-05-D-04.50-01-N-R is one example 0.025” pitch IDC cable


Software setup: I've been able to use ST's standard tools in Windows to detect and flash the EC, but I've not been able to get ST's Linux tools to install properly to attempt flashing.

For the Windows ST tools, it is required to enable in the submenu to detect in hot plug mode for the SWD interface.


### Others options

Sam has successfully used the Segger JLink Pro with some Segger Linux tools.

## RS232 Serial Console Port

The 6P6C (RJ25) receptacle on Servo v4.1 is an RS232 serial port.  With the standard firmware it provides console access, even when Host-facing USB may not be working.

### Terminal settings (for use with standard firmware)

* 115200 baud 8N1
* Hardware Flow Control: No
* Software Flow Control: N/A

### Pinout

The receptacle is logically a 6P4C (RJ14) as only the middle 4 pins are used, so either 6P6C or 6P4C cable may be used.

The pinout matches the middle pins of Cisco router 8P8C (RJ45) console ports.  Connect to it in the same manner, except instead of 8P8C, use either 6P6C or 6P4C.

Servo v4.1 RS232 6P6C receptacle pinout reference:

```
1 | NC
2 | TXD
3 | GND
4 | GND
5 | RXD
6 | NC
```

Or pretending it's a 6P4C receptacle (for easier reference if crimping a 6P4C plug):

```
1 | TXD
2 | GND
3 | GND
4 | RXD
```

### Example hardware for connecting to the port

**IMPORTANT:** This is ***not*** an endorsement of any specific vendors or products!  Each example product linked here has been successfully used as part of a desk setup providing Servo v4.1 serial console access, but none has gone through any kind of thorough or large-scale qualification testing for this use.  Additionally, there may be hardware revisions of these products which have not been tested at all for this use.  Use of these products is at your own risk, this document makes no promises or guarantees about them.

1. USB plug to DB9 plug RS232 Serial adapter (or built-in RS232 port on your host if available)
   * Example: Tripp Lite `USA-19HS` [Keyspan USB to Serial Adapter - USB-A Male to DB9 RS232 Male, 3 ft. (0.91 m), TAA](https://www.tripplite.com/keyspan-high-speed-usb-to-serial-adapter~USA19HS)
   * Example: Gearmo `GM-FTDI4X-M` [4 Port Serial RS-232 Hub w/ FTDI Chipset & RX/TX LED Indicators](https://www.gearmo.com/shop/gearmo-usb-4-port-serial-rs232-featuring-ftdi-chipset-with-rx-tx-led-indicators-industrial-version/)
2. DB9 receptacle to 8P8C (RJ45) receptacle "Straight Through" or "Cisco Terminal" pinout adapter
   * Example: Tripp Lite `B090-A9F` [Modular Serial Adapter Straight-Through Wiring (DB9 F to RJ45 F)](https://www.tripplite.com/modular-serial-adapter-straight-through-wiring-db9-female-rj45-female~B090A9F)
   * Example: CablesAndKits.com `CAB-9AS-FDTE` (generic Cisco `74-0495-01`) [Cisco DB9 Female to RJ45 Female Console Adapter](https://www.cablesandkits.com/accessories/cable-adapters/cab-9as-fdte-/pro-614/)
3. 6P6C or 6P4C rollover cable (or crimp your own)
   * Example: Monoprice `939` [Phone Cable, RJ12 (6P6C), Reverse for Voice - 7ft](https://www.monoprice.com/product?p_id=939)

It may be possible to crimp a 6P6C plug onto the end of a USB&lt;->8P8C (RJ45) Cisco-compatible cable, of which there are many on the market.  However the width of the typically flat cable jacket intended for serial connections might be awkward to deal with in the narrower 6P6C plug and the author has not attempted this.

With sufficient tools and expertise, you could build your own USB&lt;->6P6C/6P4C adapter cable using actual 6-wire or 4-wire cable into a 6P6C / 6P4C plug, if so desired.

## References

[ServoV4 Overview](servo_v4.md): Good resource for reviewing previous bringup
