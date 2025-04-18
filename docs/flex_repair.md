# Chrome OS Flex Repair

This document describes how Flex Repair is implemented in servo, and how to
control it.

# What is Flex?
ChromeOS Flex is an offering by ChromeOS that makes it possible to run ChromeOS
on devices that aren't chromebooks.

On servo, the Flex overlay is called "reven", following the same pattern as the
cros overlay. The reven overlay is a meta-board for all types of Flex devices.

The reven overlay is implemented so that servo doesn't require any hardware or
firmware interaction with the DUT (as that is not available on Flex devices).

So far, servo's use case for Flex fleet devices is so that they can go into
auto-repair. To do this, a relay switch driver was created, and devices in the
Flex fleet are required to have their power buttons be wired up to a relay
switch.

# Set up and Constraints
The reven board is only implemented for the servo v4p1, as only that servo has
the required number of USB ports required to control both the usb drive and the
relay switch separately.

The USB drive must be connected to the top port, and the relay switch must be
connected to the μSERVO port.

## How to run Servo on Flex
Fun fact! You don't actually need a Flex DUT to run servo with the reven
overlay. This is because there is no way for servod to detect if a Flex DUT is
connected to the board.

To run servo on flex, use one of the following commands:
```bash
(HOST) $ start-servod -b reven
(HOST) $ start-servod -b reven --mount /path/to/reven_config:/tmp -- -c /tmp/reven_config.xml
```

The purpose of `reven_config.xml` is to provide servo with any additional
parameters specific to reven.

`reven_config.xml` should be an xml file formatted in the following way:
```
<root>
  <include>
    <name>servo_reven_overlay.xml</name>
  </include>
  <control>
    <name>power_off_time</name>
    <doc>Amount of time to hold down power button to turn off the device.</doc>
    <params cmd="get" drv="echo" interface="servo" value="9" input_type="float"/>
  </control>
</root>
```

`value` may be changed from `9` to however long a power-button hold takes to
power off the device.

## dut-control options for flex
As Flex doesn't have an EC, a lot of commands that are available to other boards
are not available for Flex.
Here are some commands that are available for Flex:

### Controlling the power switch
```bash
(HOST) $ dut-control -- power_state:on
(HOST) $ dut-control -- power_state:off
(HOST) $ dut-control -- power_state:reset
```

### Controlling the usb mux direction
```bash
(HOST) $ dut-control -- image_usbkey_direction:dut_sees_usbkey
(HOST) $ dut-control -- image_usbkey_direction:servo_sees_usbkey
(HOST) $ dut-control -- second_usbkey_direction:dut_sees_usbkey
(HOST) $ dut-control -- second_usbkey_direction:servo_sees_usbkey
```
