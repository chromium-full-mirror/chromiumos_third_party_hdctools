# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import logging

from servo.common import interface as _interface
from servo.common.interface import ftdii2c
from servo.utils import usb_hierarchy


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
        token_db=None,
        grpc_data_addr=None,
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
            InterfaceUtils._logger.info("Initializing interface %d to %s", i, name)
            try:
                result = _interface.build(
                    name=name,
                    index=i,
                    vid=vid,
                    pid=pid,
                    sid=serial,
                    interface_data=interface_data,
                    servo_device=None,
                    token_db=token_db,
                    grpc_data_addr=grpc_data_addr,
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
            InterfaceUtils._logger.info(
                "Interface %d initialized: %s", i, interface_list[i]
            )

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
    def reinitialize(vid=None, pid=None, serial=None):
        """Reinitialize the interfaces based on the provided VID, PID, and serial.

        Args:
            vid (int): Vendor ID.
            pid (int): Product ID.
            serial (str): Serial number.
        """
        interface_key = None
        if vid and pid and serial:
            interface_key = InterfaceUtils.get_interface_key(vid, pid, serial)

        if interface_key:
            if interface_key not in InterfaceUtils._interface_dict:
                InterfaceUtils._logger.warning(
                    "Reinitialize requested for unknown device: %s", interface_key
                )
                return
            interface_list = InterfaceUtils._interface_dict[interface_key][
                "interface_list"
            ]
            for interface in interface_list:
                interface.reinitialize()
        else:
            # Reinitialize ALL interfaces if no specific device is provided.
            # This is primarily for backward compatibility or global resets.
            interface_dict = InterfaceUtils._interface_dict
            for device_key in interface_dict:
                interface_list = interface_dict[device_key]["interface_list"]
                for interface in interface_list:
                    try:
                        interface.reinitialize()
                    except usb_hierarchy.HierarchyError as e:
                        InterfaceUtils._logger.info(
                            "Ignoring failed re-initialization for %s. error(%s).",
                            device_key,
                            e,
                        )

    @staticmethod
    def close_interface(interface_key):
        """Close interfaces based on the provided VID, PID, and serial."""
        interface_dict = InterfaceUtils._interface_dict

        if interface_key not in interface_dict:
            InterfaceUtils._logger.debug(
                "Missing interface: %s (ignoring close request)", interface_key
            )
            return

        device = interface_dict[interface_key]
        interface_list = device["interface_list"]
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

        del interface_dict[interface_key]

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
        except AttributeError as exc:
            raise InterfaceUtilsError(
                "ftdi_i2c object does not have method %r" % cmd
            ) from exc
        logger.debug("Running %s on ftdii2c interface.", cmd)
        func()

    @staticmethod
    def reset_interface_init(interface_key, index):
        """
            Marked interface as not initialized

        Args:
            interface_key: (string) a combination of vid, pid and serial
            index: interface index

        return:
            interface_init
        """
        InterfaceUtils._interface_dict[interface_key]["interface_init"][index] = False
