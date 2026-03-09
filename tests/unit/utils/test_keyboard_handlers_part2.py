from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from servo.common.utils import keyboard_handlers


# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


class TestKeyboardHandlersMore:
    @patch(
        "servo.common.utils.keyboard_handlers._BaseHandler._servod_get",
        return_value="test",
    )
    @patch("servo.common.utils.keyboard_handlers._BaseHandler._servod_set")
    @patch("servo.common.utils.keyboard_handlers.GrpcClient.create_grpc_channel")
    @patch("servo.common.utils.keyboard_handlers.servo_dev_grpc.ServoService")
    def test_keyboard_handler_base(
        self, unused_mock_stub, unused_mock_channel, unused_mock_set, unused_mock_get
    ):

        handler = keyboard_handlers._BaseHandler(["localhost", 1234])
        assert handler.power_key() is None
        assert handler.power_key(1) is None
        with pytest.raises(NotImplementedError):
            handler.ctrl_key()
        with pytest.raises(NotImplementedError):
            handler.sysrq_x()
        with pytest.raises(NotImplementedError):
            handler.ctrl_d()
        with pytest.raises(NotImplementedError):
            handler.ctrl_u()
        with pytest.raises(NotImplementedError):
            handler.ctrl_enter()

    @patch(
        "servo.common.utils.keyboard_handlers._BaseHandler._servod_get",
        return_value="test",
    )
    @patch("servo.common.utils.keyboard_handlers._BaseHandler._servod_set")
    @patch("servo.common.utils.keyboard_handlers.GrpcClient.create_grpc_channel")
    @patch("servo.common.utils.keyboard_handlers.servo_dev_grpc.ServoService")
    def test_matrix_keyboard_handler(
        self, unused_mock_stub, unused_mock_channel, mock_set, unused_mock_get
    ):

        handler = keyboard_handlers.MatrixKeyboardHandler(["localhost", 1234])
        handler._driver_client = MagicMock()

        handler.power_key()
        handler._driver_client.SetGetAll.assert_called()

        mock_set.reset_mock()
        handler.power_key(2)
        handler._driver_client.SetGetAll.assert_called()

        mock_set.reset_mock()
        handler.ctrl_key()
        handler._driver_client.SetGetAll.assert_called()

        handler.power_key(2)

        handler.ctrl_key()

    @patch(
        "servo.common.utils.keyboard_handlers._BaseHandler._servod_get",
        return_value="test",
    )
    @patch("servo.common.utils.keyboard_handlers._BaseHandler._servod_set")
    @patch("servo.common.utils.keyboard_handlers.GrpcClient.create_grpc_channel")
    @patch("servo.common.utils.keyboard_handlers.servo_dev_grpc.ServoService")
    @patch("servo.common.utils.keyboard_handlers.serial.Serial")
    def test_usb_keyboard_handler(
        self,
        unused_mock_serial,
        unused_mock_stub,
        unused_mock_channel,
        unused_mock_set,
        unused_mock_get,
    ):

        unused_mock_servo = MagicMock()
        handler = keyboard_handlers.USBkm232Handler(["localhost", 1234], "ttyUSB0")

        handler.power_key()
        handler.power_key(2)
        handler.ctrl_d()
        handler.ctrl_u()
        with pytest.raises(NotImplementedError):
            handler.ctrl_enter()
        handler.sysrq_x()

    @patch(
        "servo.common.utils.keyboard_handlers._BaseHandler._servod_get",
        return_value="test",
    )
    @patch("servo.common.utils.keyboard_handlers._BaseHandler._servod_set")
    @patch("servo.common.utils.keyboard_handlers.GrpcClient.create_grpc_channel")
    @patch("servo.common.utils.keyboard_handlers.servo_dev_grpc.ServoService")
    def test_chromebox_keyboard_handler(
        self, unused_mock_stub, unused_mock_channel, unused_mock_set, unused_mock_get
    ):

        unused_mock_servo = MagicMock()
        handler = keyboard_handlers.ChromeECHandler(["localhost", 1234])

        handler.power_key()
        handler.power_key(2)
        handler.ctrl_d()
        handler.ctrl_u()
        handler.ctrl_enter()
