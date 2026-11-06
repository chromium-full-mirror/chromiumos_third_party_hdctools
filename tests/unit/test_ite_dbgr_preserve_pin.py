# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for ite_dbgr_preserve_pin servo controls across overlays."""

import os
import unittest
import xml.etree.ElementTree as ET


class TestIteDbgrPreservePin(unittest.TestCase):
    """Verify ite_dbgr_preserve_pin values in XML overlays."""

    def setUp(self):
        super().setUp()
        self.data_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "servo", "data"
        )
        self.data_dir = os.path.abspath(self.data_dir)

    def _get_control_from_file(self, filename, control_name):
        """Parse an XML overlay and find the named control."""
        path = os.path.join(self.data_dir, filename)
        self.assertTrue(os.path.exists(path), f"File {path} does not exist")
        tree = ET.parse(path)
        root = tree.getroot()
        for ctrl in root.findall(".//control"):
            name = ctrl.find("name")
            if name is not None and name.text == control_name:
                return ctrl
        return None

    def test_ec_common_default_is_empty(self):
        """ec_common.xml defines the base read-only control defaulting to empty."""
        ctrl = self._get_control_from_file("ec_common.xml", "ite_dbgr_preserve_pin")
        self.assertIsNotNone(ctrl, "ite_dbgr_preserve_pin missing in ec_common.xml")
        params = ctrl.find("params")
        self.assertIsNotNone(params)
        self.assertEqual(params.get("drv"), "echo")
        self.assertEqual(params.get("cmd"), "get")
        self.assertEqual(params.get("value"), "")

    def test_corsola_common_overrides_to_g1(self):
        """corsola_common.xml overrides ite_dbgr_preserve_pin to G1."""
        ctrl = self._get_control_from_file(
            "corsola_common.xml", "ite_dbgr_preserve_pin"
        )
        self.assertIsNotNone(
            ctrl, "ite_dbgr_preserve_pin missing in corsola_common.xml"
        )
        params = ctrl.find("params")
        self.assertIsNotNone(params)
        self.assertEqual(params.get("drv"), "echo")
        self.assertEqual(params.get("cmd"), "get")
        self.assertEqual(params.get("value"), "G1")
        self.assertEqual(params.get("clobber_ok"), "full")

    def test_rauru_overlay_overrides_to_g4(self):
        """servo_rauru_overlay.xml overrides ite_dbgr_preserve_pin to G4."""
        ctrl = self._get_control_from_file(
            "servo_rauru_overlay.xml", "ite_dbgr_preserve_pin"
        )
        self.assertIsNotNone(
            ctrl, "ite_dbgr_preserve_pin missing in servo_rauru_overlay.xml"
        )
        params = ctrl.find("params")
        self.assertIsNotNone(params)
        self.assertEqual(params.get("drv"), "echo")
        self.assertEqual(params.get("cmd"), "get")
        self.assertEqual(params.get("value"), "G4")
        self.assertEqual(params.get("clobber_ok"), "full")

    def test_overlay_includes_resolve(self):
        """Verify rauru and corsola child overlays include the common overlays."""
        # Rauru variants include servo_rauru_overlay.xml
        for variant in (
            "servo_rauru_navi_overlay.xml",
            "servo_rauru_hylia_overlay.xml",
        ):
            tree = ET.parse(os.path.join(self.data_dir, variant))
            includes = [
                inc.find("name").text
                for inc in tree.getroot().findall(".//include")
                if inc.find("name") is not None
            ]
            self.assertIn("servo_rauru_overlay.xml", includes)

        # Corsola variants include corsola_common.xml
        for variant in (
            "servo_corsola_overlay.xml",
            "servo_corsola_veluza_overlay.xml",
            "servo_krabby_overlay.xml",
            "servo_staryu_overlay.xml",
        ):
            tree = ET.parse(os.path.join(self.data_dir, variant))
            includes = [
                inc.find("name").text
                for inc in tree.getroot().findall(".//include")
                if inc.find("name") is not None
            ]
            self.assertIn("corsola_common.xml", includes)


if __name__ == "__main__":
    unittest.main()
