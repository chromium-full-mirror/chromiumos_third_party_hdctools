# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest
from unittest.mock import Mock
from unittest.mock import patch

from servo.drv.ad5248 import ad5248
from servo.drv.ad5248 import Ad5248Error
from servo.drv.ad5248 import FULL_RESISTANCE_SPEC
from servo.drv.ad5248 import WIPER_RESISTANCE


class TestAd5248(unittest.TestCase):
    def setUp(self):
        self.interface_mock = Mock()
        self.valid_params = {
            "child": "0x34",
            "port": "0",
            "subtype": "r10k",
            "cmd": "set",
            "control_name": "test_control_name",
        }
        self.ad_instance = ad5248(
            ("localhost", 9999),
            ("localhost", 9999),
            self.interface_mock,
            params=self.valid_params,
        )

    def test_constructor_with_valid_params(self):
        # Test the constructor with valid parameters
        with patch("servo.drv.ad5248.ad5248._get_child", return_value=0x34), patch(
            "servo.drv.ad5248.ad5248._get_port", return_value=0
        ), patch("servo.drv.ad5248.ad5248._get_subtype", return_value="r10k"):
            ad = ad5248(
                ("localhost", 9999),
                ("localhost", 9999),
                self.interface_mock,
                self.valid_params,
            )
        self.assertEqual(ad._child, 0x34)
        self.assertEqual(ad._port, 0)
        self.assertEqual(ad._subtype, "r10k")

    def test_constructor_missing_child_param(self):
        # Test the constructor when the 'child' parameter is missing
        invalid_params = self.valid_params.copy()
        del invalid_params["child"]
        with self.assertRaises(Ad5248Error) as context:
            ad5248(
                ("localhost", 9999),
                ("localhost", 9999),
                self.interface_mock,
                invalid_params,
            )
        self.assertEqual(str(context.exception), "getting child address")

    def test_constructor_invalid_port_value(self):
        # Test the constructor with an invalid 'port' parameter value
        invalid_params = self.valid_params.copy()
        invalid_params["port"] = "2"
        with self.assertRaises(Ad5248Error) as context:
            ad5248(
                ("localhost", 9999),
                ("localhost", 9999),
                self.interface_mock,
                invalid_params,
            )
        self.assertEqual(str(context.exception), "port value should be 0 | 1")

    def test_constructor_missing_subtype_param(self):
        # Test the constructor when the 'subtype' parameter is missing
        invalid_params = self.valid_params.copy()
        del invalid_params["subtype"]
        with self.assertRaises(Ad5248Error) as context:
            ad5248(
                ("localhost", 9999),
                ("localhost", 9999),
                self.interface_mock,
                invalid_params,
            )
        self.assertEqual(str(context.exception), "getting subtype")

    def test_set_rdac_with_valid_byte_as_integer(self):
        # Test setting RDAC with a valid byte as an integer
        self.ad_instance._set_rdac(127)
        self.interface_mock.wr_rd.assert_called_once_with(0x34, [0, 127])

    def test_set_rdac_with_valid_byte_as_hex_string(self):
        # Test setting RDAC with a valid byte as a hex string
        self.ad_instance._set_rdac("0xAB")
        self.interface_mock.wr_rd.assert_called_once_with(0x34, [0, 0xAB])

    def test_set_rdac_with_invalid_byte_value(self):
        # Test setting RDAC with an invalid byte value
        with self.assertRaises(Ad5248Error) as context:
            self.ad_instance._set_rdac(300)
        self.assertEqual(str(context.exception), "setting value out of range 0~255")

    def test_set_resistance_value_within_range(self):
        # Test setting resistance value within the valid range
        with patch("servo.drv.ad5248.ad5248._set_rdac") as set_rdac_mock:
            self.ad_instance._set_resistance_value(5000)
        set_rdac_mock.assert_called_once()

    def test_set_resistance_value_lower_than_min(self):
        # Test setting resistance value lower than the valid range
        with self.assertRaises(Ad5248Error) as context:
            self.ad_instance._set_resistance_value(-1)
        self.assertEqual(
            str(context.exception),
            "setting value out of range 0~%d"
            % (
                FULL_RESISTANCE_SPEC["r10k"]
                + 2 * WIPER_RESISTANCE
                - FULL_RESISTANCE_SPEC["r10k"] / 256
            ),
        )

    def test_set_resistance_value_higher_than_max(self):
        # Test setting resistance value higher than the valid range
        with self.assertRaises(Ad5248Error) as context:
            self.ad_instance._set_resistance_value(15000)
        self.assertEqual(
            str(context.exception),
            "setting value out of range 0~%d"
            % (
                FULL_RESISTANCE_SPEC["r10k"]
                + 2 * WIPER_RESISTANCE
                - FULL_RESISTANCE_SPEC["r10k"] / 256
            ),
        )

    def test_get_rdac_success(self):
        # Test getting RDAC value successfully
        with patch.object(self.ad_instance._interface, "wr_rd", return_value=[42]):
            result = self.ad_instance._get_rdac()
        self.assertEqual(result, 42)

    def test_get_rdac_error_on_wr_rd(self):
        # Test handling an error when calling _interface.wr_rd
        with patch.object(
            self.ad_instance._interface,
            "wr_rd",
            side_effect=Ad5248Error("Mocked error"),
        ):
            with self.assertRaises(Ad5248Error) as context:
                self.ad_instance._get_rdac()
        self.assertEqual(str(context.exception), "Mocked error")

    def test_get_resistance_value(self):
        # Mocking self._get_rdac to control its return value
        with patch.object(self.ad_instance, "_get_rdac", return_value=127):
            result = self.ad_instance._get_resistance_value()

        # Expected calculation based on the mocked _get_rdac value
        expected_result = (
            127 * FULL_RESISTANCE_SPEC["r10k"] / 256
        ) + 2 * WIPER_RESISTANCE
        self.assertEqual(result, expected_result)

    def test_set_rdac(self):
        # Test _Set_rdac method
        with patch.object(self.ad_instance, "_set_rdac") as set_rdac_mock:
            self.ad_instance._Set_rdac(42)
        set_rdac_mock.assert_called_once_with(42)

    def test_set_r2p5k(self):
        # Test _Set_r2p5k method
        with patch.object(
            self.ad_instance, "_set_resistance_value"
        ) as set_resistance_mock:
            self.ad_instance._Set_r2p5k(2500)
        set_resistance_mock.assert_called_once_with(2500)

    def test_get_rdac(self):
        # Test _Get_rdac method
        with patch.object(self.ad_instance, "_get_rdac", return_value=42):
            result = self.ad_instance._Get_rdac()
        self.assertEqual(result, 42)

    def test_get_r2p5k(self):
        # Test _Get_r2p5k method
        with patch.object(self.ad_instance, "_get_resistance_value", return_value=2500):
            result = self.ad_instance._Get_r2p5k()
        self.assertEqual(result, 2500)

    def test_set_r10k(self):
        # Test _Set_r10k method
        with patch.object(
            self.ad_instance, "_set_resistance_value"
        ) as set_resistance_mock:
            self.ad_instance._Set_r10k(2500)
        set_resistance_mock.assert_called_once_with(2500)

    def test_get_r10k(self):
        # Test _Get_r10k method
        with patch.object(self.ad_instance, "_get_resistance_value", return_value=42):
            result = self.ad_instance._Get_r10k()
        self.assertEqual(result, 42)

    def test_set_r50k(self):
        # Test _Set_r50k method
        with patch.object(
            self.ad_instance, "_set_resistance_value"
        ) as set_resistance_mock:
            self.ad_instance._Set_r50k(2500)
        set_resistance_mock.assert_called_once_with(2500)

    def test_get_r50k(self):
        # Test _Get_r50k method
        with patch.object(self.ad_instance, "_get_resistance_value", return_value=42):
            result = self.ad_instance._Get_r50k()
        self.assertEqual(result, 42)

    def test_set_r100k(self):
        # Test _Set_r100k method
        with patch.object(
            self.ad_instance, "_set_resistance_value"
        ) as set_resistance_mock:
            self.ad_instance._Set_r100k(2500)
        set_resistance_mock.assert_called_once_with(2500)

    def test_get_r100k(self):
        # Test _Get_r100k method
        with patch.object(self.ad_instance, "_get_resistance_value", return_value=42):
            result = self.ad_instance._Get_r100k()
        self.assertEqual(result, 42)


if __name__ == "__main__":
    unittest.main()
