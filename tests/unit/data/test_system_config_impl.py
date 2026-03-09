# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

from servo.common.proto.system_config_pb2 import SystemConfigRequest
from servo.common.proto.system_config_pb2 import SystemConfigResponse
from servo.data.impl.system_config_impl import (
    SystemConfigImpl,  # Replace 'your_module' with the actual module name
)


class TestSystemConfigImpl(unittest.TestCase):
    def setUp(self):
        self.system_config_impl = SystemConfigImpl()

    @patch("servo.common.config.system_config.SystemConfig.add_cfg_file")
    def test_get_file_content(self, mock_add_cfg_file):
        context_mock = MagicMock()
        system_config_request = SystemConfigRequest(VID=0x18D1, PID=0x520D)
        response = self.system_config_impl.GetFileContent(
            system_config_request, context_mock
        )
        mock_add_cfg_file.assert_called()
        self.assertIsInstance(response, SystemConfigResponse)

    @patch("servo.common.config.system_config.SystemConfig.add_cfg_file")
    def test_add_cfg_file(self, mock_add_cfg_file):
        context_mock = MagicMock()
        request_mock = MagicMock()
        response = self.system_config_impl.AddCfgFile(request_mock, context_mock)
        mock_add_cfg_file.assert_called()
        self.assertIsInstance(response, SystemConfigResponse)
