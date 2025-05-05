# Servo

[TOC]

## Introduction

Servo is a debug board used for ChromiumOS test and development. Depending on
the version of Servo, it can connect to a debug header or USB port on the Chrome
OS device. The debug header is used primarily during development and is often
removed before a device is released to consumers.

Servo is a key enabler for automated testing, including
[automated firmware testing][FAFT]. It provides:

*   Software access to device GPIOs, through `hdctools`
*   Access to EC and CPU UART ports, for convenient debugging
*   Reflashing of EC and system firmware, for easy recovery of bricked systems

For example, it can act as a USB host to simulate connection and removal of
external USB devices. It also provides JTAG/SWD support.

Though Servo boards are not publicly distributed or sold (by Google), schematics
and layout for each version is available.

## Hardware Versions

### Servo v2

See the detailed documentation in [Servo v2].

### Servo Micro

Servo Micro is a self-contained replacement for Yoshi Servo flex. It is meant to
be compatible with Servo v2 via `servod`. The design uses case closed debug
software on an STM32 MCU to provide a [CCD] interface into systems with a Yoshi
debug port.

Servo Micro is usually paired with a Servo v4 Type-A, which provides ethernet,
dut hub, and muxed usb storage.

See the detailed documentation in [Servo Micro].

### Servo v4

While Servo v4 is still supported in software, the hardware has been discontinued
and replaced by Servo v4.1.

See the detailed documentation in [Servo v4].

### Servo v4.1

Servo v4.1 is the latest test and debug board to work with Google hardware. It
combines Case Closed Debug ([CCD]) with numerous different methods to download
data to the DUT and other testing and debug functionality.

Servo v4.1 is a superset of Servo v4 for functionality.

See the detailed documentation in [Servo v4.1].

## Using Servo {#using-servo}

To use Servo, on your Linux workstation you need to
[build ChromiumOS][developer_guide] and create a chroot environment.

The `hdctools` (Chrome OS Hardware Debug & Control Tools) package contains
several tools needed to work with servo. The Docker image will check for
updates each day.

On your workstation, servod must also be running to communicate with servo:

```bash
(HOST) $ start-servod -b $BOARD
```

With `servod` running, `dut-control` commands can be used to probe and change
various controls. For a list of commands, run:

```bash
(HOST) $ dut-control -- all_controls
```

You can toggle GPIOs by specifying the control and the state.

Perform a DUT cold reset:

```bash
(HOST) $ dut-control -- cold_reset:on
(HOST) $ sleep 1
(HOST) $ dut-control -- cold_reset:off
```

Power-cycle a DUT:

```bash
(HOST) $ dut-control -- power_state:off
(HOST) $ dut-control -- power_state:on
```

Higher-level controls may set several sub-controls in sequence.

For example, to transition a DUT to recovery mode:

```bash
(HOST) $ dut-control -- power_state:rec
```

To read the value of a `dut-control` property, just specify the name of the
property:

```bash
(HOST) $ dut-control -- <name_of_property>
```

For example, to access the CPU or EC UARTs, first check the port mapping with
`dut-control`, then attach a terminal emulator program to the port:

```bash
(HOST) $ dut-control -- cpu_uart_pty
(HOST) $ dut-control -- ec_uart_pty
(HOST) $ sudo minicom -D /dev/pts/$PORT
```

To see all the available `dut-control` commands, you can do:

```bash
(HOST) $ dut-control -- --info
```

Servo can also be used for flashing firmware. For details look into this
[page](https://chromium.googlesource.com/chromiumos/third_party/hdctools/+/HEAD/docs/servod_outside_chroot.md#i-want-to-flash-firmware-how-do-i-do-that).

To read FW you can try following command:
```bash
(HOST) $ docker exec -it your_servod_name-docker_servod futility read --servo -v "$OUTFILE"
(HOST) $ docker exec -it your_servod_name-docker_servod cat "$OUTFILE" > "$OUTFILE"
```

To set up servo to run automated tests, connect the servo board and the test
device to the network via Ethernet, and load a ChromiumOS image onto USB memory
stick. The networking and build image steps are not described here; see [FAFT]
for details on configuring servo to run automated tests. For information on
writing tests, see the [servo library code] in the [ChromiumOS autotest repo].

## Using multiple servos on the same machine

It's possible to connect multiple servos at once, which is especially useful for
testing/developing against multiple devices. Servo v4 will charge the DUT if a
charger is attached to it and also provides an ethernet jack so SSH is always
available.

To use multiple servos, you need to run multiple instances of `servod`, each
running on a different port. You also need to specify the servo's serial name.

To find the serialname of connected servos you can look into `lsusb``.

### Example

Multiple servod instances can be launched by specifying serial names:

```bash
# servo v4
(HOST) $ start-servod -b nocturne -s C1804020116 -n my_servod

# servo micro
(HOST) $ start-servod -b hatch -s CMO653-00166-040489J03624 -n my_servod
```

Each servod container has unique name, given automatically or by user.
`-n my_servod` is used to identify specific containers if multiple are running.

```
To stop this container: $ stop-servod --container_name my_servod
```

To interact with that container:
```bash
(HOST) $ dut-control -n my_servod -- power_state:off
```

### servodrc

An even simpler way to deal with multiple servos is to use a `.servodrc` file.
This file lets you map arbitrary symbolic names to servo serial numbers, so you
don't have to remember the port when running `dut-control`.

For complete details on the format see [Servo Parsing].

#### Example

**`~/.servodrc`**:

```
# servo-name, serial-number, port-number (legacy, ignored), board-name (optional), board-model (optional)

kohaku, C1706311077, , hatch
dragonclaw, CMO653-00166-040489J03624
nocturne, C1804020116, , nocturne
```

<!-- mdformat off(b/139308852) -->
***note
**NOTE**: Even though `board-name` is optional, you probably want to specify it
if you know it. Otherwise some controls (e.g., `power_state`) will not work.
***
<!-- mdformat on -->

With the above `.servodrc`, you can now simply start `servod` instances by
symbolic name as as follows:

```bash
(HOST) $ start-servod -n kohaku
```

```bash
(HOST) $ dut-control -n kohaku fw_wp_state
```

[FAFT]: https://www.chromium.org/for-testers/faft
[FAFT setup image]: https://www.chromium.org/for-testers/faft/Servo2_with_labels.jpg
[developer_guide]: https://chromium.googlesource.com/chromiumos/docs/+/HEAD/developer_guide.md
[servo library code]: https://chromium.googlesource.com/chromiumos/third_party/autotest/+/HEAD/server/cros/servo/
[ChromiumOS autotest repo]: https://chromium.googlesource.com/chromiumos/third_party/autotest
[Servo v2]: ./servo_v2.md
[Servo v4]: ./servo_v4.md
[Servo v4.1]: ./servo_v4p1.md
[Servo Micro]: ./servo_micro.md
[servod_no_nspid]: https://groups.google.com/a/google.com/d/msg/chromeos-chatty-firmware/mDexO8T1TyM/rFONCSifAAAJ
[CCD]: https://chromium.googlesource.com/chromiumos/platform/ec/+/cr50_stab/docs/case_closed_debugging_cr50.md
[Servo Parsing]: ./servod.md#servo-parsing
