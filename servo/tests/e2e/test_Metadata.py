# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging
import os
import pytest
from servo.tests.fixtures import common


class TestMetadata:
    """ Tests related to information about the device setup, version type etc.
    """
    @pytest.mark.parametrize("board,model", common.get_board_model_pairs())
    def test_servo_type_4p1_cr50(self, mock_host_with_4p1_servo_and_ccd, board, model):
        """ Ensure the call

        Args:
            mock_host_with_4p1_servo_and_ccd (_type_): _description_
            board (_type_): _description_
            model (_type_): _description_
        """
        (servo_host, servo_v4p1_device, ccd_device) = mock_host_with_4p1_servo_and_ccd(board, model)
        servo_host.clear_all_interfaces()
        try:
            assert (
                servo_host.starter._servod.get("servo_type") == "servo_v4p1_with_ccd_cr50"
            )

            servo_expected = {0: [], 2: [], 3: [], 4: []}
            ccd_expected = {0: [], 1: [], 2: [], 5: []}
            results = servo_host.dump_all_interfaces()
            assert common.compare_results(
                {
                    servo_v4p1_device.iSerial: servo_expected,
                    ccd_device.iSerial: ccd_expected,
                },
                results,
            )
        finally: # tear down servo_host immediately after the test to release all the tty
            servo_host.stop()


    @pytest.mark.parametrize("board,model", common.get_board_model_pairs())
    def test_servo_type_4p1_servo_micro(self, mock_host_with_4p1_servo_and_servo_micro, board, model):
        """ Ensure the call

        Args:
            mock_host_with_4p1_servo_and_servo_micro (_type_): _description_
            board (_type_): _description_
            model (_type_): _description_
        """
        (servo_host, servo_v4p1_device, servo_micro_device) = mock_host_with_4p1_servo_and_servo_micro(board, model)
        servo_host.clear_all_interfaces()
        try:
            assert (
                servo_host.starter._servod.get("servo_type") == "servo_v4p1_with_servo_micro"
            )

            servo_expected = {0: [], 2: [], 3: [], 4: []}
            servo_micro_expected = {0: [], 3: [], 4: [], 5: [], 6:[]}
            results = servo_host.dump_all_interfaces()
            assert common.compare_results(
                {
                    servo_v4p1_device.iSerial: servo_expected,
                    servo_micro_device.iSerial: servo_micro_expected,
                },
                results,
            )
        finally: # tear down servo_host immediately after the test to release all the tty
            servo_host.stop()

    @pytest.mark.parametrize("board,model", common.get_board_model_pairs())
    def test_servo_type_4p1_c2d2(self, mock_host_with_4p1_servo_and_c2d2, board, model):
        """ Ensure the call

        Args:
            mock_host_with_4p1_servo_and_c2d2 (_type_): _description_
            board (_type_): _description_
            model (_type_): _description_
        """
        (servo_host, servo_v4p1_device, c2d2_device) = mock_host_with_4p1_servo_and_c2d2(board, model)
        servo_host.clear_all_interfaces()
        try:
            assert (
                servo_host.starter._servod.get("servo_type") == "servo_v4p1_with_c2d2"
            )

            servo_expected = {0: [], 2: [], 3: [], 4: []}
            c2d2_expected = {0: [], 3: [], 4: [], 5: [], 6:[]}
            results = servo_host.dump_all_interfaces()
            assert common.compare_results(
                {
                    servo_v4p1_device.iSerial: servo_expected,
                    c2d2_device.iSerial: c2d2_expected,
                },
                results,
            )
        finally: # tear down servo_host immediately after the test to release all the tty
            servo_host.stop()