# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


from unittest.mock import patch

from servo_updater.ecusb import tiny_servod


class TestTinyServod:
    @patch("servo_updater.ecusb.tiny_servod.pty_driver.PtyDriver")
    @patch("servo_updater.ecusb.tiny_servod.stm32uart.Suart")
    def test_init_and_close(self, mock_suart, mock_pty):
        ts = tiny_servod.TinyServod(0x18D1, 0x501A, 1, "serial", True)
        mock_suart.assert_called_with(
            vendor=0x18D1,
            product=0x501A,
            interface=1,
            serialname="serial",
            debuglog=True,
        )
        mock_suart.return_value.run.assert_called_once()
        mock_pty.assert_called_with(mock_suart.return_value, [])

        ts.close()
        mock_suart.return_value.close.assert_called_once()

    @patch("servo_updater.ecusb.tiny_servod.pty_driver.PtyDriver")
    @patch("servo_updater.ecusb.tiny_servod.stm32uart.Suart")
    def test_reinitialize(self, mock_suart, unused_mock_pty):
        ts = tiny_servod.TinyServod(0x18D1, 0x501A, 1)
        mock_suart.return_value.close.reset_mock()
        mock_suart.return_value.run.reset_mock()

        ts.reinitialize()
        mock_suart.return_value.close.assert_called_once()
        mock_suart.return_value.run.assert_called_once()
