# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
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
            assert (servo_host.starter._servod.get("servo_type") == "servo_v4p1_with_ccd_cr50")
            serial_json = json.loads(servo_host.starter._servod.get("serialnames"))
            assert (serial_json["root"] == servo_v4p1_device.iSerial)
            assert (serial_json["main"] == ccd_device.iSerial)
            assert (servo_host.starter._servod.get("serialname") == servo_v4p1_device.iSerial)
            assert (servo_host.starter._servod.get("servo_serialname") == servo_v4p1_device.iSerial)
            assert (servo_host.starter._servod.get("ccd_serialname") == ccd_device.iSerial)
            # aleena is the harcoded board name in mocked_pty_data
            # not_applicable is the board name overriden by some overlays
            if board == 'mistral':
                assert (servo_host.starter._servod.get("ccd_cr50.ec_board") == "not_applicable")
            else:
                assert (servo_host.starter._servod.get("ccd_cr50.ec_board") == "aleena")
            assert (servo_host.starter._servod.get("servo_v4p1.servo_v4p1_version") == "servo_v4p1_v2.0.8584+1a7e7e64c")
            assert (servo_host.starter._servod.get("cold_reset") == "off")
            assert (servo_host.starter._servod.get("warm_reset") == "off")
            # there is no effective way of checking state change yet
            assert servo_host.starter._servod.set("cold_reset", "on")
            assert servo_host.starter._servod.set("warm_reset", "on")

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
        test_servo_type = "servo_v4p1_with_servo_micro"
        if not common.board_supports_servo_type(board, test_servo_type):
            return
        (servo_host, servo_v4p1_device, servo_micro_device) = mock_host_with_4p1_servo_and_servo_micro(board, model)
        servo_host.clear_all_interfaces()
        try:
            assert (servo_host.starter._servod.get("servo_type") == test_servo_type)
            serial_json = json.loads(servo_host.starter._servod.get("serialnames"))
            assert (serial_json["root"] == servo_v4p1_device.iSerial)
            assert (serial_json["main"] == servo_micro_device.iSerial)
            assert (servo_host.starter._servod.get("serialname") == servo_v4p1_device.iSerial)
            assert (servo_host.starter._servod.get("servo_micro_serialname") == servo_micro_device.iSerial)
            assert (servo_host.starter._servod.get("servo_v4p1.servo_v4p1_version") == "servo_v4p1_v2.0.8584+1a7e7e64c")
            assert (servo_host.starter._servod.get("servo_micro.servo_micro_version") == "servo_micro_v2.4.57-ce329f64f")
            assert (servo_host.starter._servod.get("cold_reset") == "off")
            assert (servo_host.starter._servod.get("warm_reset") == "off")
            # there is no effective way of checking state change yet
            assert servo_host.starter._servod.set("cold_reset", "off")
            assert servo_host.starter._servod.set("warm_reset", "off")

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
    def test_servo_type_4p1_servo_micro_cr50(self, mock_host_with_4p1_servo_and_servo_micro_and_ccd, board, model):
        """ Ensure the call

        Args:
            mock_host_with_4p1_servo_and_servo_micro_and_ccd (_type_): _description_
            board (_type_): _description_
            model (_type_): _description_
        """
        test_servo_type = "servo_v4p1_with_servo_micro_and_ccd_cr50"
        if not common.board_supports_servo_type(board, test_servo_type):
            return
        (servo_host, servo_v4p1_device, servo_micro_device, ccd_device) = mock_host_with_4p1_servo_and_servo_micro_and_ccd(board, model)
        servo_host.clear_all_interfaces()
        try:
            assert (servo_host.starter._servod.get("servo_type") == test_servo_type)
            serial_json = json.loads(servo_host.starter._servod.get("serialnames"))
            assert (serial_json["root"] == servo_v4p1_device.iSerial)
            assert (serial_json["main"] == servo_micro_device.iSerial)
            assert (serial_json["ccd_cr50"] == ccd_device.iSerial)
            assert (servo_host.starter._servod.get("serialname") == servo_v4p1_device.iSerial)
            assert (servo_host.starter._servod.get("ccd_serialname") == ccd_device.iSerial)
            assert (servo_host.starter._servod.get("servo_v4p1_serialname") == servo_v4p1_device.iSerial)
            assert (servo_host.starter._servod.get("servo_micro_serialname") == servo_micro_device.iSerial)
            assert (servo_host.starter._servod.get("servo_v4p1_version") == "servo_v4p1_v2.0.8584+1a7e7e64c")
            assert (servo_host.starter._servod.get("servo_micro_version") == "servo_micro_v2.4.57-ce329f64f")
            assert (servo_host.starter._servod.get("cold_reset") == "off")
            assert (servo_host.starter._servod.get("warm_reset") == "off")
            # there is no effective way of checking state change yet
            assert servo_host.starter._servod.set("cold_reset", "off")
            assert servo_host.starter._servod.set("warm_reset", "off")

            servo_expected = {0: [], 2: [], 3: [], 4: []}
            ccd_expected = {0: [], 1: [], 2: [], 5: []}
            servo_micro_expected = {0: [], 3: [], 4: [], 5: [], 6:[]}
            results = servo_host.dump_all_interfaces()
            assert common.compare_results(
                {
                    servo_v4p1_device.iSerial: servo_expected,
                    ccd_device.iSerial: ccd_expected,
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
        test_servo_type = "servo_v4p1_with_c2d2"
        if not common.board_supports_servo_type(board, test_servo_type):
            return
        (servo_host, servo_v4p1_device, c2d2_device) = mock_host_with_4p1_servo_and_c2d2(board, model)
        servo_host.clear_all_interfaces()
        try:
            assert (servo_host.starter._servod.get("servo_type") == test_servo_type)
            serial_json = json.loads(servo_host.starter._servod.get("serialnames"))
            assert (serial_json["root"] == servo_v4p1_device.iSerial)
            assert (serial_json["main"] == c2d2_device.iSerial)
            assert (servo_host.starter._servod.get("serialname") == servo_v4p1_device.iSerial)
            assert (servo_host.starter._servod.get("c2d2_serialname") == c2d2_device.iSerial)
            assert (servo_host.starter._servod.get("servo_v4p1_serialname") == servo_v4p1_device.iSerial)
            assert (servo_host.starter._servod.get("servo_v4p1_version") == "servo_v4p1_v2.0.8584+1a7e7e64c")
            assert (servo_host.starter._servod.get("c2d2_version") == "c2d2_v2.4.35-f1113c92b")
            assert (servo_host.starter._servod.get("cold_reset") == "off")
            assert (servo_host.starter._servod.get("warm_reset") == "off")
            # there is no effective way of checking state change yet
            assert servo_host.starter._servod.set("cold_reset", "on")
            assert servo_host.starter._servod.set("warm_reset", "on")

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

    @pytest.mark.parametrize("board,model", common.get_board_model_pairs())
    def test_servo_type_4p1_c2d2_cr50(self, mock_host_with_4p1_servo_and_c2d2_and_ccd, board, model):
        """ Ensure the call

        Args:
            mock_host_with_4p1_servo_and_c2d2_and_ccd (_type_): _description_
            board (_type_): _description_
            model (_type_): _description_
        """
        test_servo_type = "servo_v4p1_with_c2d2_and_ccd_cr50"
        if not common.board_supports_servo_type(board, test_servo_type):
            return
        (servo_host, servo_v4p1_device, c2d2_device, ccd_device) = mock_host_with_4p1_servo_and_c2d2_and_ccd(board, model)
        servo_host.clear_all_interfaces()
        try:
            assert (servo_host.starter._servod.get("servo_type") == test_servo_type)
            serial_json = json.loads(servo_host.starter._servod.get("serialnames"))
            assert (serial_json["root"] == servo_v4p1_device.iSerial)
            assert (serial_json["main"] == c2d2_device.iSerial)
            assert (serial_json["ccd_cr50"] == ccd_device.iSerial)
            assert (servo_host.starter._servod.get("serialname") == servo_v4p1_device.iSerial)
            assert (servo_host.starter._servod.get("ccd_serialname") == ccd_device.iSerial)
            assert (servo_host.starter._servod.get("servo_v4p1_serialname") == servo_v4p1_device.iSerial)
            assert (servo_host.starter._servod.get("c2d2_serialname") == c2d2_device.iSerial)
            assert (servo_host.starter._servod.get("servo_v4p1_version") == "servo_v4p1_v2.0.8584+1a7e7e64c")
            assert (servo_host.starter._servod.get("c2d2_version") == "c2d2_v2.4.35-f1113c92b")
            assert (servo_host.starter._servod.get("cold_reset") == "off")
            assert (servo_host.starter._servod.get("warm_reset") == "off")
            # there is no effective way of checking state change yet
            assert servo_host.starter._servod.set("cold_reset", "on")
            assert servo_host.starter._servod.set("warm_reset", "on")

            servo_expected = {0: [], 2: [], 3: [], 4: []}
            ccd_expected = {0: [], 1: [], 2: [], 5: []}
            c2d2_expected = {0: [], 3: [], 4: [], 5: [], 6:[]}
            results = servo_host.dump_all_interfaces()
            assert common.compare_results(
                {
                    servo_v4p1_device.iSerial: servo_expected,
                    ccd_device.iSerial: ccd_expected,
                    c2d2_device.iSerial: c2d2_expected,
                },
                results,
            )
        finally: # tear down servo_host immediately after the test to release all the tty
            servo_host.stop()
