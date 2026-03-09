# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from unittest.mock import MagicMock
from unittest.mock import patch

from servo.common.utils import keyboard_handlers


def test_noop_handler():
    handler = keyboard_handlers.NoopHandler(None)
    assert not handler.is_open()
    handler.open()
    assert not handler.is_open()
    handler.close()
    assert not handler.is_open()


def test_base_handler():
    with patch(
        "servo.common.utils.keyboard_handlers.GrpcClient.create_grpc_channel"
    ) as mock_channel, patch(
        "servo.common.utils.keyboard_handlers.servo_dev_grpc.ServoService"
    ) as mock_service:

        handler = keyboard_handlers._BaseHandler(("localhost", 9999))
        mock_channel.assert_called_once_with("localhost", 9999)
        mock_service.assert_called_once()

        handler.open()
        assert handler.is_open()
        handler.close()
        assert not handler.is_open()


def test_chrome_ec_handler_key_matrix():
    with patch(
        "servo.common.utils.keyboard_handlers.GrpcClient.create_grpc_channel"
    ), patch("servo.common.utils.keyboard_handlers.servo_dev_grpc.ServoService"):

        handler = keyboard_handlers.ChromeECHandler(("localhost", 9999))
        handler._driver_client = MagicMock()
        handler._servod_set = MagicMock()
        # Avoid MagicMock parameter injection by explicit mocking
        with patch.object(handler, "_servod_set") as mock_set:
            handler.power_key(1)
            mock_set.assert_called()  # power_key defaults to "press"


def test_chrome_ec_handler_write():
    with patch(
        "servo.common.utils.keyboard_handlers.GrpcClient.create_grpc_channel"
    ), patch(
        "servo.common.utils.keyboard_handlers.servo_dev_grpc.ServoService"
    ) as unused_mock_service:

        handler = keyboard_handlers.ChromeECHandler(("localhost", 9999))
        handler._driver_client = MagicMock()
        handler._servod_set = MagicMock()
        handler.ctrl_d(1)
        handler._servod_set.assert_called()


def test_usb_handler():
    with patch(
        "servo.common.utils.keyboard_handlers.GrpcClient.create_grpc_channel"
    ), patch("servo.common.utils.keyboard_handlers.servo_dev_grpc.ServoService"), patch(
        "serial.Serial"
    ) as mock_serial:

        handler = keyboard_handlers.USBkm232Handler(None, "test_device")
        handler.serial = mock_serial.return_value
        handler.serial.read.return_value = b"\x00"
