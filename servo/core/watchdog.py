# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Watchdog for servo devices falling off the usb stack."""

import logging
import os
import signal
import threading
import time


class DeviceWatchdog(threading.Thread):
    """Watchdog to ensure servod stops when a servo device gets lost.

    Public Attributes:
      done: event to signal that the watchdog functionality can stop
    """

    # Default rate in seconds used to poll.
    DEFAULT_POLL_RATE = 1.0

    # Rate in seconds used to poll when a reinit capable device is attached.
    REINIT_POLL_RATE = 0.1

    # Grace period in seconds before killing servod for non-reinit devices
    DISCONNECT_GRACE_PERIOD_SEC = 20.0

    class DuplicateFilter(logging.Filter):
        """Prevent duplicate log messages from being logged more than once per
        minute.
        """

        def __init__(self):
            super().__init__()
            self.last_log = None
            self.next_log_time = time.time()

        def filter(self, record):
            current_log = (record.msg, record.levelno, record.args)
            if current_log == self.last_log and self.next_log_time > time.time():
                return False
            self.last_log = current_log
            self.next_log_time = time.time() + 60
            return True

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
        self._logger.addFilter(DeviceWatchdog.DuplicateFilter())
        self._turndown_signal = signal.SIGTERM
        self.done = threading.Event()
        self._servod = servod
        self._rate = self.DEFAULT_POLL_RATE
        self._devices = []
        self._reconnect_timeout = float(reconnect_timeout)

        for device in self._servod.get_devices():
            self._devices.append(device)

        self._update_poll_rate()

        # TODO(coconutruben): Here and below in addition to VID/PID also print out
        # the device type i.e. servo_micro.
        self._logger.info("Watchdog setup for devices: %s", self._devices)

    @property
    def reconnect_timeout(self):
        return self._reconnect_timeout

    @reconnect_timeout.setter
    def reconnect_timeout(self, new_timeout):
        self._reconnect_timeout = float(new_timeout)
        self._update_poll_rate()

    def _update_poll_rate(self):
        self._rate = self.DEFAULT_POLL_RATE
        for device in self._devices:
            if device.reinit_ok():
                if self._reconnect_timeout <= 0:
                    self._rate = self.REINIT_POLL_RATE
                    self._logger.info(
                        "Reinit capable device found. Polling rate set to %.2fs.",
                        self._rate,
                    )
                else:
                    self._rate = self._reconnect_timeout / max(
                        device.REINIT_ATTEMPTS, 1
                    )
                    self._logger.info(
                        "Reinit capable device found. Polling rate set "
                        "to %.2fs for %.2fs reconnect timeout",
                        self._rate,
                        self._reconnect_timeout,
                    )
                # Use the first reinit capable device to determine the polling rate.
                # This fixes a prior bug where the rate was overwritten by the
                # last device.
                break

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
        # Keep track of device numbers to catch issues where a device re-enumerates
        # without the watchdog catching it.
        devnums = {dev.get_id(): dev.usb_devnum() for dev in self._devices}
        while not self.done.is_set():
            self.done.wait(self._rate)
            for device in self._devices:
                dev_id = device.get_id()
                if device.is_connected():
                    # Device was found. If it is in the disconnected devices, then it
                    # needs to be reinitialized.
                    # If the device's devnum has changed, then a re-enumeration happened
                    # that the watchdog missed. This is fine for re-init capable
                    # devices, but not for the rest.
                    devnum = device.usb_devnum()
                    if devnum != devnums[dev_id] or dev_id in missing_devices:
                        if not device.reinit_ok():
                            # Re-enumeration here is bad and not recoverable.
                            if devnum != devnums[dev_id]:
                                self._logger.error(
                                    "Device - %s - changed devnum from %d to %d.",
                                    device,
                                    devnums[dev_id],
                                    devnum,
                                )
                            else:
                                self._logger.error(
                                    "Device - %s - reconnected with "
                                    "the same devnum %d.",
                                    device,
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
                            # Once the last missing device has been found again,
                            # reinitialize them all.
                            try:
                                self._servod.reinitialize()
                            except Exception as e:
                                # Has to be a broad except because we do not want to
                                # orphan the watchdog thread. But instead of turning
                                # down servod instantly, we retry by treating the
                                # device as still disconnected (e.g. sysfs exists
                                # but libusb enumeration isn't fully ready yet).
                                self._logger.debug(
                                    "Failed to reinit servod (device may not "
                                    "be fully enumerated yet): %s",
                                    e,
                                    exc_info=True,
                                    stack_info=True,
                                )
                                missing_devices[dev_id] = 1
                                device.disconnect()
                else:
                    # Device was not found.
                    self._logger.debug("Device - %s not found when polling.", device)
                    if not device.reinit_ok():
                        # Calculate max allowed failures based on the current
                        # poll rate to achieve a 20s grace period.
                        max_allowed_failures = int(
                            self.DISCONNECT_GRACE_PERIOD_SEC / self._rate
                        )
                        if dev_id not in missing_devices:
                            missing_devices[dev_id] = 1
                        else:
                            missing_devices[dev_id] += 1

                        if missing_devices[dev_id] >= max_allowed_failures:
                            self._logger.error(
                                "Device - %s - not found for %d consecutive polls. "
                                "Turning down servod.",
                                device,
                                missing_devices[dev_id],
                            )
                            self.disconnect(device)
                            break
                        continue
                    missing_devices[dev_id] = 1
                    device.disconnect()
