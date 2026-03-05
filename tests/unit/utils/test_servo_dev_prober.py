# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# pylint: disable=redefined-outer-name

import unittest.mock

import pytest

from servo.utils import servo_dev_prober


@pytest.fixture
def prober():
    return servo_dev_prober.DeviceProber()


def test_get_board_from_ec(prober):
    mock_dev = unittest.mock.MagicMock()
    mock_dev.get.return_value = "test_board"

    assert prober.get_board_from_ec(mock_dev) == "test_board"
    mock_dev.get.assert_called_once_with("ec_board")


def test_get_model_from_ec(prober):
    mock_dev = unittest.mock.MagicMock()
    mock_dev.get.return_value = "test_model"

    assert prober.get_model_from_ec(mock_dev) == "test_model"
    mock_dev.get.assert_called_once_with("ec_model")


def test_get_info_from_ec_success_on_retry(prober):
    mock_dev = unittest.mock.MagicMock()
    mock_dev.get.side_effect = [Exception("error"), Exception("error"), "success"]

    assert prober._get_info_from_ec(mock_dev, "ec_board", attempts=3) == "success"
    assert mock_dev.get.call_count == 3


def test_get_info_from_ec_failure(prober):
    mock_dev = unittest.mock.MagicMock()
    mock_dev.get.side_effect = Exception("error")

    assert prober._get_info_from_ec(mock_dev, "ec_board", attempts=2) is None
    assert mock_dev.get.call_count == 2
