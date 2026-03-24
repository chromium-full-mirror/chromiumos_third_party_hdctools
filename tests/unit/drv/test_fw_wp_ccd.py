# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import unittest.mock
from unittest.mock import MagicMock
from unittest.mock import patch

from servo.drv.fw_wp_ccd import fwWpCcd
from servo.drv.fw_wp_ccd import fwWpCcdError


class TestFwWpCcd(unittest.TestCase):
    def setUp(self):
        self.mock_interface = MagicMock()
        self.mock_logger = MagicMock()
        self.instance = fwWpCcd(
            grpc_core_addr=("localhost", 9999),
            grpc_data_addr=("localhost", 9999),
            interface=self.mock_interface,
            params={"cmd": "set"},
        )

    @patch("servo.drv.fw_wp_ccd.fwWpCcd._issue_cmd_get_results")
    def test_force_on(self, mock_issue_cmd_get_results):
        self.instance._params = {"atboot": "no"}
        self.instance._force_on()
        mock_issue_cmd_get_results.assert_called_with("wp on", [])

    @patch("servo.drv.fw_wp_ccd.fwWpCcd._issue_cmd_get_results")
    def test_force_off(self, mock_issue_cmd_get_results):
        self.instance._params = {"atboot": "no"}
        self.instance._force_off()
        mock_issue_cmd_get_results.assert_called_with("wp off", [])

    @patch("servo.drv.fw_wp_ccd.fwWpCcd._issue_cmd_get_results")
    def test_reset(self, mock_issue_cmd_get_results):
        self.instance._params = {"atboot": "no"}
        self.instance._reset()
        mock_issue_cmd_get_results.assert_called_with("wp follow_batt_pres", [])

    @patch("servo.drv.fw_wp_ccd.fwWpCcd._issue_cmd_get_results")
    def test_get_state(self, mock_issue_cmd_get_results):
        # Mocking the result for the _issue_cmd_get_results method
        mock_issue_cmd_get_results.return_value = [["Flash WP: enabled", "fwmp"]]

        self.instance._params = {"atboot": "no"}
        state = self.instance._get_state()

        self.assertEqual(state, self.instance._STATE_OFF)

    @patch("servo.drv.fw_wp_ccd.fwWpCcd._issue_cmd_get_results")
    def test_get_state_with_error(self, mock_issue_cmd_get_results):
        # Mocking the result for the _issue_cmd_get_results method
        mock_issue_cmd_get_results.return_value = [None]

        self.instance._params = {"atboot": "no"}
        with self.assertRaises(fwWpCcdError):
            self.instance._get_state()
