# Copyright 2018 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Driver for common sequences for image management on switchable usb port."""

import errno
import glob
import os
import subprocess
import tempfile
import time

import usb

from servo.drv import hw_driver
from servo.utils import scratch
from servo.utils.sys_interface import sys_interface
import servo.utils.usb_hierarchy as usb_hierarchy


# If a hub is attached to the usual image usb storage slot, use this port on the
# hub to search for the usb storage.
STORAGE_ON_HUB_PORT = 1


class UsbImageManagerError(hw_driver.HwDriverError):
    """Error class for UsbImageManager errors."""

    pass


# pylint: disable=invalid-name
# Servod driver discovery logic requires this naming convention
class usbImageManager(hw_driver.HwDriver):
    """Driver to handle common tasks on the switchable usb port."""

    # Polling rate to poll for image usb dev to appear if setting mux to
    # servo_sees_usbkey
    _POLLING_DELAY_S = 0.1
    # Timeout to wait before giving up on hoping the image usb dev will enumerate
    _WAIT_TIMEOUT_S = 30

    # Timeout to settle all pending tasks on the device before writing to it.
    _SETTLE_TIMEOUT_S = 60

    # Control aliases to the image mux and power intended for image management
    _IMAGE_USB_MUX = "image_usbkey_mux"
    _USB_MUX_BOTTOM = "bottom_usbkey_mux"  # only for servo v4.1
    _IMAGE_USB_PWR = "image_usbkey_pwr"
    _USB_PWR_BOTTOM = "bottom_usbkey_pwr"
    _IMAGE_DEV = "image_usbkey_dev"
    _IMAGE_MUX_TO_SERVO = "servo_sees_usbkey"

    _HTTP_PREFIX = "http://"

    _DEFAULT_ERROR_MSG = "No USB storage device found for image transfer."

    def _drv_init(self):
        """Driver specific initializer."""
        super()._drv_init()
        # This delay is required to safely switch the usb image mux direction
        self._poweroff_delay = self._params.get("usb_power_off_delay", 0)
        if self._poweroff_delay:
            self._poweroff_delay = float(self._poweroff_delay)
        # This is required to determine if the usbkey is connected to the host.
        # The |hub_ports| is a comma-separated string of usb hub port numbers
        # that the image usbkey enumerates under for a given servo device.
        # NOTE: initialization here is shared among multiple controls, some of which
        # do not use the hub_ports logic. Do not raise error here if the param
        # is not available, but rather inside the controls that leverage it.
        self._image_usbkey_hub_ports = None
        if "hub_ports" in self._params:
            self._image_usbkey_hub_ports = self._params.get("hub_ports").split(",")
        # Flag to indicate whether the usb port supports having a hub attached to
        # it. In that case, the image will be searched on the |STORAGE_ON_HUB_PORT|
        # of the hub.
        self._supports_hub_on_port = self._params.get("hub_on_port", False)
        self._error_msg = self._DEFAULT_ERROR_MSG
        if "error_amendment" in self._params:
            self._error_msg += " " + self._params["error_amendment"]

        # Retrieve map_params(if exists) and create a reversed dict to allow reverse lookup
        self._MAP_DICT = self._params.get("map_params")
        if isinstance(self._MAP_DICT, dict):
            self._MAP_DICT_REVERSED = {val: key for key, val in self._MAP_DICT.items()}
        else:
            self._MAP_DICT_REVERSED = None

    def _Get_image_usbkey_direction(self):
        """Return direction of image usbkey mux (as a usbkey string)."""
        return self._servod_get(self._IMAGE_USB_MUX)

    def _Get_second_usbkey_direction(self):
        """Return direction of bottom usbkey mux.
        Please note that this is only compatible with servo_v4p1
        """
        return self._servod_get(self._USB_MUX_BOTTOM)

    def _Set_image_usbkey_direction(self, mux_direction):
        """Connect USB flash stick to either servo or DUT.

        This function switches 'usb_mux_sel1' to provide electrical
        connection between the USB port J3 and either servo or DUT side.

        Args:
          mux_direction: string/int values of "servo_sees_usbkey" or "dut_sees_usbkey".
        Raises:
          UsbImageManagerError: if an invalid usbkey int is passed in
        """
        # If mux_direction is an int, change it to its corresponding string
        if isinstance(mux_direction, int) and self._MAP_DICT_REVERSED is not None:
            try:
                mux_direction = self._MAP_DICT_REVERSED[str(mux_direction)]
            except KeyError as e:
                raise UsbImageManagerError(
                    "Invalid usbkey value. Try one of these values: "
                    + str(self._MAP_DICT)
                ) from e
        self._SafelySwitchMux(mux_direction)
        if self._servod_get(self._IMAGE_USB_MUX) == self._IMAGE_MUX_TO_SERVO:
            # This will ensure that we make a best-effort attempt to only
            # return when the block device of the attached usb stick fully
            # enumerates.
            self._servod_get(self._IMAGE_DEV)

    def _Set_second_usbkey_direction(self, mux_direction):
        """Connect USB port to either servo or DUT.

        This function switches 'usb_mux_sel2' to provide electrical
        connection between the USB port and either servo or DUT side.

        Args:
          mux_direction: string/int values of "servo_sees_usbkey" or "dut_sees_usbkey".
        Raises:
          UsbImageManagerError: if an invalid usbkey int is passed in
        """
        # If mux_direction is an int, change it to its corresponding string
        if isinstance(mux_direction, int) and self._MAP_DICT_REVERSED is not None:
            try:
                mux_direction = self._MAP_DICT_REVERSED[str(mux_direction)]
            except KeyError as e:
                raise UsbImageManagerError(
                    "Invalid usbkey value. Try one of these values: "
                    + str(self._MAP_DICT)
                ) from e
        self._SafelySwitchMux(mux_direction, self._USB_MUX_BOTTOM)
        # Note: We don't check that image usb is connected as this port isn't currently used for images

    def _SafelySwitchMux(self, mux_direction, usb_mux=None):
        """Helper to switch the usb mux.

        Switching the usb mux is accompanied by powercycling
        of the USB stick, because it sometimes gets wedged if the mux
        is switched while the stick power is on.

        Args:
          mux_direction: string values of "servo_sees_usbkey" or "dut_sees_usbkey".
        """
        # Older servos have just one usb "image port", so the default mux is image.
        if usb_mux is None:
            usb_mux = self._IMAGE_USB_MUX

        # Select corresponding usb_pwr
        usb_pwr = (
            self._IMAGE_USB_PWR
            if usb_mux == self._IMAGE_USB_MUX
            else self._USB_PWR_BOTTOM
        )

        if self._servod_get(usb_mux) != mux_direction:
            self._servod_set(usb_pwr, "off")
            time.sleep(self._poweroff_delay)
            self._servod_set(usb_mux, mux_direction)
            time.sleep(self._poweroff_delay)
        if self._servod_get(usb_pwr) != "on":
            # Enforce that power is supplied.
            self._servod_set(usb_pwr, "on")

    def _PathIsHub(self, usb_sysfs_path):
        """Return whether |usb_sysfs_path| is a usb hub."""
        if not os.path.exists(usb_sysfs_path):
            return False
        with open(os.path.join(usb_sysfs_path, "bDeviceClass"), "r") as classf:
            return int(classf.read().strip(), 16) == usb.CLASS_HUB

    def _Get_image_usbkey_dev(self):
        """Probe the USB disk device plugged in the servo from the host side.

        Returns:
          USB disk path if one and only one USB disk path is found, otherwise an
          empty string.

        Raises:
          UsbImageManagerError: if 'hub_ports' was not defined in params
        """
        if self._image_usbkey_hub_ports is None:
            raise UsbImageManagerError("hub_ports need to be defined in params.")
        # When the user is requesting the usb_dev they most likely intend for the
        # usb to the facing the servo, and be powered. Enforce that.
        self._SafelySwitchMux(self._IMAGE_MUX_TO_SERVO, self._IMAGE_USB_MUX)
        # Look for own servod usb device
        # pylint: disable=protected-access

        with scratch.ConcurrencyGuard(max_concurrency=3, name="imaging"):
            # Need servod information to find own servod instance.
            # hub device can be the cluster root device, or the main device if there
            # is only 1 device on this servod instance
            hub_on_servo = self._driver_client.GetUSBHubAddress().response
            if len(hub_on_servo) == 0:
                raise UsbImageManagerError("There is no USB hub device connected.")
            # Image usb is one of the hub ports |self._image_usbkey_hub_ports|
            image_location_candidates = [
                "%s.%s" % (hub_on_servo, p) for p in self._image_usbkey_hub_ports
            ]
            # all |image_location_candidates| here assume that the device is on the same
            # bus as the servo device. If the servo is attached to a usb controller
            # that has both usb2 and usb3 busses, we need to search both.
            busnum = usb_hierarchy.Hierarchy.bus_num_from_sysfs(hub_on_servo)
            usb3_busnum = usb_hierarchy.Hierarchy.complement_bus_num(busnum)
            if usb3_busnum is not None:
                # It can be none if the bus only appears in one speed.
                usb3_location_candidates = [
                    c.replace("/%d-" % busnum, "/%d-" % usb3_busnum)
                    for c in image_location_candidates
                ]
                image_location_candidates.extend(usb3_location_candidates)
            hub_location_candidates = []
            if self._supports_hub_on_port:
                # Here the config says that |image_usbkey_sysfs| might actually have a hub
                # and not storage attached to it. In that case, the |STORAGE_ON_HUB_PORT|
                # on that hub will house the storage.
                hub_location_candidates = [
                    "%s.%d" % (path, STORAGE_ON_HUB_PORT)
                    for path in image_location_candidates
                ]
                image_location_candidates.extend(hub_location_candidates)
            self._logger.debug(
                "usb image dev file candidates: %s",
                ", ".join(image_location_candidates),
            )
            # Let the device settle first before pushing out any data onto it.
            sys_interface.call(["udevadm", "settle", "-t", str(self._SETTLE_TIMEOUT_S)])
            self._logger.debug("All udev events have settled.")
            end = time.time() + self._WAIT_TIMEOUT_S
            while image_location_candidates:
                active_storage_candidate = image_location_candidates.pop(0)
                if os.path.exists(active_storage_candidate):
                    if self._PathIsHub(active_storage_candidate):
                        # Do not check the hub, only devices.
                        continue
                    # Use /sys/block/ entries to see which block device is the |hub_device|.
                    # Use sd* to avoid querying any non-external block devices.
                    for candidate in glob.glob("/sys/block/sd*"):
                        # |candidate| is a link to a sys hw device file
                        devicepath = os.path.realpath(candidate)
                        # |active_storage_candidate| is also a link to a sys hw device file
                        if devicepath.startswith(
                            os.path.realpath(active_storage_candidate)
                        ):
                            devpath = "/dev/%s" % os.path.basename(candidate)
                            try:
                                f = open(devpath, "rb")
                            except FileNotFoundError:
                                continue
                            # ensure that the block device is readable
                            # by reading the first sector.
                            read_bytes = 512
                            read_len = 0
                            with f:
                                try:
                                    read_len = len(f.read(read_bytes))
                                except OSError as error:
                                    self._logger.warning(
                                        "open() or read() of {!r} failed with errno {:d} {} ({}), skipping it as a USB mux drive candidate.".format(
                                            devpath,
                                            error.errno,
                                            errno.errorcode.get(error.errno, "UNKNOWN"),
                                            os.strerror(error.errno),
                                        )
                                    )
                                    continue
                            if read_len < read_bytes:
                                self._logger.warning(
                                    "read() returned only {:d} bytes out of {:d} requested from {!r}, the drive is likely not functional, skipping it as a USB mux drive candidate.".format(
                                        read_len, read_bytes, devpath
                                    )
                                )
                                continue
                            return devpath
                # Enqueue the candidate again in hopes that it will eventually enumerate.
                image_location_candidates.append(active_storage_candidate)
                if time.time() >= end:
                    break
                time.sleep(self._POLLING_DELAY_S)
        # Split and join to help with error message formatting from XML that might
        # introduce multiple white-spaces.
        self._logger.warning(" ".join(self._error_msg.split()))
        self._logger.warning(
            "Stick should be at one of the usb image dev file candidates: %s",
            ", ".join(image_location_candidates),
        )
        if self._supports_hub_on_port:
            self._logger.warning(
                "If using a hub on the image key port, please make "
                "sure to use port %d on the hub. This should be at "
                "one of: %s.",
                STORAGE_ON_HUB_PORT,
                ", ".join(hub_location_candidates),
            )
        return ""

    def _Set_make_image_noninteractive(self, usb_dev_partition):
        """Makes the recovery image noninteractive.

        A noninteractive image will reboot automatically after installation
        instead of waiting for the USB device to be removed to initiate a system
        reboot.

        Mounts |usb_dev_partition| and creates a file called "non_interactive" so
        that the image will become noninteractive.

        Args:
          usb_dev_partition: string of dev partition file e.g. sdb1 or sdc3

        Raises:
         UsbImageManagerError: if error occurred during the process
        """
        # pylint: disable=broad-except
        # Ensure that any issue gets caught & reported as UsbImageError
        if not usb_dev_partition or not os.path.exists(usb_dev_partition):
            msg = "Usb partition device file provided %r invalid." % usb_dev_partition
            self._logger.error(msg)
            raise UsbImageManagerError(msg)
        # Create TempDirectory
        tmpdir = tempfile.mkdtemp()
        result = True
        if not tmpdir:
            self._logger.error("Failed to create temp directory.")
            result = False
        else:
            # Mount drive to tmpdir.
            rc = sys_interface.call(["mount", usb_dev_partition, tmpdir])
            if rc == 0:
                # Create file 'non_interactive'
                non_interactive_file = os.path.join(tmpdir, "non_interactive")
                try:
                    open(non_interactive_file, "w").close()
                except IOError as e:
                    self._logger.error(
                        "Failed to create file %s : %s ( %d )",
                        non_interactive_file,
                        e.strerror,
                        e.errno,
                    )
                    result = False
                except BaseException as e:
                    self._logger.error(
                        "Unexpected Exception creating file %s : %s",
                        non_interactive_file,
                        str(e),
                    )
                    result = False
                # Unmount drive regardless if file creation worked or not.
                rc = sys_interface.call(["umount", usb_dev_partition])
                if rc != 0:
                    self._logger.error("Failed to unmount USB Device")
                    result = False
            else:
                self._logger.error("Failed to mount USB Device")
                result = False

            # Delete tmpdir. May throw exception if 'umount' failed.
            try:
                sys_interface.rmdir(tmpdir)
            except OSError as e:
                self._logger.error(
                    "Failed to remove temp directory %s : %s", tmpdir, str(e)
                )
                result = False
            except BaseException as e:
                self._logger.error(
                    "Unexpected Exception removing tempdir %s : %s", tmpdir, str(e)
                )
                result = False
        if not result:
            raise UsbImageManagerError("Failed to make image noninteractive.")
