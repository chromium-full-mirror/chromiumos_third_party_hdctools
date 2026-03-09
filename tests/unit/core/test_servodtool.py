# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from servo.core import servodtool


class TestServodtool:
    def test_servod_tool_error(self):
        exc = servodtool.ServodToolError("error")
        assert "error" in str(exc)

    def test_setup_logging(self):
        with patch("servo.core.servodtool.logging.getLogger") as unused_mock_logger:
            with patch("servo.core.servodtool.logging.StreamHandler") as mock_handler:
                servodtool.setup_logging(debug=True)
                mock_handler.return_value.setLevel.assert_called_with(
                    servodtool.logging.DEBUG
                )

                servodtool.setup_logging(debug=False)
                mock_handler.return_value.setLevel.assert_called_with(
                    servodtool.logging.INFO
                )

    @patch("servo.core.servodtool.tools.instance.Instance")
    def test_servodutil(self, mock_instance):
        with patch("servo.core.servodtool.setup_logging") as mock_setup:
            servodtool.servodutil([])
            mock_setup.assert_called_once()
            mock_instance.return_value.add_args.assert_called()
            mock_instance.return_value.run.assert_called()

    def test_main(self):
        # We need to mock tools.REGISTERED_TOOLS to return our test tools
        mock_tool_cls = MagicMock()
        mock_tool_instance = MagicMock()
        mock_tool_instance.name = "test_tool"
        mock_tool_instance.help = "test help"
        mock_tool_cls.return_value = mock_tool_instance

        with patch("servo.core.servodtool.tools.REGISTERED_TOOLS", [mock_tool_cls]):
            with patch("servo.core.servodtool.setup_logging") as mock_setup:
                # Test help
                with pytest.raises(SystemExit):
                    servodtool.main(["--help"])

                # Test test tool execution
                servodtool.main(["--", "test_tool"])
                mock_setup.assert_called_with(False)
                mock_tool_instance.run.assert_called()

                servodtool.main(["--debug", "test_tool"])
                mock_setup.assert_called_with(True)
