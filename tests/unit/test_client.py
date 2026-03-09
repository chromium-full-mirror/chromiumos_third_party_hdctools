# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest
import unittest.mock
import xmlrpc.client

from servo.core import client


class TestServoClient(unittest.TestCase):
    """Test ServoClient."""

    @unittest.mock.patch(
        "xmlrpc.client.ServerProxy.__init__", unittest.mock.MagicMock(return_value=None)
    )
    def setUp(self):
        """Set up for each test case."""
        unittest.TestCase.setUp(self)
        self._client = client.ServoClient()

    def test_doc_all(self):
        """Test doc_all()."""
        self._client._server.doc_all = unittest.mock.MagicMock(return_value="123")
        res = self._client.doc_all()

        self._client._server.doc_all.assert_called_once()
        self.assertEqual(res, "123")

    def test_doc(self):
        """Test doc()."""
        self._client._server.doc = unittest.mock.MagicMock(return_value="1234")
        res = self._client.doc("testing")

        self._client._server.doc.assert_called_once_with("testing")
        self.assertEqual(res, "1234")

    def test_doc_error(self):
        """Test doc() in case of error."""
        self._client._server.doc = unittest.mock.MagicMock(
            side_effect=xmlrpc.client.Fault(1, "testing")
        )

        with self.assertRaisesRegex(
            client.ServoClientError, "Problem docstring 'testing'"
        ):
            self._client.doc("testing")
        self._client._server.doc.assert_called_once_with("testing")

    def test_get(self):
        """Test get()."""
        self._client._server.get = unittest.mock.MagicMock(return_value="1235")
        res = self._client.get("testing")

        self._client._server.get.assert_called_once_with("testing")
        self.assertEqual(res, "1235")

    def test_get_error(self):
        """Test get() in case of error."""
        self._client._server.get = unittest.mock.MagicMock(
            side_effect=xmlrpc.client.Fault(1, "testing")
        )

        with self.assertRaisesRegex(
            client.ServoClientError, "Problem getting 'testing'"
        ):
            self._client.get("testing")
        self._client._server.get.assert_called_once_with("testing")

    def test_set(self):
        """Test set()."""
        self._client._server.set = unittest.mock.MagicMock()
        self._client.set("testing", "1")

        self._client._server.set.assert_called_once_with("testing", "1")

    def test_set_error(self):
        """Test set() in case of error."""
        self._client._server.set = unittest.mock.MagicMock(
            side_effect=xmlrpc.client.Fault(1, "testing")
        )

        with self.assertRaisesRegex(
            client.ServoClientError, "Problem setting 'testing'"
        ):
            self._client.set("testing", "1")
        self._client._server.set.assert_called_once_with("testing", "1")

    def test_get_all(self):
        """Test get_all()."""
        self._client._server.get_all = unittest.mock.MagicMock(return_value="1236")
        res = self._client.get_all()

        self._client._server.get_all.assert_called_once()
        self.assertEqual(res, "1236")

    def test_set_get_all(self):
        """Test set_get_all()."""
        self._client._server.set_get_all = unittest.mock.MagicMock(return_value="1237")
        res = self._client.set_get_all(["testing", "testing2"])

        self._client._server.set_get_all.assert_called_once_with(
            ["testing", "testing2"]
        )
        self.assertEqual(res, "1237")

    def test_set_get_all_error(self):
        """Test set_get_all() in case of error."""
        self._client._server.set_get_all = unittest.mock.MagicMock(
            side_effect=xmlrpc.client.Fault(1, "testing")
        )

        with self.assertRaisesRegex(
            client.ServoClientError, r"Problem with \['testing', 'testing2'\]"
        ):
            self._client.set_get_all(["testing", "testing2"])
        self._client._server.set_get_all.assert_called_once_with(
            ["testing", "testing2"]
        )

    def test_ftdii2c(self):
        """Test ftdii2c()."""
        self._client._server.ftdii2c = unittest.mock.MagicMock()
        self._client.ftdii2c("args")

        self._client._server.ftdii2c.assert_called_once_with("args")

    def test_hwinit(self):
        """Test hwinit()."""
        self._client._server.hwinit = unittest.mock.MagicMock()
        self._client.hwinit()

        self._client._server.hwinit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
