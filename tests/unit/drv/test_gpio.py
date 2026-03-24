# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import unittest.mock
from unittest.mock import MagicMock
from unittest.mock import patch

from servo.drv.gpio import gpio
from servo.drv.gpio import gpioError


class TestGpio(unittest.TestCase):
    def setUp(self):
        self.mock_interface = MagicMock()
        self.mock_logger = MagicMock()
        self.params = {
            "cmd": "set",
            "offset": 0,
            "chip": "gpiochip0",
            "muxfile": "/sys/class/gpio/gpiochip0",
        }
        self.instance = gpio(
            grpc_core_addr=("localhost", 9999),
            grpc_data_addr=("localhost", 9999),
            interface=self.mock_interface,
            params=self.params,
        )

    @patch("servo.drv.gpio.gpio._get_common_params")
    def test_get(self, mock_get_common_params):
        mock_get_common_params.return_value = (0, 1)
        self.mock_interface.gpio_wr_rd.return_value = 1

        result = self.instance._get()

        self.assertEqual(result, 1)
        self.mock_interface.gpio_wr_rd.assert_called_with(0, 1)

    @patch("servo.drv.gpio.gpio._get_common_params")
    def test_set(self, mock_get_common_params):
        mock_get_common_params.return_value = (0, 1)
        self.mock_interface.gpio_wr_rd.return_value = 1
        self.instance._io_type = "PU"

        self.instance._set(1)

        self.mock_interface.gpio_wr_rd.assert_called_with(0, 1, 0, 1)

    def test_get_common_params(self):
        result = self.instance._get_common_params()

        self.assertEqual(result, (0, 1))

    def test_get_common_params_no_offset(self):
        del self.params["offset"]
        with self.assertRaises(gpioError):
            self.instance._get_common_params()

    def test_get_common_params_invalid_offset(self):
        self.params["offset"] = "invalid"
        with self.assertRaises(gpioError):
            self.instance._get_common_params()

    def test_get_common_params_invalid_width(self):
        self.params["width"] = "invalid"
        with self.assertRaises(gpioError):
            self.instance._get_common_params()
