# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from unittest import mock

import pytest

from servo.utils import diagnose


@pytest.fixture(name="mock_servo_dev")
def mock_servo_dev_fixture():
    dev = mock.MagicMock()
    # Provide default values so it doesn't crash on standard checks
    dev_vars = {
        "servo_dut_sbu1_mv": "0",
        "servo_dut_sbu2_mv": "0",
        "servo_dut_cc1_mv": "0",
        "servo_dut_cc2_mv": "0",
        "servo_chg_cc1_mv": "0",
        "servo_chg_cc2_mv": "0",
        "sbu_mux_enable": "off",
        "sbu_flip_sel": "off",
        "dut_connection_type": "type-c",
        "servo_fw_version": "1.0",
        "servo_latest_fw_version": "1.0",
    }

    def get_side_effect(key):
        return dev_vars.get(key)

    dev.get.side_effect = get_side_effect
    dev.template.TYPE = "servo_v4"

    return dev, dev_vars


def test_diagnose_ccd_all_default_zeros(mock_servo_dev):
    dev, unused_vars = mock_servo_dev
    faults = diagnose.diagnose_ccd(dev)

    # sbu1/2 < NC_LOW means SBU_VOLTAGE_LOW
    assert diagnose.SBU_VOLTAGE_LOW in faults
    assert diagnose.SBU_VOLTAGE_FLOAT not in faults


def test_diagnose_ccd_sbu_float(mock_servo_dev):
    dev, dev_vars = mock_servo_dev
    dev_vars["servo_dut_sbu1_mv"] = "1000"
    dev_vars["servo_dut_sbu2_mv"] = "1000"
    faults = diagnose.diagnose_ccd(dev)

    assert diagnose.SBU_VOLTAGE_FLOAT in faults
    assert diagnose.SBU_VOLTAGE_LOW not in faults


def test_diagnose_ccd_cr50_orientation_direct(mock_servo_dev):
    dev, dev_vars = mock_servo_dev
    # sbu1 < NC_LOW, sbu2 > NC_HIGH
    dev_vars["servo_dut_sbu1_mv"] = "100"
    dev_vars["servo_dut_sbu2_mv"] = "3000"
    dev_vars["sbu_flip_sel"] = "off"

    # We just run it to make sure it hits the direct logic path
    # Since direct orientation doesn't append faults, we just check no exceptions
    faults = diagnose.diagnose_ccd(dev)
    assert not faults


def test_diagnose_ccd_cr50_orientation_flip(mock_servo_dev):
    dev, dev_vars = mock_servo_dev
    # sbu1 > NC_HIGH, sbu2 < NC_LOW
    dev_vars["servo_dut_sbu1_mv"] = "3000"
    dev_vars["servo_dut_sbu2_mv"] = "100"
    dev_vars["sbu_flip_sel"] = "on"

    faults = diagnose.diagnose_ccd(dev)
    assert not faults


def test_diagnose_ccd_charger_connected(mock_servo_dev):
    dev, dev_vars = mock_servo_dev
    dev_vars["servo_chg_cc1_mv"] = "1500"
    dev_vars["servo_chg_cc2_mv"] = "1500"

    faults = diagnose.diagnose_ccd(dev)
    assert diagnose.SBU_VOLTAGE_LOW in faults


def test_diagnose_ccd_dut_connected(mock_servo_dev):
    dev, dev_vars = mock_servo_dev
    dev_vars["servo_dut_cc1_mv"] = "1500"
    dev_vars["servo_dut_cc2_mv"] = "1500"

    faults = diagnose.diagnose_ccd(dev)
    assert diagnose.SBU_VOLTAGE_LOW in faults


def test_diagnose_ccd_dut_connected_high(mock_servo_dev):
    dev, dev_vars = mock_servo_dev
    dev_vars["servo_dut_cc1_mv"] = "3000"
    dev_vars["servo_dut_cc2_mv"] = "3000"

    faults = diagnose.diagnose_ccd(dev)
    assert diagnose.SBU_VOLTAGE_LOW in faults


def test_diagnose_ccd_obsolete_fw(mock_servo_dev):
    dev, dev_vars = mock_servo_dev
    dev_vars["servo_fw_version"] = "1.0"
    dev_vars["servo_latest_fw_version"] = "2.0"

    faults = diagnose.diagnose_ccd(dev)
    assert diagnose.SBU_VOLTAGE_LOW in faults


def test_diagnose_ccd_suzyq_enabled(mock_servo_dev):
    dev, dev_vars = mock_servo_dev
    dev_vars["sbu_mux_enable"] = "on"

    faults = diagnose.diagnose_ccd(dev)
    assert diagnose.SBU_VOLTAGE_LOW in faults


@mock.patch("servo.utils.diagnose.logging.getLogger")
def test_diagnose_ccd_latest_fw_fails(mock_get_logger, mock_servo_dev):
    dev, unused_vars = mock_servo_dev
    mock_logger = mock.MagicMock()
    mock_get_logger.return_value = mock_logger

    def get_side_effect(key):
        if key == "servo_latest_fw_version":
            raise ValueError("No firmware binary found")
        if "mv" in key:
            return "0"
        return "1.0"

    dev.get.side_effect = get_side_effect

    # Should not crash
    faults = diagnose.diagnose_ccd(dev)
    assert faults

    # Verify that we didn't log an obsolete firmware warning
    for call in mock_logger.error.call_args_list:
        assert "servo firmware version doesn't match latest." not in str(call)
