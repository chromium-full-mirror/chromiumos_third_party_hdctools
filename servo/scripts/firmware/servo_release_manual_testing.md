# Manual testing

Below you can find general guidelines on how to conduct tests. Note that these are minimum and not fully detailedrequirements. Tester can expand tests scope. Especially if releasing FW contains specific set of higher risk changes tester should add more specific test cases. Tester should look for any unexpected behaviors during testing.


# Servo_v4pX
**Important notes:**
 * Save all logs possible into one document, paste it into bug crate to track testing, note things like: used servo serialname, DUT&ChromeOS version. See examples in [this issue](https://b.corp.google.com/issues/362748132/dependencies) and its child issues.
 * In case of any problems/bugs spotted, 1st make sure this is new regression, so rollback FW and redo test. In case of new regression you need to stop further work until issue resolved or decided differently.
 * Look for any unexpected errors eg. during enumeration, during normal work (`dmesg -w` command on host and DUT), in servod logs, etc. Also these not critical.

---
**Servo itself tests:**

Requirements:
* Use 2 different servo units. Best to use different production batches we have.

Steps:
* update device to expected new FW, look for success logs (and blinking red light on servo_v4p1)
* test rollback possibility
* verify device enumerates properly in host system
* test you are able to reliably use servo console under  `/dev/ttyUSB0`, try at least `serial` and `version` commands
* test you are able to start servod and verify if that command reports expected output `dut-control serialname`


---

**Device compatibility tests:**

Requirements:
* Use minimum 3 different platforms. Best if they differ significantly - uses ARM/Intel/AMD, or CR50/Ti50, etc.
* To servo connect: charger, ethernet cable, 2 (1 for v4) USB memory sticks

Steps:
* connect pigtail cable to DUT (retry with other cable orientation)
    * verify if GSC device is enumerated on host system, consoles are properly attached
    * verify if all servo usb devices are properly enumerated on DUT system (check dmesg, this includes servo, usb ports, eth device, keyboard simulator)
* test you are able to reliably use consoles via CCD, under /dev/ttyUSBX
* test you are able to start servod with -b flag and verify if that command reports expected output `dut-control serialname
* test USB ports and muxing, take usbstick and mux it between DUT and host, example commands to use:

    servo_v4p1:

    ```
    dut-control -- top_usb_mux_sel:servo_sees_usbkey bottom_usb_mux_sel:servo_sees_usbkey; sleep 10; dut-control -- bottom_usb_mux_sel:dut_sees_usbkey top_usb_mux_sel:dut_sees_usbkey
    ```

    servo_v4:

    ```
    dut-control -- usb3_mux_sel:servo_sees_usbkey; sleep 10; dut-control -- usb3_mux_sel:dut_sees_usbkey
    ```
* test we are able to charge device through charged connected to servo (also green light on servo should turn on). Best if you can try different chargers.
* test internet connection provided via servo Ethernet. Eg. in DUT console run: `ping google.com`
* change servo pd role to SNK and retry all tests


# Servo_micro & c2d2

TODO(guidelines for manual testing of these devices)
