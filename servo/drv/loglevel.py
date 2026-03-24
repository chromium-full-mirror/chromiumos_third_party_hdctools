# Copyright 2016 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver for servod's loglevel."""

import logging

from servo.common.grpc_client import GrpcClient
import servo.common.interface.ec3po_interface
from servo.common.proto import driver_grpc
from servo.common.utils import servo_logging
from servo.drv import hw_driver


class loglevel(hw_driver.HwDriver):
    """Class to access loglevel controls."""

    def _drv_init(self):
        """Initializes the loglevel driver."""
        # Create a gRPC channel to the specified host and port
        grpc_data_host, grpc_data_port = self.grpc_data_addr
        channel = GrpcClient.create_grpc_channel(grpc_data_host, grpc_data_port)
        self._data_client = driver_grpc.DriverService(channel)

    def _set(self, new_level):
        """Changes the current loglevel of the root logger.

        Args:
          new_level: A string containing the new desired log level.

        Raises:
          HwDriverError if passed in an invalid logging level name.
        """
        new_level = new_level.lower()
        root_logger = logging.getLogger()

        try:
            level, fmt_string = servo_logging.LOGLEVEL_MAP[new_level]
        except KeyError:
            raise hw_driver.HwDriverError(
                "Unknown logging level. "
                "(known: critical, error, warning,"
                " info, or debug)"
            )
        out_handlers = [
            handler
            for handler in root_logger.handlers
            if not isinstance(handler, servo_logging.ServodRotatingFileHandler)
        ]
        # Set servod's stdout logging level.
        if len(root_logger.handlers) == 1:
            # In this case, servod is logging with basicConfig i.e. the handler
            # is not the gate-keeper, but rather the root logger itself.
            root_logger.setLevel(level)
            # Set EC-3PO's logging level. This is only relevant when filtering through
            # the root-logger and not through the handlers.
            self._data_client.SetInterfacesLoglevel(name=new_level)
        else:
            for handler in out_handlers:
                handler.setLevel(level)
        # Irrespective of basicConfig or handler based logging, the
        # standard handlers need to be reset for this format.
        for handler in out_handlers:
            handler.setFormatter(servo_logging.UTCFormatter(fmt=fmt_string))

    def _get(self):
        """Gets the current loglevel of the root logger."""
        root_logger = logging.getLogger()
        if len(root_logger.handlers) == 1:
            # In this case, servod is logging with basicConfig i.e. the handler
            # is not the gate-keeper, but rather the root logger itself.
            cur_level = root_logger.level
        else:
            for handler in root_logger.handlers:
                # The loglevel is the level of any handler that is not the Servod
                # handler as that one is always on debug.
                if not isinstance(handler, servo_logging.ServodRotatingFileHandler):
                    # The file logger is always DEBUG and cannot be changed.
                    cur_level = handler.level
                    break
            else:
                raise hw_driver.HwDriverError(
                    "Root logger has no output handlers "
                    "besides potentially the "
                    "ServodRotatingFileHandler"
                )
        return logging.getLevelName(cur_level).lower()
