# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from unittest import mock

import pytest

from servo.utils import keyboard


class MockServod:
    def __init__(self):
        self._keyboard = None
        self._usb_keyboard = None
        self._usbkm232 = None
        self.controls = []

    def has_control(self, control):
        return control in self.controls

    def set(self, control, value):
        pass


def test_get_keyboard_usb():
    servod = MockServod()
    servod._usb_keyboard = mock.Mock()
    kb = keyboard.get_keyboard(servod, "usb")
    assert kb == servod._usb_keyboard


def test_get_keyboard_normal():
    servod = MockServod()
    servod._keyboard = mock.Mock()
    kb = keyboard.get_keyboard(servod, "normal")
    assert kb == servod._keyboard


def test_get_keyboard_missing():
    servod = MockServod()
    with pytest.raises(keyboard.KeyboardUtilError):
        keyboard.get_keyboard(servod, "usb")


@mock.patch("servo.common.utils.keyboard_handlers.USBkm232Handler")
def test_set_usb_keyboard_with_usbkm232(mock_handler):
    servod = MockServod()
    servod._usbkm232 = "/dev/ttyUSB0"
    keyboard.set_usb_keyboard(("localhost", 9999), servod, False)
    mock_handler.assert_called_with(("localhost", 9999), "/dev/ttyUSB0")
    assert servod._usb_keyboard == mock_handler.return_value


@mock.patch("servo.common.utils.keyboard_handlers.ServoUSBkm232Handler")
def test_set_usb_keyboard_atmega(mock_handler):
    servod = MockServod()
    servod.controls.append("atmega_rst")
    keyboard.set_usb_keyboard(("localhost", 9999), servod, True)
    mock_handler.assert_called_with(("localhost", 9999), True)
    assert servod._usb_keyboard == mock_handler.return_value


def test_set_usb_keyboard_no_atmega():
    servod = MockServod()
    with pytest.raises(keyboard.KeyboardUtilError):
        keyboard.set_usb_keyboard(("localhost", 9999), servod, False)


@mock.patch("servo.common.utils.keyboard_handlers.NoopHandler")
def test_set_keyboard_usb_no_init(unused_mock_noop):
    servod = MockServod()
    keyboard.set_keyboard(("localhost", 9999), servod, "usb", True)
    assert servod._keyboard == unused_mock_noop.return_value
    unused_mock_noop.return_value.open.assert_called_once()


@mock.patch("servo.common.utils.keyboard_handlers.NoopHandler")
def test_set_keyboard_usb_with_init(unused_mock_noop):
    servod = MockServod()
    servod.controls.append("init_usb_keyboard")
    servod._usb_keyboard = mock.Mock()

    with mock.patch.object(servod, "set") as mock_set:
        keyboard.set_keyboard(("localhost", 9999), servod, "usb", True)
        mock_set.assert_called_with("init_usb_keyboard", True)

    assert servod._keyboard == servod._usb_keyboard
    servod._keyboard.open.assert_called_once()


@mock.patch("servo.common.utils.keyboard_handlers.ChromeECHandler")
def test_set_keyboard_normal(mock_matrix):
    servod = MockServod()
    keyboard.set_keyboard(("localhost", 9999), servod, "ChromeEC", True)
    mock_matrix.assert_called_with(("localhost", 9999))
    assert servod._keyboard == mock_matrix.return_value
    mock_matrix.return_value.open.assert_called_once()


@mock.patch("servo.common.utils.keyboard_handlers.ChromeECHandler")
def test_set_keyboard_close(mock_matrix):
    servod = MockServod()
    keyboard.set_keyboard(("localhost", 9999), servod, "ChromeEC", False)
    mock_matrix.return_value.close.assert_called_once()
