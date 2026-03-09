# Copyright 2011 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Base class for servo drivers."""

import logging
import re
import weakref

from servo.common.exceptions import HwDriverError
from servo.common.grpc_client import GrpcClient
from servo.common.proto import servo_dev_grpc
from servo.common.utils import json_utils
from servo.utils.retry_util import retry_hardware


VALID_IO_TYPES = ["PU", "PP"]


def _get_io_type(params):
    """Retrieve IO driver type.

    Valid driver types are:
      PU == Pull-up
      PP == Push-pull

    Returns: string either 'PP' or 'PU'

    Raises: HwDriverError if:
       io type is invalid
       controls width > 1
    """
    if "od" in params:
        width = params.get("width", 1)
        if width > 1:
            raise HwDriverError("Open drain not implemented for widths != 1")
        io_type = params["od"].upper()
        if io_type not in VALID_IO_TYPES:
            raise HwDriverError("Unrecognized io type (param 'od') %s" % io_type)
        return io_type
    return False


class HwDriver:
    """Base class for all hardware drivers."""

    # The list of params that an overlay needs to specific for the drv to be
    # effective. By default, that list is empty, though a drv implementation
    # can simply overwrite them.
    # Should a drv require different params for set and get, make sure that
    # 1. the drv uses the type specific |REQUIRED_GET_PARAMS| and
    # |REQUIRED_SET_PARAMS| and
    # 2. the overlay contains the right 'cmd' for each of them, or follows the cmd
    # convention for single-params controls.
    # If both set and get use the same required params, simplify define one and
    # set the other to that definition.
    REQUIRED_GET_PARAMS = []
    REQUIRED_SET_PARAMS = []

    def __init__(self, grpc_core_addr, grpc_data_addr, interface, params):
        """Driver constructor.

        Args:
          interface: FTDI interface object to handle low-level communication to
              control
          params: dictionary of params needed to perform operations on gpio driver

              params dictionary can have k=v pairs necessary to communicate with the
              underlying hardware.  Notables are:
                width: integer of width of the control in bits.
                    Default: 1
                offset: integer of position of bit(s) with respect to lsb.
                    Default: 0
                map: name string of map dictionary to use for unmapping / remapping
                fmt: function name string to call to format the result.

             Additional param keys will be described in sub-class drivers.
          servod: Servod object to handle cross-servo-device communication

        Attributes:
          _logger: logger object.  May be accessed via sub-class
          _complement: a weak reference to the complement drv e.g. the controls'
                       set implementation if this is a get implementation.
          _interface: interface object.  May be accessed via sub-class
          _params: parameter dictionary.  May be accessed via sub-class
          _io_type: String of io type or False if not explicitly assigned.
        """
        self._logger = logging.getLogger(type(self).__name__)

        self._complement = None
        self._interface = interface
        self._servod = None
        self._params = params
        # Check whether all required params are provided. if 'cmd' is in params,
        # use a type-specific |REQUIRED_PARAMS| e.g. set or get. If not, use the
        # generic one.
        cmd = self._params["cmd"]
        if cmd == "get":
            req_params = self.REQUIRED_GET_PARAMS
        elif cmd == "set":
            req_params = self.REQUIRED_SET_PARAMS
        # The cmd is invalid here, raise an error. While this doesn't necessarily
        # cause an issue, we do not want config files laying around that misuse
        # cmd.
        else:
            raise HwDriverError("'cmd' param %r unknown. Use 'set' or 'get'" % (cmd,))
        for a in req_params:
            # Empty |req_params| leads to no checks being performed.
            if a not in self._params:
                raise HwDriverError("Required param %r not in params" % (a,))
        # |set| cmd might define choices that show what are valid choices to be
        # set.
        self._choices = None
        if "choices" in self._params:
            self._choices = re.compile(self._params["choices"])
            self._logger.debug("Valid input choices: %s", self._choices)
        self._io_type = _get_io_type(params)
        self._prefix = self._params.get("interface_prefix")
        # Create a gRPC channel to the specified host and port
        self.grpc_core_addr = grpc_core_addr
        self.grpc_data_addr = grpc_data_addr
        if grpc_core_addr:
            grpc_core_host, grpc_core_port = grpc_core_addr
            channel = GrpcClient.create_grpc_channel(grpc_core_host, grpc_core_port)
            self._logger.debug("Connect to grpc server of core.....")
            self._driver_client = servo_dev_grpc.ServoService(channel)
        else:
            self._driver_client = None

        self._drv_init()

    def _drv_init(self):
        """Subclasses may override this to perform custom initialization.

        The attributes documented in __init__() will be available when this is
        called.

        **Do** use super() to call this base class implementation, in case it
        gains functionality in the future.
        """

    def __str__(self):
        """Return a string representation of this drv."""
        return "%s[%s](%s)" % (
            self._params["control_name"],
            type(self).__name__,
            self._mode(),
        )

    def _servod_get(self, control):
        """Get the value of the given control with proper prefix."""
        service = self._driver_client.GetServo(control_name=control)
        return service.response

    def _servod_set(self, control, value):
        """Set the value of the given control with proper prefix."""
        val_pb = json_utils.wrap_value(value)
        self._driver_client.SetServo(control_name=control, value=val_pb)

    def _servod_has_control(self, control):
        """Check if servod has a control with specified name"""
        return self._driver_client.HasControl(control_name=control).value

    def __repr__(self):
        """Return same as __str__()"""
        return str(self)

    def _is_set(self):
        """Whether the |self| is a driver instance for 'set'.

        Returns:
          True if 'cmd' is 'set'
        """
        return self._mode() == "set"

    def _is_get(self):
        """Whether the |self| is a driver instance for 'get'.

        Returns:
          True if 'cmd' is 'get'
        """
        return self._mode() == "get"

    def _mode(self):
        """Mode of this drv, either 'set' or 'get'.

        Returns:
          contents of self._params['cmd']
        """
        return self._params["cmd"]

    def set_complement(self, complement_drv):
        """set |complement_drv| to this drv's complement and vice-versa

        Args:
          complement_drv: this control drv's complement

        Raises:
          HwDriverError: if |complement_drv| and |self| have the same mode (set,get)
          HwDriverError: if |complement_drv| or |self| already have a complement
        """
        # pylint: disable=protected-access
        # Access required as the goal is to link both the classes.
        if complement_drv._mode() == self._mode():
            raise HwDriverError(
                "Cannot set %r as the complement of %r." % (complement_drv, self)
            )

        # Note: this policy can be changed if necessary, but for now it seems safer
        # to enforce that complements are set once. There is no known reason so far
        # to have a complement drv dynamically change at runtime after the first
        # time it is set. If this is changed in the future, consider that we do
        # not want to have open loops i.e. if a complement is cleaned up, it needs
        # to be cleaned up from both sides.
        for d in [self, complement_drv]:
            if d._complement is not None:
                # |d._complement| is a weakref. Casting it to a string before passing it
                # to %r ensures it prints the actual object class and not that it's
                # a weakref.
                raise HwDriverError(
                    "drv %r already has a complement: %r" % (d, str(d._complement))
                )

        self._complement = weakref.proxy(complement_drv)
        complement_drv._complement = weakref.proxy(self)
        # |self._complement| is a weakref. Casting it to a string before passing it
        # to %r ensures it prints the actual object class and not that it's a
        # weakref.
        self._logger.debug(
            "Set drvs %r and %r as each others complements.",
            self,
            str(self._complement),
        )

    def _get_complement(self):
        """Return the complement drv.

        Returns:
          self._complement i.e. the complement drv. Can be None if not set yet.
        """
        return self._complement

    def _check_input(self, value):
        """Check whether |value| is a valid input.

        If |self._choices| is defined, then |value| has to match.

        Args:
          value: value to check

        Raises:
          HwDriverError: if |self._choices| is defined and value does not match.
        """
        if self._choices and self._choices.match(str(value)) is None:
            raise HwDriverError(
                "%r not a valid input choice (%r)" % (value, self._choices.pattern)
            )

    @retry_hardware()
    def set(self, logical_value):
        """Set hardware control to a particular value.

        This function first check that |logical_value| is a valid choice before
        passing it down. Then, it tries to set the value:
        1. If `subtype` is specified in the self._params, run _Set_[subtype]()
        2. Otherwise, run _set()

        DO NOT OVERRIDE THIS METHOD in the subclass. Instead, override _set().

        Args:
          logical_value: Integer value to write to hardware.

        Returns:
          Value from _Set_[subtype]() or _set()

        Raises:
          HwDriverError: If unable to locate _Set_[subtype]() method.
        """
        self._logger.debug("logical_value = %s", logical_value)
        self._check_input(logical_value)
        if "subtype" in self._params:
            if self._params["subtype"] == "":
                raise HwDriverError(
                    "Subtype should not be empty. \
          Please remove subtype param if it is unnecessary."
                )
            fn_name = "_Set_%s" % self._params["subtype"]
            if hasattr(self, fn_name):
                return getattr(self, fn_name)(logical_value)
            self._logger.warning(
                "Cannot find set subtype function %s. \
        Fall back to general set function."
                % (fn_name,)
            )
        return self._set(logical_value)

    def _set(self, logical_value):
        """Set the control to |logical_value|.

        Args:
          logical_value: Integer value to write to hardware.

        Returns:
          Value from subclass method.

        Raises:
          NotImplementedError: _set() unimplemented in the subclass.
        """
        raise NotImplementedError("_set should be implemented in subclass.")

    @retry_hardware()
    def get(self):
        """Get hardware control to a particular value.

        This function tries to get the value:
        1. If `subtype` is specified in the self._params, run _Get_[subtype]()
        2. Otherwise, run _get()

        DO NOT OVERRIDE THIS METHOD in the subclass. Instead, override _get().

        Returns:
          Value from _Get_[subtype]() or _get()

        Raises:
          HwDriverError: If unable to locate _Get_[subtype]() method.
        """
        if "subtype" in self._params:
            if self._params["subtype"] == "":
                raise HwDriverError(
                    "Subtype should not be empty. \
          Please remove subtype param if it is unnecessary."
                )
            fn_name = "_Get_%s" % self._params["subtype"]
            if hasattr(self, fn_name):
                return getattr(self, fn_name)()
            self._logger.warning(
                "Cannot find get subtype function %s. \
        Fall back to general get function."
                % fn_name
            )
        return self._get()

    def _get(self):
        """Get the control.

        Returns:
          Value from subclass method.

        Raises:
          NotImplementedError: _get() unimplemented in the subclass.
        """
        raise NotImplementedError("_get method should be implemented in subclass.")

    def _create_logical_value(self, hw_value):
        """Create logical value using mask & offset.

        logical_value = (hw_value & mask) >> offset

        In MOST cases, subclass drivers should use this for data coming back from
        get method.

        Args:
          hw_value: value to convert to logical value

        Returns:
          integer in logical representation
        """
        (offset, mask) = self._get_offset_mask()
        if offset is not None:
            # Handle float-represented integers from gRPC/JSON.
            hw_value = json_utils.ensure_int(hw_value)
            fmt_value = (hw_value & mask) >> offset
        else:
            fmt_value = hw_value
        return fmt_value

    def _create_hw_value(self, logical_value):
        """Create hardware value using mask & offset.

        hw_value = (logical_value << offset) & mask

        In MOST cases, subclass drivers should use this for data going to value
        argument in set method.

        Args:
          logical_value: value to convert to hardware value

        Returns:
          integer in hardware representation

        Raises:
          HwDriverError: when logical_value would assert bits outside the mask
        """
        (offset, mask) = self._get_offset_mask()
        if offset is not None:
            # Handle float-represented integers from gRPC/JSON.
            logical_value = json_utils.ensure_int(logical_value)
            hw_value = (logical_value << offset) & mask
            if hw_value != (hw_value & mask):
                raise HwDriverError("format value asserts bits outside mask")
        else:
            hw_value = logical_value
        return hw_value

    def _get_offset_mask(self):
        """Retrieve offset and mask.

        Subclasses should use to obtain &| create these ints from param dict

        Returns:
          tuple (offset, mask) where:
            offset: integer offset or None if not defined in param dict
            mask: integer mask or None if offset not defined in param dict
          For example if width=2 and offset=4 then mask=0x30

        """
        if "offset" in self._params:
            offset = int(self._params["offset"])
            if "width" not in self._params:
                mask = 1 << offset
            else:
                mask = (pow(2, int(self._params["width"])) - 1) << offset
        else:
            offset = None
            mask = None
        return (offset, mask)
