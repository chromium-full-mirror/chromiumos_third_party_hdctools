# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import unittest
from unittest.mock import patch

from servo.data.impl.system_config_service import get_system_config


class TestGetSystemConfig(unittest.TestCase):
    def setUp(self):
        global _scfg_dict
        _scfg_dict = {}

    @patch("servo.common.config.system_config.SystemConfig")
    @patch("servo.data.config.servo_file_discover.get_default_config_by_vid_pid")
    @patch("servo.common.config.system_config.SystemConfig.add_cfg_file")
    def test_get_system_config(
        self, get_default_config_mock, system_config_mock, add_cfg_file_mock
    ):
        vid = "1234"
        pid = "5678"
        file_path_mock = "mock_file_path"
        get_default_config_mock.return_value = file_path_mock
        serial = "serial"
        get_system_config(pid, vid, serial)
        get_default_config_mock.assert_called_once()
