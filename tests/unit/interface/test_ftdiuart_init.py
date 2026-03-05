# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest
from unittest import mock

from servo.common.interface import ftdiuart


class TestFuartInit(unittest.TestCase):
    def setUp(self):
        self.patcher = mock.patch("servo.common.interface.ftdi_utils.load_libs")
        self.mock_load_libs = self.patcher.start()
        self.mock_flib = mock.Mock()
        self.mock_lib = mock.Mock()
        self.mock_load_libs.return_value = (self.mock_flib, self.mock_lib)

    def tearDown(self):
        self.patcher.stop()

    def test_init_success(self):
        self.mock_flib.ftdi_init.return_value = 0
        self.mock_lib.fuart_init.return_value = 0

        unused_obj = ftdiuart.Fuart(serialname="test_serial")

        self.mock_flib.ftdi_init.assert_called_once()
        self.mock_lib.fuart_init.assert_called_once()

    def test_init_ftdi_init_fail(self):
        self.mock_flib.ftdi_init.return_value = 1

        with self.assertRaisesRegex(ftdiuart.FuartError, "doing ftdi_init"):
            ftdiuart.Fuart(serialname="test_serial")

        self.mock_lib.fuart_init.assert_not_called()

    def test_init_fuart_init_fail(self):
        self.mock_flib.ftdi_init.return_value = 0
        self.mock_lib.fuart_init.return_value = 1

        with self.assertRaisesRegex(ftdiuart.FuartError, "doing fuart_init"):
            ftdiuart.Fuart(serialname="test_serial")

        self.mock_flib.ftdi_init.assert_called_once()
        self.mock_lib.fuart_init.assert_called_once()
        self.mock_flib.ftdi_deinit.assert_called_once()

    def test_context_manager(self):
        self.mock_flib.ftdi_init.return_value = 0
        self.mock_lib.fuart_init.return_value = 0
        self.mock_lib.fuart_close.return_value = 0

        with ftdiuart.Fuart(serialname="test_serial") as obj:
            self.assertIsInstance(obj, ftdiuart.Fuart)
            # Pretend it was opened so close is called
            obj._is_closed = False

        self.mock_lib.fuart_close.assert_called_once()
