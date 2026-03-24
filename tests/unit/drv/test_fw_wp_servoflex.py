# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import unittest.mock
from unittest.mock import MagicMock
from unittest.mock import patch

from servo.drv.fw_wp_servoflex import fwWpServoflex


class TestFwWpServoflex(unittest.TestCase):
    def setUp(self):
        self.mock_interface = MagicMock()
        self.mock_logger = MagicMock()
        self.instance = fwWpServoflex(
            grpc_core_addr=("localhost", 9999),
            grpc_data_addr=("localhost", 9999),
            interface=self.mock_interface,
            params={"cmd": "set", "control_name": "test_fw_wp_state"},
        )

    @patch("servo.drv.fw_wp_servoflex.fwWpServoflex._servod_set")
    def test_force_on(self, mock_servod_set):
        self.instance._force_on()

        if self.instance._is_open_drain:
            mock_servod_set.assert_called_with("fw_wp_od", "on")
        else:
            mock_servod_set.assert_any_call("fw_wp_vref", self.instance._fw_wp_vref)
            mock_servod_set.assert_any_call("fw_wp_en", "on")
            mock_servod_set.assert_any_call("fw_wp", "on")

    @patch("servo.drv.fw_wp_servoflex.fwWpServoflex._servod_set")
    def test_force_off(self, mock_servod_set):
        self.instance._force_off()

        if self.instance._is_open_drain:
            mock_servod_set.assert_called_with("fw_wp_od", "off")
        else:
            mock_servod_set.assert_any_call("fw_wp_vref", self.instance._fw_wp_vref)
            mock_servod_set.assert_any_call("fw_wp_en", "on")
            mock_servod_set.assert_any_call("fw_wp", "off")

    @patch("servo.drv.fw_wp_servoflex.fwWpServoflex._servod_set")
    def test_reset(self, mock_servod_set):
        self.instance._reset()

        if self.instance._is_open_drain:
            mock_servod_set.assert_called_with("fw_wp_od", "off")
        else:
            mock_servod_set.assert_called_with("fw_wp_en", "off")

    @patch("servo.drv.fw_wp_servoflex.fwWpServoflex._servod_get")
    def test_get_state_open_drain(self, mock_servod_get):
        self.instance._is_open_drain = True
        mock_servod_get.return_value = "on"

        state = self.instance._get_state()

        self.assertEqual(state, self.instance._STATE_FORCE_ON)

    @patch("servo.drv.fw_wp_servoflex.fwWpServoflex._servod_get")
    def test_get_state_not_open_drain(self, mock_servod_get):
        self.instance._is_open_drain = False
        mock_servod_get.side_effect = ["on", "on", "on"]

        state = self.instance._get_state()

        self.assertEqual(state, self.instance._STATE_FORCE_ON)
