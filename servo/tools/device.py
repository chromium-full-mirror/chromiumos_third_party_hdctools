# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# pylint: disable=redefined-variable-type

"""Device tool to manage the (usb) servo device."""

import collections
import time

import usb

from servo.common import servo_dev_templates
from servo.common import tiny_servod
from servo.drv.pty_driver import PtyError
from servo.tools import tool
import servo.utils.usb_hierarchy as uh


class DeviceError(Exception):
    """Device tool error class."""


class Device(tool.Tool):
    """Class to implement various subtools to manage a servo devices."""

    # Time to sleep after reset to let kernel handle sysfs files
    RESET_DEBOUNCE_S = 2

    # time to sleep for the servo device to reenumerate.
    MAX_REINIT_SLEEP_S = 8

    # Polling intervals to find the |devnum| file for reset device.
    REINIT_POLL_SLEEP_S = 0.1

    # Time to sleep and attempts to interact with servo console after reboot.
    REBOOT_SLEEP_S = 1
    REBOOT_TIMEOUT_ATTEMPTS = 4

    # Dictionary to look up the device's servo console USB interface number.
    # TODO(coconutruben): remove this once we have servo device templates that
    # contain all this information.
    USB_CONSOLE_IFACE = collections.defaultdict(dict)
    USB_CONSOLE_IFACE[0x18D1][0x501A] = 3  # servo_micro
    USB_CONSOLE_IFACE[0x18D1][0x501B] = 0  # servo_v4
    USB_CONSOLE_IFACE[0x18D1][0x5020] = 0  # sweetberry
    USB_CONSOLE_IFACE[0x18D1][0x520D] = 0  # servo_v4p1
    USB_CONSOLE_IFACE[0x18D1][0x5041] = 0  # c2d2

    @property
    def help(self):
        """Tool help message for parsing."""
        return "Manage servo device."

    def _usb_path(self, serial):
        """Helper to get the device path.

        Args:
          serial: str, servo serial

        Returns:
          /sys/bus/usb/devices/ path to servo with |serial| or None if not found
        """
        # This list is used to find all servos on the system.
        vid_pid_list = list(servo_dev_templates.SERVO_ID_DEFAULTS)
        devs = uh.Hierarchy.get_all_usb_device_sysfs_paths(vid_pid_list)
        for dev_path in devs:
            dev_serial = uh.Hierarchy.serial_from_sysfs(dev_path)
            if dev_serial == serial:
                return dev_path
        return None

    def reboot(self, args):
        """Reboot the device."""
        # First, let's make sure the device exists.
        reboot_error = None
        dev_path = self._usb_path(args.serial)
        if not dev_path:
            self.error("Device with serial %r not found.", args.serial)
        vid = uh.Hierarchy.vendor_id_from_sysfs(dev_path)
        pid = uh.Hierarchy.product_id_from_sysfs(dev_path)
        devnum = uh.Hierarchy.dev_num_from_sysfs(dev_path)
        if vid not in self.USB_CONSOLE_IFACE or pid not in self.USB_CONSOLE_IFACE[vid]:
            self.error(
                "Device %04x:%04x %s does not support reboot", vid, pid, args.serial
            )
        iface = self.USB_CONSOLE_IFACE[vid][pid]
        ts = tiny_servod.TinyServod(vid, pid, iface, args.serial)
        ts.pty._issue_cmd_get_results("chan 0", [">"])
        try:
            ts.pty._issue_cmd_get_results("reboot", [">"])
        except PtyError as ex:
            # We except a no-data error here occasionally, if the reboot
            # was too quick for the console to send a newline. That's fine.
            if "No data was sent from the pty" not in str(ex):
                raise
            reboot_error = ex
        # Make sure the device comes back with a new devnum before attempting
        # to communicate with it.
        self._check_devnum_reset(dev_path, devnum, "reboot")
        for i in range(self.REBOOT_TIMEOUT_ATTEMPTS):
            try:
                # Make sure the device is back
                self._logger.debug(
                    "Attempt %d to interact with console post reboot", i + 1
                )
                ts.reinitialize()
                ts.pty._issue_cmd_get_results("chan 0", [">"])
                ts.pty._issue_cmd_get_results(
                    "serialno", [r"Serial number: ([^\r\n]+)[\n\r]+"]
                )
                ts.pty._issue_cmd_get_results("chan restore", [">"])
                return
            except Exception as ex:
                # store the exception in reboot_error here so that we have access to
                # it later if we need to print it.
                self._logger.debug(ex)
                reboot_error = ex
            time.sleep(self.REBOOT_SLEEP_S)
        self.error(
            "Device %04x:%04x %s issue after reboot: %s",
            vid,
            pid,
            args.serial,
            reboot_error,
        )

    def usb_path(self, args):
        """Retrieve the usb sysfs path for a serial number."""
        dev_path = self._usb_path(args.serial)
        if dev_path:
            self._logger.info(dev_path)
        else:
            self.error("Device with serial %r not found.", args.serial)

    def usb_comms(self, args):
        """Test whether usb communication works for device at |args.serial|.

        This tool tries to identify USB devices that are still enumerated on the
        the system, but that fail to respond to USB communication e.g. because their
        data lines have been muxed off but the system has not registered that.

        The detection is done by using cached values of the device on sysfs to find
        the device on pyusb, and then attempting to read the iSerial, as this
        requires opening the device and communicating with it.
        """
        dev_path = self._usb_path(args.serial)
        if not dev_path:
            self.error("Device with serial %r not found.", args.serial)
        # Now, retrieve busnum and devnum using sysfs as those values are cached.
        devnum = uh.Hierarchy.dev_num_from_sysfs(dev_path)
        busnum = uh.Hierarchy.bus_num_from_sysfs(dev_path)
        dev = usb.core.find(address=devnum, bus=busnum)
        if dev is None:
            self.error("Device with serial %r not found on pyusb.", args.serial)
        # The real experiment - reading some data.
        try:
            _unused = usb.util.get_string(dev, dev.iSerialNumber)
        except (ValueError, usb.core.USBError) as e:
            self.error("Device with serial %r has USB comms issues. %s", args.serial, e)

    def _check_devnum_reset(self, dev_path, devnum, action):
        """Check that the |devnum| has changed after a reset/reboot/power-cycle

        Args:
          dev_path: device sysfs path
          devnum: int, usb devnum (original devnum, before reset action)
          action: str, action performed (used to print better errors/logs

        Note: this helper will call self.error() (and thus exit) if
        - the devnum does not change
        - it fails to read the devnum after self.MAX_REINIT_SLEEP_S
        """
        # Sleep a bit to let the device fully fall off, and the sysfs files be
        # renewed.
        time.sleep(self.RESET_DEBOUNCE_S)
        # For |MAX_REINIT_SLEEP_S| seconds, try to find the new devnum for the
        # device.
        end = time.time() + self.MAX_REINIT_SLEEP_S
        while time.time() < end:
            try:
                # check devnum reset
                if devnum == uh.Hierarchy.dev_num_from_sysfs(dev_path):
                    self.error(
                        "%r likely unsuccessful. devnum stayed the same.", action
                    )
                # If |devnum| changed, then the goal is fulfilled. Move on.
                break
            except uh.HierarchyError:
                # The device might not have reenumerated yet. Sample again.
                time.sleep(self.REINIT_POLL_SLEEP_S)
        else:
            # The while loop finished without breaking out e.g. we never read the
            # |devnum| file successfully.
            self.error(
                "unable to read device |devnum| file after %ds. Giving up.",
                self.MAX_REINIT_SLEEP_S,
            )

    def add_args(self, tool_parser):
        """Add the arguments needed for this tool."""
        subcommands = tool_parser.add_subparsers(dest="command")
        tool_parser.add_argument(
            "-s",
            "--serial",
            required=True,
            help="serial of servo device on the system.",
        )
        subcommands.add_parser("reboot", help="Reboot the device MCU")
        subcommands.add_parser(
            "usb-comms",
            help="Test whether USB communication on the device "
            "works. Exit code 1 if USB communication broken, "
            "and exit code 0 otherwise. Requires root.",
        )
        subcommands.add_parser(
            "usb-path", help="Show /sys/bus/usb/devices path of the device"
        )
