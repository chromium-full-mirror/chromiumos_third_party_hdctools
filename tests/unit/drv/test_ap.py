# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest
from unittest.mock import Mock
from unittest.mock import patch

from servo.drv import ap
from servo.drv import pty_driver


class TestAp(unittest.TestCase):
    def setUp(self):
        self.interface_mock = Mock()
        self.valid_params = {
            "child": "0x34",
            "port": "0",
            "subtype": "r10k",
            "cmd": "set",
            "control_name": "test_control_name",
        }
        self.ap_instance = ap.ap(
            ("localhost", 9999),
            ("localhost", 9999),
            self.interface_mock,
            self.valid_params,
        )

    def test_get_password(self):
        # Test _Get_password method
        self.assertEqual(self.ap_instance._Get_password(), "test0000")

    def test_set_password(self):
        # Test _Set_password method
        self.ap_instance._Set_password("new_password")
        self.assertEqual(self.ap_instance._Get_password(), "new_password")

    def test_get_username(self):
        # Test _Get_username method
        self.assertEqual(self.ap_instance._Get_username(), "root")

    def test_set_username(self):
        # Test _Set_username method
        self.ap_instance._Set_username("new_username")
        self.assertEqual(self.ap_instance._Get_username(), "new_username")

    @patch("servo.drv.pty_driver.PtyDriver._issue_cmd_get_results")
    def test_get_login_success(self, mock_issue_cmd):
        # Test _Get_login method success scenario
        mock_issue_cmd.return_value = ["localhost login:"]
        result = self.ap_instance._Get_login()
        self.assertEqual(result, 0)  # Since "localhost login:" is in the match

    @patch(
        "servo.drv.pty_driver.PtyDriver._issue_cmd_get_results",
        side_effect=pty_driver.PtyError("Mocked error"),
    )
    def test_get_login_error(self, mock_issue_cmd):
        # Test _Get_login method error handling
        result = self.ap_instance._Get_login()
        self.assertEqual(result, 0)  # It should return 0 in case of an error


if __name__ == "__main__":
    unittest.main()
