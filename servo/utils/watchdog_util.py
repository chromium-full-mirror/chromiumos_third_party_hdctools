# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


class WatchdogUtilError(Exception):
    """Error class for watchdog util"""


def get_device_state(device):
    """String of the current device state."""
    connected_str = "" if device.is_connected() else "dis"
    disconnect_ok_str = " (disconnect ok)" if device.disconnect_is_ok() else ""
    name = ", ".join(device.get_prefixes())
    return "%s: %sconnected%s" % (name, connected_str, disconnect_ok_str)


def get_device_from_type(servod, device_type):
    """Returns the device with the given type."""
    if device_type:
        # Check main device before checking other devices
        main_device = servod.get_main_device()
        if device_type in servod.get_main_device().template.TYPE:
            return main_device

        # If the name matches with multiple devices, error out.
        candidates = []
        for device in servod.get_devices():
            if device_type in device.template.TYPE:
                candidates.append(device)
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            raise WatchdogUtilError(
                "Multiple devices %s matching with type %s" % (candidates, device_type)
            )
    return None
