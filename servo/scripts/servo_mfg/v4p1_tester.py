# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Base programmer outlining the interface to program."""

from servo_mfg import control_test
from servo_mfg import tester
from servo_mfg import usb_device_test

# Import this for the right vid/pid information.
from servo_mfg.v4p1_manufacturer import V4P1Manufacturer


class V4P1Tester(tester.Tester):
    """Class to handle one manufacturing round for one device type."""

    PHASE = 1

    def _gen_ina_tests(self, name_param, i2c_addr, sch_hint=None):
        # Helper to format INA tests.
        regex = r"\d+\.\d+"
        # Note: careful when editing this. The controls line up with the
        # error messages below.
        ctrls = ["%s_%s" % (name_param, v) for v in ["mv", "ma", "mw"]]
        testnames = ctrls
        if sch_hint:
            testnames = ["%s %s" % (ctrl, sch_hint) for ctrl in ctrls]
        ina_base_msg = (
            "INA (0x%02x) failed to read %s. INA might be broken, "
            "unstuffed or i2c communication might be failing."
        )
        debug_lines = [
            ina_base_msg % (i2c_addr, v) for v in ["bus voltage", "current", "power"]
        ]
        for name, ctrl, debug_line in zip(testnames, ctrls, debug_lines):
            test = control_test.ControlTest(name=name, regex=regex, ctrl=ctrl)
            test.base_debug_line = debug_line
            self._register_test(test)

    def _register(self):
        # This is broken out to allow for clean readability and maintainability
        # Check the serialnumber to validate communication to the MCU works.
        test = control_test.ControlTest(name="serialname", regex=".+")
        # Indicate test is to check basic communication.
        test.base_debug_line = "Basic communication with servo EC failed."
        self._register_test(test)

        # Check the role to make sure that the cc readings work internally, at
        # least at surface level.
        test = control_test.ControlTest(name="servo_pd_role", regex="(src|snk)")
        # Indicate test is to check cc values.
        test.base_debug_line = "Querying cc values by the servo EC failed."
        self._register_test(test)

        # Check this usb mux control to make sure that i2c communication
        # to the gpioexpander works at least from a read perspective.
        # TODO(b/169900864): expand to test all communications on the gpio
        # expander(s).
        test = control_test.ControlTest(name="aux_usbkey_pwr", regex="(on|off)")
        # Indicate test is to check cc values.
        test.base_debug_line = "Communication with GPIO expander 0x%02x failed." % 0x42
        self._register_test(test)
        # Check all INAs to make sure they can be communicated with.
        self._gen_ina_tests("ppdut5", 0x80, "INA231 [U7]")
        self._gen_ina_tests("ppchg5", 0x82, "INA231 [U23]")
        self._gen_ina_tests("ppservo5", 0x84, "INA231 [U51]")

        # Base prompt for all these usb tests.
        base_prompt = "Plug a USB stick into the"

        # Add USB hub testing for the two usb3 ports, and the uservo port.
        name = "image USB-A port (J2.0)"
        usb_test = usb_device_test.UsbDeviceTest(
            name=name,
            prompt="%s %s" % (base_prompt, name),
            port_number=2,
            hub_vid=V4P1Manufacturer.HH_VID,
            hub_pid=V4P1Manufacturer.HH_PID,
            hub_pid3=V4P1Manufacturer.HH_PID3,
            pwr_ctrl="image_usbkey_pwr",
            mux_ctrl="image_usbkey_mux",
            mux_val="servo_sees_usbkey",
        )
        self._register_test(usb_test)
        # No prompt on the second one, as it's essentially the same test again.
        usb_test2 = usb_device_test.UsbDeviceTest(
            name=name,
            port_number=2,
            hub_vid=V4P1Manufacturer.DH_VID,
            hub_pid=V4P1Manufacturer.DH_PID,
            hub_pid3=V4P1Manufacturer.DH_PID3,
            pwr_ctrl="image_usbkey_pwr",
            mux_ctrl="image_usbkey_mux",
            mux_val="dut_sees_usbkey",
        )
        self._register_test(usb_test2)
        name = "aux USB-A port (J2.1)"
        usb_test3 = usb_device_test.UsbDeviceTest(
            name=name,
            prompt="%s %s" % (base_prompt, name),
            port_number=1,
            hub_vid=V4P1Manufacturer.HH_VID,
            hub_pid=V4P1Manufacturer.HH_PID,
            hub_pid3=V4P1Manufacturer.HH_PID3,
            pwr_ctrl="aux_usbkey_pwr",
            mux_ctrl="aux_usbkey_mux",
            mux_val="servo_sees_usbkey",
        )
        self._register_test(usb_test3)
        # No prompt on the second one, as it's essentially the same test again.
        usb_test4 = usb_device_test.UsbDeviceTest(
            name=name,
            port_number=3,
            hub_vid=V4P1Manufacturer.DH_VID,
            hub_pid=V4P1Manufacturer.DH_PID,
            hub_pid3=V4P1Manufacturer.DH_PID3,
            pwr_ctrl="aux_usbkey_pwr",
            mux_ctrl="aux_usbkey_mux",
            mux_val="dut_sees_usbkey",
        )
        self._register_test(usb_test4)
        name = "uservo USB-A port (J4)"
        usb_test5 = usb_device_test.UsbDeviceTest(
            name=name,
            prompt="%s %s" % (base_prompt, name),
            port_number=4,
            hub_vid=V4P1Manufacturer.HH_VID,
            # no pid3 as this port is not USB3
            # capable.
            hub_pid=V4P1Manufacturer.HH_PID,
            pwr_ctrl="uservo_pwr_en",
        )
        self._register_test(usb_test5)
