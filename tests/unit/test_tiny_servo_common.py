# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for tiny_servo_common."""

import datetime
from unittest import mock

import pytest

from servo_updater.ecusb import tiny_servo_common


def test_get_subprocess_args():
    assert tiny_servo_common.get_subprocess_args() == {"encoding": "utf-8"}


@mock.patch("servo_updater.ecusb.tiny_servo_common.sys.stdout")
def test_log(mock_stdout):
    tiny_servo_common.log("hello")
    mock_stdout.write.assert_has_calls([mock.call("hello"), mock.call("\n")])
    mock_stdout.flush.assert_called_once()


@mock.patch("servo_updater.ecusb.tiny_servo_common.get_usb_dev")
def test_check_usb(mock_get_usb_dev):
    mock_get_usb_dev.return_value = ["dev1", "dev2"]
    assert tiny_servo_common.check_usb(["18d1:501a"]) is True

    mock_get_usb_dev.return_value = []
    assert tiny_servo_common.check_usb(["18d1:501a"]) is False


def test_parse_vidpid_string():
    vid, pid = tiny_servo_common._parse_vidpid_string("18d1:501a")
    assert vid == 0x18D1
    assert pid == 0x501A


@mock.patch("servo_updater.ecusb.tiny_servo_common.usb.util.get_string")
def test_match_device(mock_get_string):
    dev = mock.Mock()
    dev.idVendor = 0x18D1
    dev.idProduct = 0x501A
    dev.iSerialNumber = 1

    mock_get_string.return_value = "12345"

    assert tiny_servo_common._match_device(dev, {(0x18D1, 0x501A)}, "12345") is True
    assert tiny_servo_common._match_device(dev, {(0x18D1, 0x501A)}, "wrong") is False
    assert tiny_servo_common._match_device(dev, {(0x0000, 0x0000)}, "12345") is False
    assert tiny_servo_common._match_device(dev, {(0x18D1, 0x501A)}, None) is True


@mock.patch("servo_updater.ecusb.tiny_servo_common.usb.core.find")
def test_get_usb_dev(mock_find):
    mock_find.return_value = ["dev1"]
    res = tiny_servo_common.get_usb_dev(["18d1:501a"], "12345")
    assert res == ["dev1"]
    mock_find.assert_called_once()


@mock.patch("servo_updater.ecusb.tiny_servo_common.get_usb_dev")
def test_check_usb_dev(mock_get_usb_dev):
    dev = mock.Mock()
    dev.address = 5
    mock_get_usb_dev.return_value = [dev]
    assert tiny_servo_common.check_usb_dev(["18d1:501a"]) == 5

    # Test multiple devices
    mock_get_usb_dev.return_value = [dev, dev]
    assert tiny_servo_common.check_usb_dev(["18d1:501a"]) is None

    # Test no devices
    mock_get_usb_dev.return_value = []
    assert tiny_servo_common.check_usb_dev(["18d1:501a"]) is None


@mock.patch("servo_updater.ecusb.tiny_servo_common.time.sleep")
@mock.patch("servo_updater.ecusb.tiny_servo_common.get_usb_dev")
def test_wait_for_usb(mock_get_usb_dev, unused_mock_sleep):
    mock_get_usb_dev.side_effect = [[], [], ["dev1"]]
    assert tiny_servo_common.wait_for_usb(["18d1:501a"], "12345") == {"dev1"}


@mock.patch("servo_updater.ecusb.tiny_servo_common.time.sleep")
@mock.patch("servo_updater.ecusb.tiny_servo_common.datetime")
@mock.patch("servo_updater.ecusb.tiny_servo_common.get_usb_dev")
def test_wait_for_usb_timeout(mock_get_usb_dev, mock_datetime, unused_mock_sleep):
    mock_get_usb_dev.return_value = []

    # We need real datetime and timedelta
    real_datetime = datetime.datetime

    now = real_datetime(2025, 1, 1, 12, 0, 0)
    mock_datetime.datetime.now.side_effect = [
        now,  # initial call
        now + datetime.timedelta(seconds=2),  # loop check
    ]
    mock_datetime.timedelta = datetime.timedelta

    with pytest.raises(
        tiny_servo_common.TinyServoError, match="Timeout waiting for USB"
    ):
        tiny_servo_common.wait_for_usb(["18d1:501a"], "12345", timeout=0.1)


@mock.patch("servo_updater.ecusb.tiny_servo_common.time.sleep")
@mock.patch("servo_updater.ecusb.tiny_servo_common.get_usb_dev")
def test_wait_for_usb_remove(mock_get_usb_dev, unused_mock_sleep):
    mock_get_usb_dev.side_effect = [["dev1"], ["dev1"], []]
    assert tiny_servo_common.wait_for_usb_remove(["18d1:501a"], "12345") is None


@mock.patch("servo_updater.ecusb.tiny_servo_common.time.sleep")
@mock.patch("servo_updater.ecusb.tiny_servo_common.datetime")
@mock.patch("servo_updater.ecusb.tiny_servo_common.get_usb_dev")
def test_wait_for_usb_remove_timeout(
    mock_get_usb_dev, mock_datetime, unused_mock_sleep
):
    mock_get_usb_dev.return_value = ["dev1"]

    real_datetime = datetime.datetime
    now = real_datetime(2025, 1, 1, 12, 0, 0)
    mock_datetime.datetime.now.side_effect = [now, now + datetime.timedelta(seconds=2)]
    mock_datetime.timedelta = datetime.timedelta

    with pytest.raises(
        tiny_servo_common.TinyServoError, match="Timeout waiting for USB"
    ):
        tiny_servo_common.wait_for_usb_remove(["18d1:501a"], "12345", timeout=0.1)


@mock.patch("servo_updater.ecusb.tiny_servo_common.sys.stdout.write")
def test_do_serialno(unused_mock_stdout):
    pty_mock = mock.Mock()
    pty_mock._issue_cmd_get_results.return_value = [("matched", "12345\n\r")]

    tiny_servo_common.do_serialno("12345", pty_mock)

    pty_mock._issue_cmd_get_results.return_value = [("matched", "99999\n\r")]
    with pytest.raises(tiny_servo_common.TinyServoError, match="Serial number set to"):
        tiny_servo_common.do_serialno("12345", pty_mock)


@mock.patch("servo_updater.ecusb.tiny_servo_common.stm32uart.Suart")
@mock.patch("servo_updater.ecusb.tiny_servo_common.pty_driver.PtyDriver")
def test_setup_tinyservod(mock_pty_driver, mock_suart):
    mock_suart_instance = mock.Mock()
    mock_suart.return_value = mock_suart_instance
    mock_pty_instance = mock.Mock()
    mock_pty_driver.return_value = mock_pty_instance

    res = tiny_servo_common.setup_tinyservod("18d1:501a", 1, "12345")

    mock_suart.assert_called_once_with(
        vendor=0x18D1, product=0x501A, interface=1, serialname="12345", debuglog=False
    )
    mock_suart_instance.run.assert_called_once()
    mock_pty_driver.assert_called_once_with(mock_suart_instance, [])
    assert res == mock_pty_instance
