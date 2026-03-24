# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import unittest.mock
from unittest.mock import MagicMock
from unittest.mock import patch

from servo.common.proto.servo_dev_pb2 import BoolResponse
from servo.drv.hw_driver import HwDriverError
from servo.drv.macro import macro


class TestMacro(unittest.TestCase):
    def setUp(self):
        self.mock_interface = MagicMock()
        self.mock_logger = MagicMock()
        self.params = {
            "cmd": "set",
            "set_value_on": "subcontrol0:on sleep:5 subcontrol1:18 subcontrol2:on subcontrol3:cmd0 subcontrol3:cmd1",
            "set_value_off": "subcontrol2:off subcontrol0:off subcontrol3:reset",
            "get_controls": "subcontrol0 subcontrol2",
            "CONTENT": None,
        }
        self.instance = macro(
            grpc_core_addr=("localhost", 9999),
            grpc_data_addr=("localhost", 9999),
            interface=self.mock_interface,
            params=self.params,
        )
        response = BoolResponse(value=True)
        self.instance._driver_client.HasControl = unittest.mock.MagicMock(
            return_value=response
        )

    @patch("servo.drv.macro.macro._servod_get")
    @patch("servo.drv.macro.macro._servod_set")
    def test_set(self, mock_servod_set, mock_servod_get):
        mock_servod_get.return_value = "not_applicable"
        self.instance._set("on")

        mock_servod_set.assert_any_call("subcontrol0", "on")
        mock_servod_set.assert_any_call("sleep", "5")
        mock_servod_set.assert_any_call("subcontrol1", "18")
        mock_servod_set.assert_any_call("subcontrol2", "on")

    @patch("servo.drv.macro.macro._servod_get")
    def test_get(self, mock_servod_get):
        mock_servod_get.return_value = "not_applicable"

        result = self.instance._get()

        self.assertEqual(result, self.instance._STATE_UNKNOWN)

    def test_set_invalid_state(self):
        with self.assertRaises(HwDriverError):
            self.instance._set("invalid_state")
