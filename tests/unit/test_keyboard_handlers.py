# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from unittest import mock

import pytest

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


@mock.patch("servo.common.utils.keyboard_handlers.time.sleep")
@mock.patch("servo.common.utils.keyboard_handlers.servo_dev_grpc.ServoService")
@mock.patch("servo.common.utils.keyboard_handlers.GrpcClient.create_grpc_channel")
def test_chrome_ec_handler(unused_mock_channel, mock_service_class, _mock_sleep):
    mock_service = mock.Mock()
    mock_service_class.return_value = mock_service

    # Mock GetBaseBoard response
    mock_service.GetBaseBoard.return_value.response = "test_board"

    handler = keyboard_handlers.ChromeECHandler(("localhost", 9999))

    with mock.patch("servo.common.utils.json_utils.wrap_value"):
        # Test basic flow
        handler.power_key()
        handler.power_long_press()
        handler.power_short_press()
        handler.power_normal_press()

        # Test basic keys
        handler.ctrl_d()
        handler.ctrl_f()
        handler.ctrl_r()
        handler.ctrl_u()
        handler.ctrl_s()
        handler.ctrl_enter()
        handler.enter_key()
        handler.refresh_key()
        handler.ctrl_refresh_key()
        handler.sysrq_x()
        handler.sysrq_r()
        handler.alt_f5()
        handler.alt_f6()
        handler.arrow_down()
        handler.arrow_up()
        handler.ctrl_key()

        # Test set logic with arbitrary
        handler.arb_key_config("a")
        handler.arb_keys_config('["a", "b"]')
        handler.arb_key()

        with pytest.raises(keyboard_handlers.InvalidJsonConfigError):
            handler.arb_keys_config('{"a": "b"}')


@mock.patch("servo.common.utils.keyboard_handlers.servo_dev_grpc.ServoService")
@mock.patch("servo.common.utils.keyboard_handlers.GrpcClient.create_grpc_channel")
def test_base_handler_not_implemented(unused_mock_channel, mock_service_class):
    mock_service = mock.Mock()
    mock_service_class.return_value = mock_service
    handler = keyboard_handlers._BaseHandler(("localhost", 9999))

    # Base handler methods should raise NotImplementedError
    methods = [
        "ctrl_d",
        "ctrl_f",
        "ctrl_r",
        "ctrl_u",
        "ctrl_s",
        "ctrl_enter",
        "ctrl_key",
        "alt_f5",
        "alt_f6",
        "arrow_up",
        "arrow_down",
        "enter_key",
        "refresh_key",
        "ctrl_refresh_key",
        "imaginary_key",
        "sysrq_x",
        "sysrq_r",
        "arb_key",
    ]
    for method_name in methods:
        method = getattr(handler, method_name)
        try:
            method()
        except NotImplementedError:
            pass
        else:
            pytest.fail(f"Method {method_name} did not raise NotImplementedError")

    # Test power_key fallback path
    def mock_get_servo(control_name=None, **_kwargs):
        if control_name == "pwr_button":
            raise keyboard_handlers.HwDriverError("test")
        mock_response = mock.Mock()
        mock_response.response = "not_ccd"
        return mock_response

    mock_service.GetServo.side_effect = mock_get_servo
    handler.power_key()
    handler.power_key_hold(1.0)


@mock.patch("servo.common.utils.keyboard_handlers.time.sleep")
@mock.patch("servo.common.utils.keyboard_handlers.servo_dev_grpc.ServoService")
@mock.patch("servo.common.utils.keyboard_handlers.GrpcClient.create_grpc_channel")
def test_usb_handler_edge_cases(unused_mock_channel, mock_service_class, _mock_sleep):
    mock_service = mock.Mock()
    mock_service_class.return_value = mock_service

    with mock.patch("serial.Serial") as mock_serial, mock.patch(
        "os.open", create=True
    ), mock.patch("os.fdopen", create=True), mock.patch(
        "termios.tcgetattr", return_value=[[], [], [], [], [], [], []], create=True
    ), mock.patch(
        "termios.tcsetattr", create=True
    ), mock.patch(
        "servo.common.utils.json_utils.wrap_value"
    ):

        handler = keyboard_handlers.USBkm232Handler(("localhost", 9999), "/dev/ttyUSB0")

        # Test repeated open/close
        handler.open()
        handler.open()
        handler.close()
        handler.close()

        # Test error paths
        handler.open()

        # Test atmega check failure
        mock_serial.return_value.read.return_value = b"\x00"  # wrong response
        handler._test_atmega()  # logs error but doesn't raise

        # Test rsp timeout
        mock_serial.return_value.read.return_value = b""
        with pytest.raises(Exception, match="Failed to get correct response"):
            handler._rsp(b"a")

        handler.close()


# Parameterize to hit all the custom KEY_MATRIX definitions
@pytest.mark.parametrize(
    "handler_class",
    [
        keyboard_handlers.ChromeECFrostflowHandler,
        keyboard_handlers.ChromeECOsirisHandler,
        keyboard_handlers.ChromeECBansheeHandler,
        keyboard_handlers.ChromeECPujjoloHandler,
        keyboard_handlers.ChromeECDelbinHandler,
        keyboard_handlers.ChromeECChinchouHandler,
        keyboard_handlers.ChromeECGreenbayupocHandler,
        keyboard_handlers.ChromeMatrix30Handler,
    ],
)
@mock.patch("servo.common.utils.keyboard_handlers.time.sleep")
@mock.patch("servo.common.utils.keyboard_handlers.servo_dev_grpc.ServoService")
@mock.patch("servo.common.utils.keyboard_handlers.GrpcClient.create_grpc_channel")
def test_chrome_ec_specific_handlers(
    unused_mock_channel, mock_service_class, _mock_sleep, handler_class
):
    mock_service = mock.Mock()
    mock_service_class.return_value = mock_service

    # Fix TypeError on GetBaseBoard().response
    mock_service.GetBaseBoard.return_value.response = "test_board"
    # For DelbinHandler which calls `_servod_get("ec_uart_cmd")` during `__init__`
    mock_service.GetServo.return_value.response = "65543"

    handler = handler_class(("localhost", 9999))

    with mock.patch("servo.common.utils.json_utils.wrap_value"):
        # Test basic methods to evaluate the matrix logic
        handler.ctrl_d()
        handler.ctrl_f()
        handler.ctrl_r()
        handler.ctrl_u()
        handler.ctrl_s()
        handler.ctrl_enter()
        handler.enter_key()
        handler.refresh_key()
        handler.ctrl_refresh_key()
        handler.sysrq_x()
        handler.sysrq_r()
        handler.alt_f5()
        handler.alt_f6()
        handler.arrow_down()
        handler.arrow_up()
        handler.ctrl_key()


@mock.patch("servo.common.utils.keyboard_handlers.time.sleep")
@mock.patch("servo.common.utils.keyboard_handlers.servo_dev_grpc.ServoService")
@mock.patch("servo.common.utils.keyboard_handlers.GrpcClient.create_grpc_channel")
def test_usb_handler(unused_mock_channel, mock_service_class, _mock_sleep):
    mock_service = mock.Mock()
    mock_service_class.return_value = mock_service

    with mock.patch("serial.Serial") as mock_serial, mock.patch(
        "os.open", create=True
    ), mock.patch("os.fdopen", create=True), mock.patch(
        "termios.tcgetattr", return_value=[[], [], [], [], [], [], []], create=True
    ), mock.patch(
        "termios.tcsetattr", create=True
    ), mock.patch(
        "servo.common.utils.json_utils.wrap_value"
    ):

        mock_serial.return_value.read.return_value = b"\xff"

        handler = keyboard_handlers.USBkm232Handler(("localhost", 9999), "/dev/ttyUSB0")
        handler.open()
        handler.power_key()
        handler.ctrl_d()
        handler.ctrl_f()
        handler.ctrl_r()
        handler.ctrl_u()
        handler.ctrl_s()
        handler.sysrq_x()
        handler.sysrq_r()
        handler.arrow_down()
        handler.arrow_up()
        handler.crtl_enter()
        handler.enter_key()
        handler.refresh_key()
        handler.ctrl_refresh_key()
        handler.alt_f5()
        handler.alt_f6()
        handler.space_key()
        handler.tab()
        handler.ctrl_key()
        handler.writestr("test")

        handler._arb_keys = ["a"]
        handler.arb_key()

        handler.close()


@mock.patch("servo.common.utils.keyboard_handlers.time.sleep")
@mock.patch("servo.common.utils.keyboard_handlers.servo_dev_grpc.ServoService")
@mock.patch("servo.common.utils.keyboard_handlers.GrpcClient.create_grpc_channel")
def test_servo_usb_handler(unused_mock_channel, mock_service_class, _mock_sleep):
    mock_service = mock.Mock()
    mock_service_class.return_value = mock_service

    with mock.patch("serial.Serial") as mock_serial, mock.patch(
        "os.open", create=True
    ), mock.patch("os.fdopen", create=True), mock.patch(
        "termios.tcgetattr", return_value=[[], [], [], [], [], [], []], create=True
    ), mock.patch(
        "termios.tcsetattr", create=True
    ), mock.patch(
        "servo.common.utils.json_utils.wrap_value"
    ):

        mock_serial.return_value.read.return_value = b"\xff"
        mock_service.GetServo.return_value.response = "/dev/ttyUSB0"

        handler = keyboard_handlers.ServoUSBkm232Handler(
            ("localhost", 9999), legacy=True
        )
        handler.open()
        handler.power_key()
        handler.ctrl_d()
        handler.sysrq_x()
        handler.arrow_down()
        handler.arrow_up()
        handler.close()
