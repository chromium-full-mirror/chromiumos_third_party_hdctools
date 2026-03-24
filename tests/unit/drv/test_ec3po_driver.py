# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import unittest.mock
from unittest.mock import MagicMock
from unittest.mock import patch

from servo.drv.ec3po_driver import ec3poDriver
from servo.drv.ec3po_driver import NO_UART_ERR


class TestEs3poDriver(unittest.TestCase):
    """
    Unit test class for relaySwitch
    """

    def setUp(self):
        self.mock_interface = MagicMock()
        self.mock_logger = MagicMock()
        self.instance = ec3poDriver(
            grpc_core_addr=("localhost", 9999),
            grpc_data_addr=("localhost", 9999),
            interface=self.mock_interface,
            params={"cmd": "set"},
        )
        self.instance._logger = self.mock_logger

    def test_set_interp_connect_no_uart(self):
        with patch.object(self.instance, "_interface", None):
            self.instance._Set_interp_connect(state=True)
            self.mock_logger.debug.assert_called_with(NO_UART_ERR)

    def test_set_interp_connect(self):
        self.mock_interface.set_interp_connect.return_value = None
        self.instance._Set_interp_connect(state=True)
        self.mock_interface.set_interp_connect.assert_called_with(True)

    def test_get_interp_connect_with_valid_interface(self):
        self.instance._interface.get_interp_connect.return_value = "on"
        result = self.instance._Get_interp_connect()
        self.assertEqual(result, "on")

    def test_get_interp_connect_with_none_interface(self):
        with patch.object(self.instance, "_interface", None):
            result = self.instance._Get_interp_connect()
            self.assertIsNone(result)
            self.mock_logger.debug.assert_called_with(NO_UART_ERR)

    def test_set_loglevel_with_valid_interface(self):
        self.instance._Set_loglevel(level="debug")
        self.mock_interface.set_loglevel.assert_called_with("debug")

    def test_set_loglevel_with_none_interface(self):
        self.instance._interface = None
        self.instance._Set_loglevel(level="debug")
        self.mock_logger.debug.assert_called_with(NO_UART_ERR)

    def test_set_timestamp_with_valid_interface(self):
        self.instance._Set_timestamp(state=True)
        self.mock_interface.set_timestamp.assert_called_with(True)

    def test_set_timestamp_with_none_interface(self):
        self.instance._interface = None
        self.instance._Set_timestamp(state=True)
        self.mock_logger.debug.assert_called_with(NO_UART_ERR)

    def test_get_timestamp_with_valid_interface(self):
        self.instance._interface.get_timestamp.return_value = 1
        result = self.instance._Get_timestamp()
        self.assertEqual(result, 1)

    def test_get_timestamp_with_none_interface(self):
        self.instance._interface = None
        result = self.instance._Get_timestamp()
        self.assertIsNone(result)
        self.mock_logger.debug.assert_called_with(NO_UART_ERR)

    def test_set_raw_debug_with_none_interface(self):
        self.instance._interface = None
        self.instance._Set_raw_debug(state=True)
        self.mock_logger.debug.assert_called_with(NO_UART_ERR)

    def test_get_raw_debug_with_valid_interface(self):
        self.instance._interface._console.raw_debug = True
        result = self.instance._Get_raw_debug()
        self.assertEqual(result, 1)

    def test_get_raw_debug_with_none_interface(self):
        self.instance._interface = None
        result = self.instance._Get_raw_debug()
        self.assertIsNone(result)
        self.mock_logger.debug.assert_called_with(NO_UART_ERR)
