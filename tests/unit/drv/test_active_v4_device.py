# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for servo.drv.active_v4_device."""

import unittest
from unittest import mock

from servo.drv import active_v4_device


class TestActiveV4Device(unittest.TestCase):
    """Tests for activeV4Device."""

    def test_ccd_ctrl_uses_usb_ccd_only_when_connected(self):
        """Test _ccd_ctrl routes to USB CCD when connected and falls back when DTS is off."""
        drv = active_v4_device.activeV4Device.__new__(active_v4_device.activeV4Device)
        drv._driver_client = mock.MagicMock()
        drv._driver_client.IsServoHasAttr.return_value = mock.MagicMock(value=True)
        queried_ctrls = []

        def fake_servod_get(ctrl):
            queried_ctrls.append(ctrl)
            if ctrl.endswith("cr50_ccd_state_flags"):
                return "UARTEC+TX UARTFPMCU+TX"
            if ctrl.endswith("cr50_brdprop"):
                return "0x0"
            return ""

        drv._servod_get = fake_servod_get
        drv.get_v4_device_info = lambda key: "ccd_gsc_nt" if key == "ccd" else None

        # 1. Dual setup with USB CCD connected (GetCcdState().state == 1):
        #    queries are routed through 'ccd_gsc_nt.cr50_*'.
        drv._driver_client.GetCcdState.return_value = mock.MagicMock(state=1)
        self.assertTrue(drv._using_ccd())
        self.assertEqual(
            queried_ctrls,
            ["ccd_gsc_nt.cr50_ccd_state_flags", "ccd_gsc_nt.cr50_brdprop"],
        )

        # 2. Dual setup with DTS mode disabled (GetCcdState().state == 0):
        #    even though get_v4_device_info('ccd') still returns 'ccd_gsc_nt',
        #    queries fall back to unprefixed controls (main / servo_micro).
        queried_ctrls.clear()
        drv._driver_client.GetCcdState.return_value = mock.MagicMock(state=0)
        self.assertTrue(drv._using_ccd())
        self.assertEqual(
            queried_ctrls,
            ["cr50_ccd_state_flags", "cr50_brdprop"],
        )

        # 3. Single-controller setup without a CCD device:
        #    queries use unprefixed controls without calling GetCcdState.
        queried_ctrls.clear()
        drv.get_v4_device_info = lambda _key: ""
        self.assertTrue(drv._using_ccd())
        self.assertEqual(
            queried_ctrls,
            ["cr50_ccd_state_flags", "cr50_brdprop"],
        )


if __name__ == "__main__":
    unittest.main()
