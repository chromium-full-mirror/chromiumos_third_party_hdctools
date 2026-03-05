# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json

import pytest

from servo.common.config import system_config
from tests.fixtures import common


class TestMetadata:
    scfg = system_config.SystemConfig()
    scfg.add_cfg_file("", "servo_v4p1.xml")
    scfg.add_cfg_file("", "ccd_cr50.xml")

    @pytest.mark.parametrize("board,model", common.get_board_model_pairs())
    def test_servo_type_4p1_cr50(self, mock_host_with_4p1_servo_and_ccd, board, model):
        """Ensure the call

        Args:
            mock_host_with_4p1_servo_and_ccd (_type_): _description_
            board (_type_): _description_
            model (_type_): _description_
        """
        (servo_host, servo_v4p1_device, ccd_device) = mock_host_with_4p1_servo_and_ccd(
            board, model
        )
        servo_host.clear_all_interfaces()
        try:
            assert servo_host.starter._servod.get("servo_type") is not None
            assert servo_host.starter._servod.get("serialname") is not None
            assert servo_host.starter._servod.get("servo_serialname") is not None
            assert servo_host.starter._servod.get("ccd_serialname") is not None
            # aleena is the hardcoded board name in mocked_pty_data
            # not_applicable is the board name overridden by some overlays
            if board == "mistral":
                assert servo_host.starter._servod.get("ccd_cr50.ec_board") is not None
            else:
                assert servo_host.starter._servod.get("ccd_cr50.ec_board") is not None
            assert (
                servo_host.starter._servod.get("servo_v4p1.servo_v4p1_version")
                is not None
            )
            assert servo_host.starter._servod.get("cold_reset") is not None
            assert servo_host.starter._servod.get("warm_reset") is not None
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
        # tear down servo_host immediately after the test to release all the tty
        finally:
            servo_host.stop()

    scfg = system_config.SystemConfig()
    scfg.add_cfg_file("", "servo_v4p1.xml")
    scfg.add_cfg_file("", "servo_micro.xml")

    @pytest.mark.parametrize("board,model", common.get_board_model_pairs())
    def test_servo_type_4p1_servo_micro(
        self, mock_host_with_4p1_servo_and_servo_micro, board, model
    ):
        """Ensure the call

        Args:
            mock_host_with_4p1_servo_and_servo_micro (_type_): _description_
            board (_type_): _description_
            model (_type_): _description_
        """
        test_servo_type = "servo_v4p1_with_servo_micro"
        if not common.board_supports_servo_type(board, test_servo_type):
            return
        (
            servo_host,
            servo_v4p1_device,
            servo_micro_device,
        ) = mock_host_with_4p1_servo_and_servo_micro(board, model)
        servo_host.clear_all_interfaces()
        try:
            assert servo_host.starter._servod.get("servo_type") is not None

            assert servo_host.starter._servod.get("serialname") is not None
            assert servo_host.starter._servod.get("servo_micro_serialname") is not None
            assert (
                servo_host.starter._servod.get("servo_v4p1.servo_v4p1_version")
                is not None
            )
            assert (
                servo_host.starter._servod.get("servo_micro.servo_micro_version")
                is not None
            )
            assert servo_host.starter._servod.get("cold_reset") is not None
            assert servo_host.starter._servod.get("warm_reset") is not None
            # there is no effective way of checking state change yet
            assert servo_host.starter._servod.set("cold_reset", "off")
            assert servo_host.starter._servod.set("warm_reset", "off")

            servo_expected = {0: [], 2: [], 3: [], 4: []}
            servo_micro_expected = {0: [], 3: [], 4: [], 5: [], 6: []}
            results = servo_host.dump_all_interfaces()
            assert common.compare_results(
                {
                    servo_v4p1_device.iSerial: servo_expected,
                    servo_micro_device.iSerial: servo_micro_expected,
                },
                results,
            )
        # tear down servo_host immediately after the test to release all the tty
        finally:
            servo_host.stop()

    scfg = system_config.SystemConfig()
    scfg.add_cfg_file("", "servo_v4p1.xml")
    scfg.add_cfg_file("", "servo_micro.xml")
    scfg.add_cfg_file("", "ccd_cr50.xml")

    @pytest.mark.parametrize("board,model", common.get_board_model_pairs())
    def test_servo_type_4p1_servo_micro_cr50(
        self, mock_host_with_4p1_servo_and_servo_micro_and_ccd, board, model
    ):
        """Ensure the call

        Args:
            mock_host_with_4p1_servo_and_servo_micro_and_ccd (_type_): _description_
            board (_type_): _description_
            model (_type_): _description_
        """
        test_servo_type = "servo_v4p1_with_servo_micro_and_ccd_cr50"
        if not common.board_supports_servo_type(board, test_servo_type):
            return
        (
            servo_host,
            servo_v4p1_device,
            servo_micro_device,
            ccd_device,
        ) = mock_host_with_4p1_servo_and_servo_micro_and_ccd(board, model)
        servo_host.clear_all_interfaces()
        try:
            assert servo_host.starter._servod.get("servo_type") is not None

            assert servo_host.starter._servod.get("serialname") is not None
            assert servo_host.starter._servod.get("ccd_serialname") is not None
            assert servo_host.starter._servod.get("servo_v4p1_serialname") is not None
            assert servo_host.starter._servod.get("servo_micro_serialname") is not None
            assert servo_host.starter._servod.get("servo_v4p1_version") is not None
            assert servo_host.starter._servod.get("servo_micro_version") is not None
            assert servo_host.starter._servod.get("cold_reset") is not None
            assert servo_host.starter._servod.get("warm_reset") is not None
            # there is no effective way of checking state change yet
            assert servo_host.starter._servod.set("cold_reset", "off")
            assert servo_host.starter._servod.set("warm_reset", "off")

            servo_expected = {0: [], 2: [], 3: [], 4: []}
            ccd_expected = {0: [], 1: [], 2: [], 5: []}
            servo_micro_expected = {0: [], 3: [], 4: [], 5: [], 6: []}
            results = servo_host.dump_all_interfaces()
            assert common.compare_results(
                {
                    servo_v4p1_device.iSerial: servo_expected,
                    ccd_device.iSerial: ccd_expected,
                    servo_micro_device.iSerial: servo_micro_expected,
                },
                results,
            )
        # tear down servo_host immediately after the test to release all the tty
        finally:
            servo_host.stop()

    scfg = system_config.SystemConfig()
    scfg.add_cfg_file("", "servo_v4p1.xml")
    scfg.add_cfg_file("", "servo_micro.xml")
    scfg.add_cfg_file("", "ccd_cr50.xml")

    @pytest.mark.parametrize("board,model", common.get_board_model_pairs())
    def test_servo_type_4p1_servo_micro_ccd_gsc(
        self, mock_host_with_4p1_servo_and_servo_micro_and_gsc_ccd, board, model
    ):
        """Ensure the call

        Args:
            mock_host_with_4p1_servo_and_servo_micro_and_gsc_ccd (_type_): _description_
            board (_type_): _description_
            model (_type_): _description_
        """
        test_servo_type = "servo_v4p1_with_servo_micro_and_ccd_gsc"
        if not common.board_supports_servo_type(board, test_servo_type):
            return
        (
            servo_host,
            servo_v4p1_device,
            servo_micro_device,
            ccd_device,
        ) = mock_host_with_4p1_servo_and_servo_micro_and_gsc_ccd(board, model)
        servo_host.clear_all_interfaces()
        try:
            assert servo_host.starter._servod.get("servo_type") == test_servo_type
            serial_json = json.loads(servo_host.starter._servod.get("serialnames"))
            assert serial_json["root"] == servo_v4p1_device.iSerial
            assert serial_json["main"] == servo_micro_device.iSerial
            assert serial_json["ccd_gsc"] == ccd_device.iSerial
            assert (
                servo_host.starter._servod.get("serialname")
                == servo_v4p1_device.iSerial
            )
            assert (
                servo_host.starter._servod.get("ccd_serialname") == ccd_device.iSerial
            )
            assert (
                servo_host.starter._servod.get("servo_v4p1_serialname")
                == servo_v4p1_device.iSerial
            )
            assert (
                servo_host.starter._servod.get("servo_micro_serialname")
                == servo_micro_device.iSerial
            )
            assert (
                servo_host.starter._servod.get("servo_v4p1_version")
                == "servo_v4p1_v2.0.8584+1a7e7e64c"
            )
            assert (
                servo_host.starter._servod.get("servo_micro_version")
                == "servo_micro_v2.4.57-ce329f64f"
            )
            # aleena is the hardcoded board name in mocked_pty_data
            # not_applicable is the board name overridden by some overlays
            if board == "mistral":
                assert (
                    servo_host.starter._servod.get("ccd_gsc.ec_board")
                    == "not_applicable"
                )
            else:
                assert servo_host.starter._servod.get("ccd_gsc.ec_board") == "aleena"
            assert servo_host.starter._servod.get("cold_reset") == "off"
            assert servo_host.starter._servod.get("warm_reset") == "off"
            # there is no effective way of checking state change yet
            assert servo_host.starter._servod.set("cold_reset", "off")
            assert servo_host.starter._servod.set("warm_reset", "off")

            servo_expected = {0: [], 2: [], 3: [], 4: []}
            ccd_expected = {0: [], 1: [], 2: [], 5: []}
            servo_micro_expected = {0: [], 3: [], 4: [], 5: [], 6: []}
            results = servo_host.dump_all_interfaces()
            assert common.compare_results(
                {
                    servo_v4p1_device.iSerial: servo_expected,
                    ccd_device.iSerial: ccd_expected,
                    servo_micro_device.iSerial: servo_micro_expected,
                },
                results,
            )
        # tear down servo_host immediately after the test to release all the tty
        finally:
            servo_host.stop()

    scfg = system_config.SystemConfig()
    scfg.add_cfg_file("", "servo_v4p1.xml")
    scfg.add_cfg_file("", "servo_micro.xml")
    scfg.add_cfg_file("", "ccd_cr50.xml")

    @pytest.mark.parametrize("board,model", common.get_board_model_pairs())
    def test_servo_type_4p1_servo_micro_ccd_gsc_nt(
        self, mock_host_with_4p1_servo_and_servo_micro_and_gsc_ccd_nt, board, model
    ):
        """Ensure the call

        Args:
            mock_host_with_4p1_servo_and_servo_micro_and_gsc_ccd_nt (_type_): _
                description_
            board (_type_): _description_
            model (_type_): _description_
        """
        test_servo_type = "servo_v4p1_with_servo_micro_and_ccd_gsc_nt"
        if not common.board_supports_servo_type(board, test_servo_type):
            return
        (
            servo_host,
            servo_v4p1_device,
            servo_micro_device,
            ccd_device,
        ) = mock_host_with_4p1_servo_and_servo_micro_and_gsc_ccd_nt(board, model)
        servo_host.clear_all_interfaces()
        try:
            assert servo_host.starter._servod.get("servo_type") == test_servo_type
            serial_json = json.loads(servo_host.starter._servod.get("serialnames"))
            assert serial_json["root"] == servo_v4p1_device.iSerial
            assert serial_json["main"] == servo_micro_device.iSerial
            assert serial_json["ccd_gsc_nt"] == ccd_device.iSerial
            assert (
                servo_host.starter._servod.get("serialname")
                == servo_v4p1_device.iSerial
            )
            assert (
                servo_host.starter._servod.get("ccd_serialname") == ccd_device.iSerial
            )
            assert (
                servo_host.starter._servod.get("servo_v4p1_serialname")
                == servo_v4p1_device.iSerial
            )
            assert (
                servo_host.starter._servod.get("servo_micro_serialname")
                == servo_micro_device.iSerial
            )
            assert (
                servo_host.starter._servod.get("servo_v4p1_version")
                == "servo_v4p1_v2.0.8584+1a7e7e64c"
            )
            assert (
                servo_host.starter._servod.get("servo_micro_version")
                == "servo_micro_v2.4.57-ce329f64f"
            )
            # aleena is the hardcoded board name in mocked_pty_data
            # not_applicable is the board name overridden by some overlays
            if board == "mistral":
                # The common "ccd_gsc" prefix should also work for the nt
                # specific servo interface
                assert (
                    servo_host.starter._servod.get("ccd_gsc.ec_board")
                    == "not_applicable"
                )
                assert (
                    servo_host.starter._servod.get("ccd_gsc_nt.ec_board")
                    == "not_applicable"
                )
            else:
                # The common "ccd_gsc" prefix should also work for the nt
                # specific servo interface
                assert servo_host.starter._servod.get("ccd_gsc.ec_board") == "aleena"
                assert servo_host.starter._servod.get("ccd_gsc_nt.ec_board") == "aleena"
            assert servo_host.starter._servod.get("cold_reset") == "off"
            assert servo_host.starter._servod.get("warm_reset") == "off"
            # there is no effective way of checking state change yet
            assert servo_host.starter._servod.set("cold_reset", "off")
            assert servo_host.starter._servod.set("warm_reset", "off")

            servo_expected = {0: [], 2: [], 3: [], 4: []}
            ccd_expected = {0: [], 1: [], 2: [], 5: []}
            servo_micro_expected = {0: [], 3: [], 4: [], 5: [], 6: []}
            results = servo_host.dump_all_interfaces()
            assert common.compare_results(
                {
                    servo_v4p1_device.iSerial: servo_expected,
                    ccd_device.iSerial: ccd_expected,
                    servo_micro_device.iSerial: servo_micro_expected,
                },
                results,
            )
        # tear down servo_host immediately after the test to release all the tty
        finally:
            servo_host.stop()

    scfg = system_config.SystemConfig()
    scfg.add_cfg_file("", "servo_v4p1.xml")
    scfg.add_cfg_file("", "c2d2.xml")

    @pytest.mark.parametrize("board,model", common.get_board_model_pairs())
    def test_servo_type_4p1_c2d2(self, mock_host_with_4p1_servo_and_c2d2, board, model):
        """Ensure the call

        Args:
            mock_host_with_4p1_servo_and_c2d2 (_type_): _description_
            board (_type_): _description_
            model (_type_): _description_
        """
        test_servo_type = "servo_v4p1_with_c2d2"
        if not common.board_supports_servo_type(board, test_servo_type):
            return
        (
            servo_host,
            servo_v4p1_device,
            c2d2_device,
        ) = mock_host_with_4p1_servo_and_c2d2(board, model)
        servo_host.clear_all_interfaces()
        try:
            assert servo_host.starter._servod.get("servo_type") is not None
            assert servo_host.starter._servod.get("serialname") is not None
            assert servo_host.starter._servod.get("c2d2_serialname") is not None
            assert servo_host.starter._servod.get("servo_v4p1_serialname") is not None
            assert servo_host.starter._servod.get("servo_v4p1_version") is not None
            assert servo_host.starter._servod.get("c2d2_version") is not None
            assert servo_host.starter._servod.get("cold_reset") is not None
            assert servo_host.starter._servod.get("warm_reset") is not None
            # there is no effective way of checking state change yet
            assert servo_host.starter._servod.set("cold_reset", "on")
            assert servo_host.starter._servod.set("warm_reset", "on")

            servo_expected = {0: [], 2: [], 3: [], 4: []}
            c2d2_expected = {0: [], 3: [], 4: [], 5: [], 6: []}
            results = servo_host.dump_all_interfaces()
            assert common.compare_results(
                {
                    servo_v4p1_device.iSerial: servo_expected,
                    c2d2_device.iSerial: c2d2_expected,
                },
                results,
            )
        # tear down servo_host immediately after the test to release all the tty
        finally:
            servo_host.stop()

    scfg = system_config.SystemConfig()
    scfg.add_cfg_file("", "servo_v4p1.xml")
    scfg.add_cfg_file("", "c2d2.xml")
    scfg.add_cfg_file("", "ccd_cr50.xml")

    @pytest.mark.parametrize("board,model", common.get_board_model_pairs())
    def test_servo_type_4p1_c2d2_cr50(
        self, mock_host_with_4p1_servo_and_c2d2_and_ccd, board, model
    ):
        """Ensure the call

        Args:
            mock_host_with_4p1_servo_and_c2d2_and_ccd (_type_): _description_
            board (_type_): _description_
            model (_type_): _description_
        """
        test_servo_type = "servo_v4p1_with_c2d2_and_ccd_cr50"
        if not common.board_supports_servo_type(board, test_servo_type):
            return
        (
            servo_host,
            servo_v4p1_device,
            c2d2_device,
            ccd_device,
        ) = mock_host_with_4p1_servo_and_c2d2_and_ccd(board, model)
        servo_host.clear_all_interfaces()
        try:
            assert servo_host.starter._servod.get("servo_type") is not None
            assert servo_host.starter._servod.get("serialnames") is not None
            assert servo_host.starter._servod.get("servo_v4p1_version") is not None

            assert (servo_host.starter._servod.get("c2d2_version")) is not None
            assert servo_host.starter._servod.get("cold_reset") is not None
            assert servo_host.starter._servod.get("warm_reset") is not None
            # there is no effective way of checking state change yet
            assert servo_host.starter._servod.set("cold_reset", "on")
            assert servo_host.starter._servod.set("warm_reset", "on")

            servo_expected = {0: [], 2: [], 3: [], 4: []}
            ccd_expected = {0: [], 1: [], 2: [], 5: []}
            c2d2_expected = {0: [], 3: [], 4: [], 5: [], 6: []}
            results = servo_host.dump_all_interfaces()
            assert common.compare_results(
                {
                    servo_v4p1_device.iSerial: servo_expected,
                    ccd_device.iSerial: ccd_expected,
                    c2d2_device.iSerial: c2d2_expected,
                },
                results,
            )
        # tear down servo_host immediately after the test to release all the tty
        finally:
            servo_host.stop()
