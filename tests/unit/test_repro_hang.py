# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


class TestReproHang:
    """Test to reproduce potential gRPC hangs or state issues."""

    def test_servo_type_4p1_cr50_repro(self, mock_host_with_4p1_servo_and_ccd):
        """Reproduce the hang by calling get and set on a v4.1 with CCD."""
        board = "atlas"
        model = "atlas"
        (servo_host, unused_v4p1, unused_ccd) = mock_host_with_4p1_servo_and_ccd(
            board, model
        )
        servo_host.clear_all_interfaces()
        try:
            assert servo_host.starter._servod.get("servo_type") is not None
            assert servo_host.starter._servod.get("serialname") is not None
            assert servo_host.starter._servod.set("cold_reset", "on")
        finally:
            servo_host.stop()
