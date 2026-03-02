# Copyright 2016 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Allows creation of an interface via stm32 usb."""
import collections
import contextlib
import threading
import time

import usb

from servo.common.interface import common as c
from servo.common.interface import interface
from servo.utils import usb_hierarchy
from servo.utils.retry_util import retry_hardware


DeviceInfo = collections.namedtuple("DeviceInfo", ("vid", "pid", "serialname"))

EPInfo = collections.namedtuple("USBEPInfo", ("write_ep", "read_ep"))


class SusbError(c.InterfaceError):
    """Class for exceptions of Susb."""


class Susb(interface.Interface):
    # pylint: disable=abstract-method
    """Provide stm32 USB functionality.

    Instance Variables:
    _logger: S.* tagged log output
    _dev: pyUSB device object
    _read_ep: pyUSB read endpoint for this interface
    _write_ep: pyUSB write endpoint for this interface
    """

    READ_ENDPOINT = 0x81
    WRITE_ENDPOINT = 0x1
    TIMEOUT_MS = 100

    # Timeout to let a device debounce before trying to communicate with it again.
    DEV_DEBOUNCE_S = 0.1

    # The time after which to throw arms up when the lock acquisition fails.
    LOCK_TIMEOUT_S = 60

    # Map to keep track of what stm32usb device had what usb devnum (address)
    # last time it was configured by anyone.
    DEV_CONFIG_MAP = {}

    # Map to keep track of which USB interfaces have been claimed by the
    # process, and the corresponding endpoints.
    DEV_EP_STORE = collections.defaultdict(dict)

    # Map to keep locks on a per device level. These locks are required so that
    # no two threads try to set the configuration at the same time.
    DEVICE_LOCKS = collections.defaultdict(threading.Lock)

    # Device-level events used to signal when a thread is trying to reinitialize the
    # interface on a device. Since endpoints are being read in a (tight) loop like in
    # the UART interfaces, we want the tight loop to pause and give the right-of-way
    # to reinit interfaces (including non-UART interfaces) on the same device.
    REINIT_DONE_EVENTS = collections.defaultdict(threading.Event)

    def __init__(
        self,
        vendor=0x18D1,
        product=0x500F,
        interface_id=1,
        serialname=None,
        logger=None,
    ):
        """Susb constructor.

        Discovers and connects to stm32 USB endpoints.

        Args:
          vendor    : usb vendor id of stm32 device
          product   : usb product id of stm32 device
          interface_id : interface number ( 1 - 4 ) of stm32 device to use
          serialname: string of device serialname.

        Raises:
          SusbError: An error accessing Susb object
        """
        super().__init__(logger_name=type(self).__name__)
        if logger:
            self._logger = logger

        # Setting up the read and write locks. These are per instance, as each
        # instance represents one interface.
        self._read_ep_lock = threading.Lock()
        self._write_ep_lock = threading.Lock()
        self._logger.debug("Set up stm32 read and write locks")

        self._vendor = vendor
        self._product = product
        self._interface = interface_id
        self._serialname = serialname
        self._dev = None

        # An event used to signal when a thread is trying to reinitialize the
        # interface. Only clear the flag when performing a reset.
        self.REINIT_DONE_EVENTS[self.get_device_info()].set()
        self._find_device()

    @contextlib.contextmanager
    def _hold_lock(self, lock):
        """Helper to manage |lock|."""
        lock.acquire(timeout=self.LOCK_TIMEOUT_S)
        try:
            yield
        finally:
            lock.release()

    def wait_on_reset(self):
        """Potentially give the resetting thread preference.

        When endpoints are being read in a (tight) loop like in the UART interfaces,
        a race might happen between the reinitialization threads and the UART threads
        and the reinitialization threads keep losing out on the lock. The
        reinitialization threads might not be UART threads, and the UART threads should
        still give the right-of-way to the reinitialization threads regardless.

        With this helper, the thread can indicate that a reinit is about to happen on
        the same device, encouraging other threads that are performing read/write to
        stop asking for the lock, and wait until reinit is done.
        """
        # Set a very generous timeout for resetting to complete i.e the timeout
        # acquire both locks slowly, and one more lock timeout as buffer.
        if not self.REINIT_DONE_EVENTS[self.get_device_info()].wait(
            3 * self.LOCK_TIMEOUT_S
        ):
            raise SusbError(
                "Reset seems to have never finished for %04x:%04x %s"
                % self.get_device_info()
            )

    def reset_usb(self):
        """Reinitialize USB based on the device based settings from __init__"""
        # Signal that resetting is about to happen.
        self.REINIT_DONE_EVENTS[self.get_device_info()].clear()
        # Reading and writing is unavailable until the reset has finished.
        with self._hold_lock(self._read_ep_lock):
            with self._hold_lock(self._write_ep_lock):
                self._find_device()
        # Signal that resetting is done.
        self.REINIT_DONE_EVENTS[self.get_device_info()].set()

    def get_device_info(self):
        """Returns a tuple (vid, pid, serialname)."""
        return DeviceInfo(self._vendor, self._product, self._serialname)

    def _find_device(self):
        """Find device, setup configuration, and set up the usb endpoint"""
        # Find the stm32.
        devid = self.get_device_info()
        try:
            dev = usb_hierarchy.Hierarchy.get_usb_device(*devid)
        except (ValueError, usb.core.USBTimeoutError):
            self._logger.debug(
                "device not found on first attempt. Potentially debouncing."
            )
            time.sleep(self.DEV_DEBOUNCE_S)
            # The device should be found now. If not, let the error go through.
            dev = usb_hierarchy.Hierarchy.get_usb_device(*devid)
        if not dev:
            raise usb_hierarchy.HierarchyError(
                (
                    "No device found for id {0.vid:02x}:{0.pid:02x} "
                    "serial {0.serialname}"
                ).format(devid)
            )

        # TODO(crbug.com/1014672): investigate whether there is a better way not to
        # leak this many file descriptors for once system, and if there is a better
        # way to clean up the resources than the way/workaround implemented here.
        if self._dev:
            if self._dev.address != dev.address:
                # Dispose of the resources of the previously found device.
                usb.util.dispose_resources(self._dev)
            else:
                # The device did not reenumerate. No need to reinitialize it, it's still
                # valid.
                return

        # Detach raiden.ko if it is loaded.
        if dev.is_kernel_driver_active(self._interface):
            dev.detach_kernel_driver(self._interface)

        # Check whether the current address was already configured by another
        # interface, or whether we need to do that.
        if dev.address != self.DEV_CONFIG_MAP.get(devid):
            # This means the device either has never been set up, or no other
            # interface has setup the configuration for it.
            with self._hold_lock(self.DEVICE_LOCKS[devid]):
                try:
                    dev.get_active_configuration()
                except usb.core.USBError:
                    # Ignore failure as this is expected to fail for the first attempt
                    # that an interface makes to get the configuration.
                    # If |set_configuration| fails here, there is a real issue,
                    # don't mask it.
                    dev.set_configuration()

            self.DEV_CONFIG_MAP[devid] = dev.address
            # Delete all records of claimed interfaces so they can be reclaimed.
            self.DEV_EP_STORE.pop(devid, None)

        self._dev = dev
        serial = "(%s)" % self._serialname if self._serialname else ""
        self._logger.debug(
            "Found stm32%s: %04x:%04x", serial, self._vendor, self._product
        )

        # Get an endpoint instance.
        try:
            cfg = dev.get_active_configuration()
        except usb.core.USBError:
            self._logger.error(
                "You may have run out of endpoints on your machine "
                "due to running too many servos simultaneously. "
                "See crbug.com/652373"
            )
            raise

        # USB interface claiming.
        if self._interface not in self.DEV_EP_STORE[devid]:
            # Some servod interfaces share the same underlying USB interface. Only
            # one must claim it.
            usb.util.claim_interface(dev, self._interface)

            intf = usb.util.find_descriptor(cfg, bInterfaceNumber=self._interface)

            self._logger.debug("InterfaceNumber: %s", intf.bInterfaceNumber)

            read_ep_number = intf.bInterfaceNumber + self.READ_ENDPOINT
            read_ep = usb.util.find_descriptor(intf, bEndpointAddress=read_ep_number)
            self._logger.debug("Reader endpoint: 0x%x", read_ep.bEndpointAddress)

            write_ep_number = intf.bInterfaceNumber + self.WRITE_ENDPOINT
            write_ep = usb.util.find_descriptor(intf, bEndpointAddress=write_ep_number)
            self._logger.debug("Writer endpoint: 0x%x", write_ep.bEndpointAddress)

            self.DEV_EP_STORE[devid][self._interface] = EPInfo(
                read_ep=read_ep, write_ep=write_ep
            )

            self._logger.debug("Set up stm32 usb")

    def release(self):
        devid = self.get_device_info()
        if devid not in self.DEV_EP_STORE:
            raise SusbError("Device %r has no endpoints setup" % (devid,))
        if self._interface not in self.DEV_EP_STORE[devid]:
            raise SusbError(
                "Device %r has no endpoints setup for interface %d"
                % (devid, self._interface)
            )
        with self._hold_lock(self._read_ep_lock):
            with self._hold_lock(self._write_ep_lock):
                usb.util.release_interface(self._dev, self._interface)
        self._logger.debug("Released InterfaceNumber: %d", self._interface)

    def _get_ep(self, write=False):
        """Retrieve the ep.

        Args:
          write: whether the write ep or the read ep is desired

        Returns:
          reference to the shared EP

        Raises:
          SusbError: if EP is not available

        """
        devid = self.get_device_info()
        if devid not in self.DEV_EP_STORE:
            raise SusbError("Device %r has no endpoints setup" % (devid,))
        if self._interface not in self.DEV_EP_STORE[devid]:
            raise SusbError(
                "Device %r has no endpoints setup for interface %d"
                % (devid, self._interface)
            )
        if write:
            return self.DEV_EP_STORE[devid][self._interface].write_ep
        return self.DEV_EP_STORE[devid][self._interface].read_ep

    def read_ep(self, *args, **kwargs):
        """Thread safe wrapper around reading the |read_ep|"""
        self.wait_on_reset()
        with self._hold_lock(self._read_ep_lock):
            ep = self._get_ep(write=False)
            return ep.read(*args, **kwargs)

    @retry_hardware(exceptions=(usb.core.USBTimeoutError,))
    def write_ep(self, *args, **kwargs):
        """Thread safe wrapper around writing to the |write_ep|"""
        self.wait_on_reset()
        with self._hold_lock(self._write_ep_lock):
            ep = self._get_ep(write=True)
            return ep.write(*args, **kwargs)

    def control(self, request, value):
        """Send control transfer.

        Args:
          request: the request type to send, bmRequestType
          data: the data to send, wValue

        Returns:
          boolean success/fail
        """
        # usb_setup_packet: ec/include/usb_descriptor.h:231
        reqtype = (
            usb.util.CTRL_OUT
            | usb.util.CTRL_TYPE_VENDOR
            | usb.util.CTRL_RECIPIENT_INTERFACE
        )
        self._dev.ctrl_transfer(
            bmRequestType=reqtype,
            bRequest=request,
            wIndex=self._interface,
            wValue=value,
        )
        return True

    def close(self):
        """Stm32usb release."""
        if self._dev:
            usb.util.dispose_resources(self._dev)
            self._dev = None

    def __del__(self):
        """Sgpio destructor."""
        self.close()
