# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from unittest import mock

from servo.common.utils import keyboard_handlers


def test_noop_handler():
    handler = keyboard_handlers.NoopHandler(("localhost", 9999))
    handler.open()
    handler.close()


@mock.patch("servo.common.utils.keyboard_handlers.servo_dev_grpc.ServoService")
@mock.patch("servo.common.utils.keyboard_handlers.GrpcClient.create_grpc_channel")
def test_base_handler_send_key(unused_mock_channel, mock_service_class):
    mock_service = mock.Mock()
    mock_service_class.return_value = mock_service
    handler = keyboard_handlers._BaseHandler(("localhost", 9999))

    with mock.patch("servo.common.utils.json_utils.wrap_value"):
        handler._servod_set("test_ctrl", "val")
        mock_service.SetServo.assert_called()


@mock.patch("servo.common.utils.keyboard_handlers.servo_dev_grpc.ServoService")
@mock.patch("servo.common.utils.keyboard_handlers.GrpcClient.create_grpc_channel")
def test_matrix_handler_press_key(unused_mock_channel, mock_service_class):
    mock_service = mock.Mock()
    mock_service_class.return_value = mock_service
    handler = keyboard_handlers.MatrixKeyboardHandler(("localhost", 9999))

    with mock.patch("servo.common.utils.json_utils.wrap_value"):
        handler.power_key()
        handler.ctrl_d()


@mock.patch("servo.common.utils.keyboard_handlers.servo_dev_grpc.ServoService")
@mock.patch("servo.common.utils.keyboard_handlers.GrpcClient.create_grpc_channel")
def test_chrome_ec_handler(unused_mock_channel, mock_service_class):
    mock_service = mock.Mock()
    mock_service_class.return_value = mock_service

    # Mock GetBaseBoard response
    mock_service.GetBaseBoard.return_value.response = "test_board"

    handler = keyboard_handlers.ChromeECHandler(("localhost", 9999))

    with mock.patch("servo.common.utils.json_utils.wrap_value"):
        handler.power_key()
        handler.sysrq_x()


@mock.patch("servo.common.utils.keyboard_handlers.servo_dev_grpc.ServoService")
@mock.patch("servo.common.utils.keyboard_handlers.GrpcClient.create_grpc_channel")
def test_usb_handler(unused_mock_channel, mock_service_class):
    mock_service = mock.Mock()
    mock_service_class.return_value = mock_service

    with mock.patch("serial.Serial"), mock.patch("os.open", create=True), mock.patch(
        "os.fdopen", create=True
    ), mock.patch(
        "termios.tcgetattr", return_value=[[], [], [], [], [], [], []], create=True
    ), mock.patch(
        "termios.tcsetattr", create=True
    ), mock.patch(
        "servo.common.utils.json_utils.wrap_value"
    ):

        handler = keyboard_handlers.USBkm232Handler(("localhost", 9999), "/dev/ttyUSB0")
        handler.open()
        handler.power_key()
        handler.close()
