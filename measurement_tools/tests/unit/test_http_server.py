# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Test http_server works as intended."""

import io
import unittest
import unittest.mock

from measurement_tools import dut_power_data
from measurement_tools import http_server


class TestHttpRequestHandler(unittest.TestCase):
    """Test HttpRequestHandler."""

    def setUp(self):
        """Set up for each unit test."""
        unittest.TestCase.setUp(self)
        self.data = "ajkajdffadsf"

        data_sampler = dut_power_data.DataSampler(None)
        data_sampler.get_data_sample = unittest.mock.MagicMock(return_value=self.data)

        # Mock server, request, and client_address for _ActualHttpRequestHandler
        mock_request = unittest.mock.MagicMock()
        mock_client_address = ("127.0.0.1", 8080)
        mock_server = unittest.mock.MagicMock()

        with unittest.mock.patch.object(
            http_server._ActualHttpRequestHandler, "setup"
        ), unittest.mock.patch.object(
            http_server._ActualHttpRequestHandler, "handle"
        ), unittest.mock.patch.object(
            http_server._ActualHttpRequestHandler, "finish"
        ):
            self.http_handler = http_server._ActualHttpRequestHandler(
                mock_request, mock_client_address, mock_server, data_sampler
            )
        self.http_handler.send_response = unittest.mock.MagicMock()
        self.http_handler.send_header = unittest.mock.MagicMock()
        self.http_handler.end_headers = unittest.mock.MagicMock()
        self.http_handler.wfile = io.BufferedIOBase()
        self.http_handler.wfile.write = unittest.mock.MagicMock()
        self.http_handler.wfile.flush = unittest.mock.MagicMock()

    def test_do_post(self):
        """Test do_post."""
        self.http_handler.do_post()

        self.http_handler.send_response.assert_called_once_with(200)
        self.http_handler.send_header.assert_any_call("Content-Type", "text/plain")
        self.http_handler.send_header.assert_any_call(
            "Content-Length", str(len(self.data))
        )
        self.http_handler.end_headers.assert_called_once()
        self.http_handler.wfile.write.assert_called_once_with(self.data.encode("utf_8"))
        self.http_handler.wfile.flush.assert_called_once()

    def test_do_get(self):
        """Test do_GET."""
        self.http_handler.do_GET()

        self.http_handler.send_response.assert_called_once_with(200)
        self.http_handler.send_header.assert_any_call("Content-Type", "text/html")
        self.http_handler.send_header.assert_any_call(
            "Content-Length", unittest.mock.ANY
        )
        self.http_handler.end_headers.assert_called_once()
        self.http_handler.wfile.write.assert_called_once_with(unittest.mock.ANY)
        self.http_handler.wfile.flush.assert_called_once()


if __name__ == "__main__":
    unittest.main()
