# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Helper functions to monitor attach/detach and presence of usb devices."""

import logging
import os
import time

import servo.utils.usb_hierarchy as usb_hierarchy
from servo_mfg import user_input


# Timeout to wait for a user to plug usb device in.
USB_TIMEOUT_S = 180

# Polling rate to check whether a usb device is connected.
GENERAL_POLL_RATE = 0.1


class DeviceUtilError(Exception):
    """Device util error class."""


def wait_for_usb_disconnect(
    vid, pid, pid3=None, timeout=USB_TIMEOUT_S, message=None, enter_to_confirm=False
):
    """Wait for a usb device to disconnect.

    Note: if both pid and pid3 are provided, finding _neither_ of them will
          register as a successful disconnect.

    Args:
      vid: vid of the usb device
      pid: pid of the usb device
      pid3: pid of the usb device if it can show up with two different pids for
            usb2/usb3.
      timeout: time in seconds to check for the disconnect
      message: optional prompt to send to the user before checking
      enter_to_confirm: bool, whether the user should confirm the |message|
                        before proceeding

    Raises:
      DeviceUtilError: user confirmation is requested but not provided within
                       timeout
      DeviceUtilError: if the device was not disconnected within |timeout| seconds
    """
    if message:
        if not user_input.instruct_user(message, enter_to_confirm=enter_to_confirm):
            raise DeviceUtilError("User failed to confirm unplug.")
    pids = [pid]
    if pid3 is not None:
        logging.debug(
            "USB device has provided two pids, ideally one for the usb3"
            "(0x%04x:0x%04x) device and one for the "
            "usb2(0x%04x:0x%04x) device.",
            vid,
            pid3,
            vid,
            pid,
        )
        pids.append(pid3)
    end = time.time() + timeout
    while True:
        found_pids = []
        for p in pids:
            try:
                paths = usb_hierarchy.Hierarchy.get_all_usb_device_sysfs_paths(
                    [(vid, p)]
                )
                if paths:
                    # This means the device is still around. Queue it again.
                    found_pids.append(p)
            except usb_hierarchy.HierarchyError as e:
                # Sometimes the device cannot be found as we are in the middle of
                # plugging and unplugging. This means we cannot get a clean signal.
                # Simply continue and wait for the next round.
                logging.debug(str(e))
        # Set the |found_pids| to be the |pids| to check again.
        if not found_pids:
            # None of the pids are found: safe to say the device is disconnected.
            return
        pids = found_pids
        # Getting here indicates that some devices with |vid:pid| are still around.
        time.sleep(GENERAL_POLL_RATE)
        # Perform this check at the end here to allow for the function to be used
        # with a timeout = 0 to detect already disconnected device.
        if time.time() > end:
            # Add this here rather than in the while loop to make sure that
            # it will look for the image once before throwing errors.
            raise DeviceUtilError(
                "Device %04x:%04x was not disconnected after %ds" % (vid, pid, timeout)
            )


def wait_for_usb_device(
    vid, pid, pid3=None, timeout=USB_TIMEOUT_S, message=None, enter_to_confirm=False
):
    """Wait for a usb device to connect.

    Note: if both pid and pid3 are provided, finding _either_ of them will
          register as a successful connect.

    Args:
      vid: vid of the usb device
      pid: pid of the usb device
      pid3: pid of the usb device if it can show up with two different pids for
            usb2/usb3.
      timeout: time in seconds to check for the connect
      message: optional prompt to send to the user before checking
      enter_to_confirm: bool, whether the user should confirm the |message|
                        before proceeding

    Returns:
      sysfs usb device path for device. If both pid3 and pid are provided,
      returns the first one found.

    Raises:
      DeviceUtilError: user confirmation is requested but not provided within
                       timeout
      DeviceUtilError: if the device was not connected within |timeout| seconds
    """
    if message:
        if not user_input.instruct_user(message, enter_to_confirm=enter_to_confirm):
            raise DeviceUtilError("User failed to confirm plug in.")
    multi_device_warning_sent = False
    pids = [pid]
    if pid3 is not None:
        logging.debug(
            "USB device has provided two pids, ideally one for the usb3"
            "(0x%04x:0x%04x) device and one for the "
            "usb2(0x%04x:0x%04x) device.",
            vid,
            pid3,
            vid,
            pid,
        )
        pids.append(pid3)
    end = time.time() + timeout
    while True:
        for p in pids:
            try:
                devs = usb_hierarchy.Hierarchy.get_all_usb_device_sysfs_paths(
                    [(vid, p)]
                )
            except usb_hierarchy.HierarchyError as e:
                # Sometimes the device cannot be found as we are in the middle of
                # plugging and unplugging. This means we cannot get a clean signal.
                # Simply continue and wait for the next round.
                logging.debug(str(e))
                # Set devs empty here to indicate that we don't know yet if the device
                # is found or not.
                devs = []
            if len(devs) > 1 and not multi_device_warning_sent:
                user_input.instruct_user(
                    "Please make sure only one such device is "
                    "connected. Currently, there are %d such "
                    "devices" % len(devs)
                )
                # Only warn the user once.
                multi_device_warning_sent = True
            elif len(devs) == 1:
                return devs[0]
            elif time.time() > end:
                # Add this here rather than in the while loop to make sure that
                # it will look for the image once before throwing errors.
                raise DeviceUtilError(
                    "Unique device %04x:%04x was not connected "
                    "after %ds" % (vid, pid, timeout)
                )
        # If no exit condition has been met just sleep.
        time.sleep(GENERAL_POLL_RATE)


def wait_for_path_removal(path, timeout=USB_TIMEOUT_S):
    """Helper to wait |timeout| seconds for |path| to disappear.

    Note: this is intended for sysfs usb paths to check whether specific
          ports on hubs have a device connected

    Args:
      path: path to wait for
      timeout: timeout in seconds to wait

    Returns:
      True if |path| disappeared within |timeout| seconds, False otherwise
    """
    end = time.time() + timeout
    while True:
        if not os.path.exists(path):
            return True
        if time.time() > end:
            break
        # If no exit condition has been met just sleep.
        time.sleep(GENERAL_POLL_RATE)
    return False


def wait_for_path(path, timeout=USB_TIMEOUT_S):
    """Helper to wait |timeout| seconds for |path| to appear.

    Note: this is intended for sysfs usb paths to check whether specific
          ports on hubs have a device connected

    Args:
      path: path to wait for
      timeout: timeout in seconds to wait

    Returns:
      True if |path| was found within |timeout| seconds, False otherwise
    """
    end = time.time() + timeout
    while True:
        if os.path.exists(path):
            return True
        if time.time() > end:
            break
        # If no exit condition has been met just sleep.
        time.sleep(GENERAL_POLL_RATE)
    return False
