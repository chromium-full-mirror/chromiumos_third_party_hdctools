#!/usr/bin/env python3
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import ast
import json
import logging
import os
import time

from google.protobuf import empty_pb2
from google.protobuf import json_format

from servo import drv as servo_drv
from servo.common.proto import driver_grpc
from servo.common.proto import driver_pb2
from servo.common.utils import json_utils
from servo.common.utils import string_utils
from servo.common.utils.grpc_log_capture import LogCaptureContext
from servo.common.utils.interface_utils import InterfaceUtils
from servo.data.impl.system_config_service import get_system_config


_drv_dict_all = {}


class DriverImplError(Exception):
    """Exception class for DriverImpl."""


class InterfaceImplError(Exception):
    """Exception class for InterfaceImpl."""


class DriverImpl(driver_grpc.DriverServiceServicer):
    def __init__(self, grpc_core_addr, grpc_data_addr):
        super().__init__()
        self.grpc_core_addr = grpc_core_addr
        self.grpc_data_addr = grpc_data_addr

    def CallDriver(self, driver_request, context):
        """
            Get/Set driver value, this service inited related drivers
            inside the driver_dict

            Args:
                 driver_request (DriverRequest) : gRPC request
                 context
            Returns:
                driver get value

        Raises:
          DriverImplError: Error occurred while using drv
        """
        is_get = driver_request.WhichOneof("set_value") != "value"
        response = driver_pb2.DriverResponse()
        try:
            # interface ky for related vid, pid and serial
            interface_key = InterfaceUtils.get_interface_key(
                vid=driver_request.vid,
                pid=driver_request.pid,
                serial=driver_request.serial,
            )
            # Get system config
            syscfg = get_system_config(
                vid=driver_request.vid,
                pid=driver_request.pid,
                serial=driver_request.serial,
            )

            (params, drv, device) = self._get_param_drv(
                driver_request.control_name,
                driver_request.device_type,
                syscfg,
                interface_key,
                is_get,
            )
            if is_get:
                get_value = drv.get()
                params["response"] = syscfg.reformat_val(params, get_value)
                response.value = json_utils.dumps(params)
            else:
                value = json_format.MessageToDict(driver_request.value)
                wr_val = syscfg.resolve_val(params, value)
                drv.set(wr_val)
            response.success = True
            return response
        except Exception as e:
            # We used to capture tracebacks here, but now ExceptionTruncatingInterceptor
            # handles all gRPC exception truncation automatically at the server boundary.
            if hasattr(e, "details"):
                msg = e.details()
                if msg.startswith("Exception calling application: "):
                    msg = msg[len("Exception calling application: ") :]
                raise DriverImplError(msg.split("\n")[0])
            raise DriverImplError(str(e))

    def _get_param_drv(
        self, control_name, device_type, syscfg, interface_key, is_get=True
    ):
        """Get access to driver for a given control.

        Args:
          control_name: string name of control
          device_type: string device type
          syscfg: SystemConfig system config dict
          interface_key: string interface key in interfaces dict.
          is_get: boolean to determine

        Returns:
          tuple (params, drv, device_info) where:
            params: param dictionary for control
            drv: instance object of driver for particular control
            device_info: servo device information

        Raises:
          DriverImplError: Error occurred while examining params dict
        """

        if not interface_key in _drv_dict_all:
            _drv_dict_all[interface_key] = {}
        drv_dict = _drv_dict_all[interface_key]

        # if already setup just return tuple from driver dict
        if control_name in drv_dict:
            if is_get and ("get" in drv_dict[control_name]):
                return drv_dict[control_name]["get"]
            if not is_get and ("set" in drv_dict[control_name]):
                return drv_dict[control_name]["set"]

        set_params, get_params = syscfg.lookup_control_params(control_name)
        for params in [get_params, set_params]:
            # |cmd| is guaranteed to be in each params.
            mode = params["cmd"]
            drv_prefix = params.get("drv")
            if drv_prefix == "na":
                # 'na' drv can be used to selectively turn controls into noops for
                # a given servo hardware. Ensure that there is an interface.
                params.setdefault("interface", "servo")
                # Setting input_type to str allows all inputs through enabling a true
                # noop
                params.update({"input_type": "str"})

            interface_id = params.get("interface")

            if None in [drv_prefix, interface_id]:
                raise DriverImplError(
                    "No drv/interface for control %r found" % control_name
                )

            # Store map params in params
            map_name = params.get("map")
            if map_name is not None:
                map_params = syscfg.lookup_map_params(map_name)
                params["map_params"] = map_params

            # Store this device name in params (necessary to scope control names when
            # querying controls from a non-main servo device)
            # TODO(b/275723447): remove this parameter once prefix string is no longer
            # necessary in drivers
            params["device_type"] = device_type

            # this control only needs cross-servo-device communication and does not
            # need hardware interface for low-level communication
            if interface_id == "servo":
                interface = None
            else:
                # this control only needs hardware interface for low-level communication
                # and does not need cross-servo-device communication
                index = int(interface_id)
                _interface_list = InterfaceUtils.get_interface_list(interface_key)
                interface = _interface_list[index]

            device_info = None
            if hasattr(interface, "get_device_info"):
                device_info = interface.get_device_info()
            drv_module = getattr(servo_drv, drv_prefix)
            drv_class = getattr(drv_module, string_utils.snake_to_camel(drv_prefix))
            drv = drv_class(self.grpc_core_addr, self.grpc_data_addr, interface, params)

            if control_name not in drv_dict:
                drv_dict[control_name] = {}
            # Store the information in the right mode.
            drv_dict[control_name][mode] = (params, drv, device_info)
        # At this point, both 'set' and 'get' have been generated. The last thing
        # left to do is to pass each one of them a weak reference to the other.
        # This ensures that if a control needs to do read/modify/write for
        # instance it can do so without much overhead.
        _, set_drv, _ = drv_dict[control_name]["set"]
        _, get_drv, _ = drv_dict[control_name]["get"]
        set_drv.set_complement(get_drv)
        # Run the method again, as it will find the entries now in the cache.
        return self._get_param_drv(
            control_name, device_type, syscfg, interface_key, is_get
        )
    def InitInterface(self, request, context):
        """
        Service to init interfaces list for servo device

        Args:
            request InterfaceRequest
            context
        """
        with LogCaptureContext() as loglines:
            try:
                interfaces = ast.literal_eval(request.interface_template)
                InterfaceUtils.sync_interface_lists(
                    interfaces=interfaces,
                    vid=request.vid,
                    pid=request.pid,
                    serial=request.serial,
                )
                InterfaceUtils.init_servo_interfaces(
                    interfaces,
                    request.vid,
                    request.pid,
                    request.serial,
                    request.fault_tolerant,
                    request.token_db,
                    self.grpc_data_addr,
                )

                interface_key = InterfaceUtils.get_interface_key(
                    request.vid, request.pid, request.serial
                )
                _interface_list = InterfaceUtils.get_interface_list(interface_key)
                for interface in _interface_list:
                    pty_path = None
                    try:
                        if hasattr(interface, "get_control_pty"):
                            pty_path = interface.get_control_pty()
                        elif hasattr(interface, "get_pty"):
                            pty_path = interface.get_pty()
                    except Exception:
                        pass

                    if pty_path:
                        for _ in range(20):
                            if os.path.exists(pty_path):
                                break
                            time.sleep(0.1)

                return driver_pb2.InterfaceResponse(success=True, loglines=loglines)
            except Exception:
                logging.exception("Failed to initialize interface")
                # Assuming the interface didn't initialize properly, mark it as failure
                return driver_pb2.InterfaceResponse(success=False, loglines=loglines)

    def ReinitializeInterfaces(self, request, context):
        """
        Service to reinitialize interfaces list for servo device

        Args:
            request InterfaceRequest
            context
        """
        InterfaceUtils.reinitialize(
            vid=request.vid, pid=request.pid, serial=request.serial
        )
        return empty_pb2.Empty()

    def CloseInterface(self, request, context):
        """
        Service to reinitialize interfaces list for servo device

        Args:
            request InterfaceRequest
            context
        """
        interface_key = InterfaceUtils.get_interface_key(
            request.vid, request.pid, request.serial
        )
        InterfaceUtils.close_interface(interface_key)
        return empty_pb2.Empty()

    def SetInterfacesLoglevel(self, request, context):
        """
        Service to reinitialize interfaces list for servo device

        Args:
            request InterfaceRequest
            context
        """
        InterfaceUtils.set_interface_loglevel(new_level=request.name)
        return empty_pb2.Empty()

    def SyncInterfaceList(self, request, context):
        """
        Service to reinitialize interfaces list for servo device

        Args:
            request InterfaceRequest
            context
        """
        InterfaceUtils.sync_interface_lists(
            interfaces=request.interface_template,
            serial=request.serial,
            pid=request.pid,
            vid=request.vid,
        )
        return empty_pb2.Empty()

    def SetFtdii2cCmd(self, request, context):
        """
        Service to set ftdii2c cmd

        Args:
            request InterfaceRequest
            context
        """
        InterfaceUtils.set_interface_ftdii2c(request.cmd)
        return empty_pb2.Empty()

    def ResetInterfaceRequest(self, request, context):
        """
        Service to reset interface init

        Args:
            request InterfaceRequest
            context
        """
        interface_key = InterfaceUtils.get_interface_key(
            vid=request.vid, pid=request.pid, serial=request.serial
        )
        InterfaceUtils.reset_interface_init(interface_key, request.interface_index)
        return empty_pb2.Empty()

    def LimitEcDriverChannel(self, request, context):
        # interface key for related vid, pid and serial
        interface_key = InterfaceUtils.get_interface_key(
            vid=request.vid,
            pid=request.pid,
            serial=request.serial,
        )

        # Get system config
        syscfg = get_system_config(
            vid=request.vid, pid=request.pid, serial=request.serial
        )
        is_get = True

        (_, drv, _) = self._get_param_drv(
            request.control_name,
            request.device_type,
            syscfg,
            interface_key,
            is_get,
        )

        drv._limit_channel()
        return empty_pb2.Empty()

    def RestoreEcDriverChannel(self, request, context):
        # interface key for related vid, pid and serial
        interface_key = InterfaceUtils.get_interface_key(
            vid=request.vid,
            pid=request.pid,
            serial=request.serial,
        )

        # Get system config
        syscfg = get_system_config(
            vid=request.vid, pid=request.pid, serial=request.serial
        )
        is_get = True

        (_, drv, _) = self._get_param_drv(
            request.control_name,
            request.device_type,
            syscfg,
            interface_key,
            is_get,
        )

        drv._restore_channel()
        return empty_pb2.Empty()

    def IssueCmdGetResults(self, request, context):
        # interface key for related vid, pid and serial
        interface_key = InterfaceUtils.get_interface_key(
            vid=request.vid,
            pid=request.pid,
            serial=request.serial,
        )

        # Get system config
        syscfg = get_system_config(
            vid=request.vid, pid=request.pid, serial=request.serial
        )
        is_get = True

        (_, drv, _) = self._get_param_drv(
            "ec_gpio",
            request.device_type,
            syscfg,
            interface_key,
            is_get,
        )

        drv._issue_cmd_get_results(
            request.cmds,
            request.regex_list,
            request.flush,
            request.time_out,
        )

        return empty_pb2.Empty()

    def CheckDevice(self, request, context):
        import os

        from google.protobuf import wrappers_pb2
        exists = os.path.exists(request.sysfs_path)
        return wrappers_pb2.BoolValue(value=exists)
