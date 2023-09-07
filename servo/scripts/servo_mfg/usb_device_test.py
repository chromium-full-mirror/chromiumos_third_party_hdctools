# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Test to check usb device/port enumeration and power cycling."""

import os
import time

from servo_mfg import device_util
from servo_mfg import test
from servo_mfg import user_input


# Delay to wait for a mux value change to take effect.
MUX_DELAY_S = 0.01

# The default timeout to wait for the device to show up if it supports
# power cycling.
POWER_DELAY_S = 5.0

# If the device should already be enumerated, don't wait that long.
NON_POWER_DELAY_S = 1.0


class UsbDeviceTestError(test.TestError):
    """UsbDeviceTest error class."""


class UsbDeviceTest(test.Test):
    """Class to test a usb device enumerating on the servo device."""

    DETECTION_FAILURE = "detect"

    MUX_FAILURE = "mux"

    POWER_CYCLE_FAILURE = "pwr"

    def __init__(
        self,
        name,
        port_number,
        hub_vid,
        hub_pid,
        hub_pid3=None,
        pwr_ctrl=None,
        mux_ctrl=None,
        mux_val=None,
        prompt=None,
    ):
        """Initialize the test.

        Args:
          name: name for the test
          port_number: the usb port-path number that the device appears on
          hub_vid: the vid of the usb hub the device appears on
          hub_pid: the pid of the usb hub the device appears on
          hub_pid3: optional, the usb3 pid of the hub the device can appear on if
                    it enumerates in usb3
          pwr_ctrl: optional, servod control to toggle power
                    Note- if this is provided, a second test will be run to ensure
                    that when power is turned off the device is no longer visible
          mux_ctrl: optional, servod control for the mux if the usb device can be
                    muxed to multiple locations
          mux_val:  optional, servod |mux_ctrl| value that needs to be set for the
                    device to appear at the expected location
                    Note- |mux_ctrl| and |mux_val| need both be provided if either
                    is provided
          prompt:   optional, a string to display to the user if they need to do
                    some setup the test e.g. plug in a usb stick
        """
        test.Test.__init__(self, name)
        self.status = None
        self.prompt_message = prompt
        self.port_number = port_number
        self.hub_vid = hub_vid
        self.hub_pids = [hub_pid]
        if hub_pid3:
            self.hub_pids.append(hub_pid3)
        self.mux_ctrl = None
        self.mux_val = None
        self.pwr_ctrl = pwr_ctrl
        self.enum_timeout = NON_POWER_DELAY_S
        self.testname = self.name
        if self.pwr_ctrl:
            self.enum_timeout = POWER_DELAY_S
        if self.pwr_ctrl and mux_ctrl and mux_val:
            self.mux_val = mux_val
            self.mux_ctrl = mux_ctrl
            # Also amend the name to show the mux direction.
            self.testname = "%s (%s)" % (self.name, self.mux_val)
        elif mux_ctrl and mux_val:
            self._logger.info("mux_ctrl requires power control over the port.")
            self._logger.info("Test will run without the mux control.")
        elif mux_ctrl or mux_val:
            # This means one of them was provided, but not both. Report error
            # but ignore otherwise.
            self._logger.info(
                "You need to provide both mux_ctrl and mux_val for "
                "the test to use the mux_ctrl."
            )
            self._logger.info("Only got mux_ctrl:%r and mux_val:%r", mux_ctrl, mux_val)
            self._logger.info("Test will run without the mux control.")

    @property
    def debug_line(self):
        """Provide a detailed debug line where the test went wrong."""
        # overwrite standard definition for this test specificall.
        # This test runs in 3 stages: it checks the mux, then presence,
        # then power. This helps in giving debug instructions, as we never
        # reach the next stage if the previous one fails.
        if self.status == self.MUX_FAILURE:
            return (
                "Error using mux control %r for %r. Potentially an i2c "
                "issue on the board." % (self.mux_ctrl, self.name)
            )

        hub_str = " or ".join(["%04x:%04x" % (self.hub_vid, p) for p in self.hub_pids])
        dev_str = "hubs %s port %d (%s)" % (hub_str, self.port_number, self.name)
        if self.status == self.DETECTION_FAILURE:
            return (
                "Error detecting a USB device attached to %s. Could be device "
                "missing or usb port issue." % dev_str
            )
        if self.status == self.POWER_CYCLE_FAILURE:
            return (
                "Error turning off power to USB device attached to %s. Device "
                "was found, power remained. Maybe i2c issue, or GPIO expander "
                "issue." % dev_str
            )
        # we should really never get here.
        return "Unknown error for USB device attached to %s." % dev_str

    def prompt(self):
        """Instruct user if |self.prompt_message| was provided."""
        if self.prompt_message:
            user_input.instruct_user(self.prompt_message)

    def _presence_test(self, hubs):
        """Subtest to check if the device enumerates.

        Args:
          hubs: a list of usb sysfs hub paths that the device could appear on

        Returns:
          True if the device shows up on one of the paths in
          |hubs|.|self.port_number| False otherwise
        """
        # The device should be found at precisely *one* hub candidates |port_number|
        # port.
        paths_found = []
        for hub_path in hubs:
            dev_path = "%s.%d" % (hub_path, self.port_number)
            if device_util.wait_for_path(dev_path, self.enum_timeout):
                self._logger.debug("Found %r", dev_path)
                paths_found.append(dev_path)
            else:
                self._logger.debug("Did not find %r", dev_path)
                # Print hub content if possible
                if os.path.exists(hub_path):
                    self._logger.debug("Hub content: %s", os.listdir(hub_path))
        if not paths_found:
            self._logger.debug("Device not on any known location.")
            return False
        elif paths_found and len(paths_found) > 1:
            self._logger.error("A device showed up on the hubs USB3 and USB2 port.")
            self._logger.error(
                "Device should only show up on one mode, but found: %r",
                ", ".join(paths_found),
            )
            return False
        # We only found the device on one hub port. Great.
        return paths_found[0]

    def _power_off_test(self, path):
        """Subtest to check device can be power cycled.

        Args:
          path: sysfs usb path of the device itself

        Returns:
          True if |path| stopped existing after the power to the port was turned off
          False otherwise
        """
        # This is only invoked if self.pwr_ctrl exists so this is safe to call.
        self.client.set(self.pwr_ctrl, "off")
        # Change the timeout to just be 0.5s as we expect to not find the
        # device. We also know that if this test was called, then the device
        # has been found once before.
        result = device_util.wait_for_path_removal(path, self.enum_timeout)
        self.client.set(self.pwr_ctrl, "on")
        # Give device time to come back.
        device_util.wait_for_path(path, self.enum_timeout)
        return result

    @property
    def ptest_name(self):
        """Formatting to display the presence test."""
        return "%s [Presence Test]" % self.testname

    @property
    def pwrtest_name(self):
        """Formatting to display the power test."""
        return "%s [Power Off Test]" % self.testname

    def run(self):
        """Run up to two tests (presence, and power).

        Ensure any of the hubs provided in the init can be found. Then setup the
        device (power on, mux in the right position) before running the presence
        test. If power control is provided, and the presence test succeeds, run
        the power off test as well.

        Raises:
          UsbDeviceTestError: Hub (neither usb2 or usb3 version) cannot be found

        Returns:
          [(self.ptestname, outcome),
           (self.pwrtestname, outcome) // if ran]
           see the subtest methods below for outcome criteria
           Note: outcome for the presence test will also be False if the test fails
           to set the mux in the desired direction.
        """
        results = []
        hubs = []
        for pid in self.hub_pids:
            try:
                # Pass a 0 timeout here as the device should already be there.
                hub = device_util.wait_for_usb_device(
                    vid=self.hub_vid, pid=pid, timeout=0
                )
                hubs.append(hub)
            except device_util.DeviceUtilError:
                # Pass for now, both hubs might not exist.
                pass
        if not hubs:
            hub_candidate_str = " ".join(
                ["%04x:%04x" % (self.hub_vid, p) for p in self.hub_pids]
            )
            # We need to have at least one hub to know what's up.
            raise UsbDeviceTestError("Hub not found. Checked: %s" % hub_candidate_str)

        original_mux = mux_cycled = None

        # The first test, is seeing whether the device can be found at all or not.
        if self.pwr_ctrl:
            if self.mux_ctrl:
                original_mux = self.client.get(self.mux_ctrl)
                if original_mux != self.mux_val:
                    mux_cycled = True
                    self._logger.debug(
                        "Trying to set %r to %r", self.mux_ctrl, self.mux_val
                    )
                    # Turn power off first, and then cycle the mux.
                    self.client.set(self.pwr_ctrl, "off")
                    # Sleep a short delay between the mux switching for the signal to
                    # change safely.
                    time.sleep(MUX_DELAY_S)
                    self.client.set(self.mux_ctrl, self.mux_val)
                    time.sleep(MUX_DELAY_S)
                    # now safely tun the power back on for the mux.
                    self.client.set(self.pwr_ctrl, "on")
                    val = self.client.get(self.mux_ctrl)
                    if val != self.mux_val:
                        self.status = self.MUX_FAILURE
                        self._logger.error(
                            "%r is at %r. Failed to set to %r.",
                            self.mux_ctrl,
                            val,
                            self.mux_val,
                        )
                        return [(self.ptest_name, False)]
            # Make sure the device is always on.
            self.client.set(self.pwr_ctrl, "on")
        path = self._presence_test(hubs)
        # path will be the path that the device is on if found, or 'False'.
        # get a clean signal here whether the device was found.
        presence = bool(path)
        results.append((self.ptest_name, presence))
        if presence and self.pwr_ctrl:
            # Only check that the device disappears if both the presence test
            # passed and the pwr_ctrl is available.
            outcome = self._power_off_test(path)
            if not outcome:
                self.status = self.POWER_CYCLE_FAILURE
            results.append((self.pwrtest_name, outcome))
        else:
            self.status = self.DETECTION_FAILURE
        if original_mux and mux_cycled:
            # restore the mux.
            self._logger.debug("Restoring %r to %r", self.mux_ctrl, original_mux)
            self.client.set(self.mux_ctrl, original_mux)
        return results
