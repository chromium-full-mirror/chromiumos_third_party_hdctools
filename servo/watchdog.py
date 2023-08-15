# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Watchdog for servo devices falling off the usb stack."""

import logging
import os
import signal
import threading


class DeviceWatchdog(threading.Thread):
    """Watchdog to ensure servod stops when a servo device gets lost.

    Public Attributes:
      done: event to signal that the watchdog functionality can stop
    """

    # Default rate in seconds used to poll.
    DEFAULT_POLL_RATE = 1.0

    # Rate in seconds used to poll when a reinit capable device is attached.
    REINIT_POLL_RATE = 0.1

    def __init__(self, servod, reconnect_timeout=0.0):
        """Setup watchdog thread.

        Args:
          servod: servod server the watchdog is watching over.
          reconnect_timeout: approx. secs for device reconnect,
                             poll rate will be adjusted accordingly.
        """
        threading.Thread.__init__(self)
        self.daemon = True
        self._logger = logging.getLogger(type(self).__name__)
        self._turndown_signal = signal.SIGTERM
        self.done = threading.Event()
        self._servod = servod
        self._rate = self.DEFAULT_POLL_RATE
        self._devices = []

        for device in self._servod.get_devices():
            self._devices.append(device)
            if device.reinit_ok():
                if reconnect_timeout <= 0:
                    self._rate = self.REINIT_POLL_RATE
                    self._logger.info(
                        "Reinit capable device found. Polling rate set to %.2fs.",
                        self._rate,
                    )
                else:
                    self._rate = reconnect_timeout / max(device.REINIT_ATTEMPTS, 1)
                    self._logger.info(
                        "Reinit capable device found. Polling rate set "
                        "to %.2fs for %.2fs reconnect timeout",
                        self._rate,
                        reconnect_timeout,
                    )

        # TODO(coconutruben): Here and below in addition to VID/PID also print out
        # the device type i.e. servo_micro.
        self._logger.info("Watchdog setup for devices: %s", self._devices)

    def deactivate(self):
        """Signal to watchdog to stop polling."""
        self.done.set()

    def disconnect(self, device=None):
        """Helper to turn down servod if device not found.

        Args:
          device: servo device object
        """
        # Device was not found and we can't reinitialize it. End servod.
        if device is not None:
            self._logger.error("Device - %s - Turning down servod.", device)
        else:
            self._logger.error("Servod reinit failed - Turning down servod.")
        # Watchdog should run in the same process as servod thread.
        os.kill(os.getpid(), self._turndown_signal)
        self.done.set()

    def run(self):
        """Poll |_devices| every |_rate| seconds. Send SIGTERM if device lost."""
        # Devices that need to be reinitialized
        missing_devices = {}
        # Keep track of device numbers to catch issues where a device reenumerates
        # without the watchdog catching it.
        devnums = {dev.get_id(): dev.usb_devnum() for dev in self._devices}
        while not self.done.is_set():
            self.done.wait(self._rate)
            for device in self._devices:
                dev_id = device.get_id()
                if device.is_connected():
                    # Device was found. If it is in the disconnected devices, then it
                    # needs to be reinitialized.
                    # If the device's devnum has changed, then a reenumeration happened
                    # that the watchdog missed. This is fine for reeinit capable devices,
                    # but not for the rest.
                    devnum = device.usb_devnum()
                    if devnum != devnums[dev_id]:
                        if not device.reinit_ok():
                            # Reenumeration here is bad and not recoverable.
                            self._logger.error(
                                "Device - %s - changed devnum from %d to %d.",
                                device,
                                devnums[dev_id],
                                devnum,
                            )
                            self.disconnect(device)
                            break
                        # Here, the device is reinit_ok()
                        # Refresh the device number.
                        devnums[device.get_id()] = devnum
                        # Need to remove it from the missing_devices if it was there
                        # so we know how many are still disconnected.
                        missing_devices.pop(dev_id, None)
                        if not missing_devices:
                            # Once the last missing device has been found again, reinitialize
                            # them all.
                            try:
                                self._servod.reinitialize()
                            except Exception as e:
                                # Has to be a broad except because we do not want to orphan the
                                # watchdog thread, but rather make sure that we disconnect
                                # or *any* reinit failure
                                self._logger.debug(
                                    "Failed to reinit servod: %s",
                                    e,
                                    exc_info=True,
                                    stack_info=True,
                                )
                                self.disconnect()
                else:
                    # Device was not found.
                    self._logger.debug("Device - %s not found when polling.", device)
                    if not device.reinit_ok():
                        self.disconnect(device)
                        break
                    missing_devices[dev_id] = 1
                    device.disconnect()
