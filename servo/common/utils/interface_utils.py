# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import logging

from servo.common import interface as _interface
from servo.common.interface import ftdii2c


class InterfaceUtilsError(Exception):
    """Error class for interface utils"""


class InterfaceUtils:
    """
    Interface utils for init interfaces
    """

    # interfaces
    _interface_dict = {}
    _logger = logging.getLogger("InterfaceUtils")

    @staticmethod
    def get_interface_key(vid, pid, serial):
        """
        Generate a unique interface key based on the provided parameters.

        Args:
        - vid (str): Vendor ID.
        - pid (str): Product ID.
        - serial (str): Serial number.

        Returns:
        str: A unique interface key combining the provided
             parameters in the format "vid_pid_serial".
        """
        return "{}_{}_{}".format(vid, pid, serial)

    @staticmethod
    def sync_interface_lists(interfaces, vid, pid, serial):
        """Ensure when interfaces are changed, bookkeeping is kept in sync.

        Args:
          - interfaces (list): Interfaces template.
          - vid (str): Vendor ID.
          - pid (str): Product ID.
          - serial (str): Serial number.
        """
        interface_key = InterfaceUtils.get_interface_key(vid, pid, serial)
        InterfaceUtils.init_interface_dict(vid, pid, serial)
        interface_list = InterfaceUtils._interface_dict[interface_key]["interface_list"]
        interface_init = InterfaceUtils._interface_dict[interface_key]["interface_init"]
        # Extend the interface list if we need to.
        interfaces_len = len(interfaces)
        interface_list_len = len(interface_list)
        if interfaces_len > interface_list_len:
            interface_list += [_interface.empty.Empty()] * (
                interfaces_len - interface_list_len
            )
            interface_init += [False] * (interfaces_len - interface_list_len)

    @staticmethod
    def init_servo_interfaces(
        interfaces, 
        vid, 
        pid, 
        serial, 
        fault_tolerant=False, 
        token_db=None
    ):
        """Init the servo interfaces with the given interfaces.

        Args:
          interfaces (list): Interfaces template.
          pid: Product id
          vid: Vendor ID
          serial: serial
          fault_tolerant: If True, initialization error on an interface is logged but
                          not result in an exception. If false, initialization error on
                          any interface leads to an exception.

        Raises:
          ServoDeviceError: if unable to locate init method for particular interface.
        """
        interface_key = InterfaceUtils.get_interface_key(vid, pid, serial)
        InterfaceUtils.init_interface_dict(vid, pid, serial)
        interface_list = InterfaceUtils._interface_dict[interface_key]["interface_list"]
        interface_init = InterfaceUtils._interface_dict[interface_key]["interface_init"]

        for i, interface_data in enumerate(interfaces):
            if interface_init[i]:
                # Ensure initialized interfaces are not reinitialized
                continue
            if isinstance(interface_data, dict):
                name = interface_data["name"]
                # Store interface index for those that care about it.
                interface_data["index"] = i
            elif isinstance(interface_data, str):
                if interface_data in ["empty", "ftdi_empty"]:
                    # 'empty' reserves the interface for future use.  Typically the
                    # interface will be managed by external third-party tools like
                    # openOCD for JTAG or flashrom for SPI.  In the case of servo V4,
                    # it serves as a placeholder for servo micro interfaces.
                    continue
                name = interface_data
            else:
                raise TypeError("Illegal interface data type %s" % type(interface_data))
            InterfaceUtils._logger.error("Initializing interface %d to %s", i, name)
            try:
                result = _interface.Build(
                    name=name,
                    index=i,
                    vid=vid,
                    pid=pid,
                    sid=serial,
                    interface_data=interface_data,
                    servo_device=None,
                    token_db=token_db,
                )
            except Exception:
                if fault_tolerant:
                    InterfaceUtils._logger.warning(
                        "Failure trying to initialize interface %s (%s) "
                        "in fault toleratant mode, so this will not crash servod.",
                        i,
                        name,
                    )
                    continue
                raise
            if isinstance(result, tuple):
                result_len = len(result)
                interface_list[i : (i + result_len)] = result
                interface_init[i : (i + result_len)] = True
            else:
                interface_list[i] = result
                interface_init[i] = True

    @staticmethod
    def get_interface_list(interface_key):
        """
        Get interface_list.

        Args:
            interface_key: (string) a combination of vid, pid and serial

        return:
            interface_list
        """
        interface_list = InterfaceUtils._interface_dict[interface_key]["interface_list"]
        return interface_list

    @staticmethod
    def get_init_list(interface_key):
        """
        Get interface_init.

        Args:
            interface_key: (string) a combination of vid, pid and serial

        return:
            interface_init
        """
        interface_init = InterfaceUtils._interface_dict[interface_key]["interface_init"]
        return interface_init

    @staticmethod
    def init_interface_dict(vid, pid, serial):
        """
        Initialize the interface dictionary with a unique key
        based on the provided parameters.

        Args:
        - vid (str): Vendor ID.
        - pid (str): Product ID.
        - serial (str): Serial number
        """
        interface_key = InterfaceUtils.get_interface_key(vid, pid, serial)

        if interface_key not in InterfaceUtils._interface_dict:
            InterfaceUtils._interface_dict[interface_key] = {
                "interface_list": [],
                "interface_init": [],
            }

    @staticmethod
    def reinitialize():
        """Reinitialize the interfaces based on the provided VID, PID, and serial."""
        interface_dict = InterfaceUtils._interface_dict
        for device in interface_dict:
            interface_list = interface_dict[device]["interface_list"]
            for _unused, interface in enumerate(interface_list):
                interface.reinitialize()

    @staticmethod
    def close_interfaces():
        """InterfaceUtilsError
        Close interfaces based on the provided VID, PID, and serial.
        """
        interface_dict = InterfaceUtils._interface_dict
        for device in interface_dict:
            interface_list = interface_dict[device]["interface_list"]
            # Close ec3po interfaces first to remove
            # all wrappers/pointers on the raw pty
            for i, interface in enumerate(interface_list):
                if isinstance(interface, _interface.ec3po_interface.EC3PO):
                    InterfaceUtils._logger.info("Turning down interface %d", i)
                    interface.close()

            # Close all the other non-placeholder interfaces
            for i, interface in enumerate(interface_list):
                if not isinstance(interface, _interface.empty.Empty) and not isinstance(
                    interface, _interface.ec3po_interface.EC3PO
                ):
                    # Only print this on real interfaces and not place holders.
                    InterfaceUtils._logger.info("Turning down interface %d", i)
                    interface.close()

    @staticmethod
    def set_interface_loglevel(new_level):
        """Set loglevel for interfaces"""
        interface_dict = InterfaceUtils._interface_dict
        for device in interface_dict:
            interface_list = interface_dict[device]["interface_list"]
            for _unused, interface in interface_list:
                if isinstance(interface, _interface.ec3po_interface.EC3PO):
                    interface.set_loglevel(new_level)

    @staticmethod
    def set_interface_ftdii2c(cmd):
        """Set cmd for ftdii2c interface"""
        logger = logging.getLogger("InterfaceUtil")
        _ftdii2c = None
        interface_dict = InterfaceUtils._interface_dict
        for device in interface_dict:
            interface_list = interface_dict[device]
            for _unused, interface in interface_list:
                if isinstance(interface, ftdii2c.Fi2c):
                    _ftdii2c = interface
                    break
            else:
                raise InterfaceUtilsError("No ftdi_i2c object found.")
        try:
            func = getattr(_ftdii2c, cmd)
        except AttributeError:
            raise InterfaceUtilsError("ftdi_i2c object does not have method %r" % cmd)
        logger.debug("Running %s on ftdii2c interface.", cmd)
        func()
