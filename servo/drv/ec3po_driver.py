# Copyright 2015 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""EC-3PO Servo Driver."""

import logging

from servo.drv import hw_driver


NO_UART_ERR = "There is no UART on this servo for this specific interface."


class ec3poDriver(hw_driver.HwDriver):
    def _drv_init(self):
        """Driver specific initializer."""
        super()._drv_init()
        self._logger = logging.getLogger("EC3PO Driver")

    def _Set_interp_connect(self, state):
        """Set the interpreter's connection state to the UART.

        Args:
          state: A boolean indicating whether to connect or disconnect the
            interpreter from the UART if the interface is valid.
        """
        if self._interface is not None:
            self._interface.set_interp_connect(state)
        else:
            # Fail silently for now.  A NoneType interface indicates that this
            # interface is not supported on the current servo host.  There's not much
            # we can really do.
            self._logger.debug(NO_UART_ERR)

    def _Get_interp_connect(self):
        """Get the state of the interpreter connection to the UART.

        Returns:
          A string, either 'on' or 'off', indicating the connection state of the
            interpreter if the interface is valid.
        """
        if self._interface is not None:
            return self._interface.get_interp_connect()
        else:
            # Fail silently for now.  A NoneType interface indicates that this
            # interface is not supported on the current servo host.  There's not much
            # we can really do.
            self._logger.debug(NO_UART_ERR)

    def _Set_loglevel(self, level):
        """Set the interpreter's loglevel.

        Args:
          loglevel: a logging level string 'debug', 'info', 'warning', 'error',
                    'critical'
        """
        if self._interface is not None:
            self._interface.set_loglevel(level)
        else:
            # Fail silently for now.  A NoneType interface indicates that this
            # interface is not supported on the current servo host.  There's not much
            # we can really do.
            self._logger.debug(NO_UART_ERR)

    def _Get_loglevel(self):
        """Get the interpreter's loglevel.

        Returns:
          loglevel: a logging level string 'debug', 'info', 'warning', 'error',
                    'critical'
        """
        if self._interface is not None:
            return self._interface.get_loglevel()
        else:
            # Fail silently for now.  A NoneType interface indicates that this
            # interface is not supported on the current servo host.  There's not much
            # we can really do.
            self._logger.debug(NO_UART_ERR)

    def _Set_timestamp(self, state):
        """Enable timestamps on the console

        Args:
          state: A boolean indicating whether to add timestamps to the console
            output.
        """
        if self._interface is not None:
            self._interface.set_timestamp(state)
        else:
            # Fail silently for now.  A NoneType interface indicates that this
            # interface is not supported on the current servo host.  There's not much
            # we can really do.
            self._logger.debug(NO_UART_ERR)

    def _Get_timestamp(self):
        """Get whether timestamps are enabled on the console.

        Returns:
          1 if timestamps are on. 0 if timestamps are off.
        """
        if self._interface is not None:
            return self._interface.get_timestamp()
        else:
            # Fail silently for now.  A NoneType interface indicates that this
            # interface is not supported on the current servo host.  There's not much
            # we can really do.
            self._logger.debug(NO_UART_ERR)

    def _Set_raw_debug(self, state):
        """Enable raw_debug on the console

        Args:
          state: A boolean indicating whether to turn on raw debug on the console.
        """
        if self._interface is not None:
            mode = b"on" if state else b"off"
            self._logger.debug("EC3PO raw debug set to: %r", mode)
            # Make sure that only bytes are passed on to the oobm_queue
            self._interface._console.oobm_queue.put(b"rawdebug %s" % mode)
        else:
            # Fail silently for now.  A NoneType interface indicates that this
            # interface is not supported on the current servo host.  There's not much
            # we can really do.
            self._logger.debug(NO_UART_ERR)

    def _Get_raw_debug(self):
        """Get whether raw debug is enabled on the console.

        Returns:
          A string, either 'on' or 'off', indicating if raw debug enabled.
        """
        if self._interface is not None:
            return int(self._interface._console.raw_debug)
        else:
            # Fail silently for now.  A NoneType interface indicates that this
            # interface is not supported on the current servo host.  There's not much
            # we can really do.
            self._logger.debug(NO_UART_ERR)
