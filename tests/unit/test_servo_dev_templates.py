# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for ServoDevTemplates."""

import unittest

from servo.common import servo_dev_templates
from tests.data.device_info import SERVO_DEVICE_DATA


class TestServoDevTemplates(unittest.TestCase):
    def test_get_id(self):
        """Tests retrieval of IDs for a variety of devices."""
        for dev in SERVO_DEVICE_DATA:
            expected_id = SERVO_DEVICE_DATA[dev][0]
            output_id = servo_dev_templates.get_id(dev)
            self.assertEqual(expected_id, output_id)

    def test_get_vid(self):
        """Tests retrieval of VIDs for a variety of devices."""
        for dev in SERVO_DEVICE_DATA:
            expected_vid = SERVO_DEVICE_DATA[dev][0][0]
            output_vid = servo_dev_templates.get_vid(dev)
            self.assertEqual(expected_vid, output_vid)

    def test_get_pid(self):
        """Tests retrieval of PIDs for a variety of devices."""
        for dev in SERVO_DEVICE_DATA:
            expected_pid = SERVO_DEVICE_DATA[dev][0][1]
            output_pid = servo_dev_templates.get_pid(dev)
            self.assertEqual(expected_pid, output_pid)

    def test_get_template_class_by_name(self):
        """Tests retrieval of Template Class for a variety of devices and
        confirm that class has all expected values.
        """
        for dev in SERVO_DEVICE_DATA:
            expected_class = SERVO_DEVICE_DATA[dev]
            output_class = servo_dev_templates.get_template_class_by_name(dev)
            # compare all class values
            self.assertEqual(expected_class[0][0], output_class.VID)
            self.assertEqual(expected_class[0][1], output_class.PID)
            self.assertEqual(list(expected_class[1]), output_class.LOTIDS)
            self.assertEqual(expected_class[2], output_class.DEFAULT_CONFIG)

    def test_get_template_class(self):
        """Tests retrieval of Template Class using VID PID and SERIAL for a variety
        of devices and confirm that class has all expected values.
        """
        for dev in SERVO_DEVICE_DATA:
            # retrieve expected class values
            expected_vals = SERVO_DEVICE_DATA[dev]

            # Set up input PID, VID and serial
            input_vid = expected_vals[0][0]
            input_pid = expected_vals[0][1]
            input_lotids = expected_vals[1]
            input_serial_array = []
            # If class has LOTIDs, incorporate them into the serial
            if not input_lotids:
                input_serial_array = ["madeupstring"]
            else:
                for lotid in input_lotids:
                    input_serial_array.append(lotid + "-madeupstring")

            for input_serial in input_serial_array:
                # run the function
                output_class = servo_dev_templates.get_template_class(
                    input_vid, input_pid, input_serial
                )

                # compare values for the result
                self.assertEqual(dev, output_class.TYPE)
                self.assertEqual(expected_vals[2], output_class.DEFAULT_CONFIG)

    def test_get_all_servo_ids(self):
        """Tests that all servo devices in data are contained in the set returned by
        get_all_servo_ids function.
        """
        expected_ids = set()
        for dev in SERVO_DEVICE_DATA:
            servo_id = SERVO_DEVICE_DATA[dev][0]
            expected_ids.add(servo_id)
        output_ids = servo_dev_templates.get_all_servo_ids()
        # only check for for the id values that existed at the time this unit test
        # was written
        output_ids &= expected_ids
        self.assertEqual(expected_ids, output_ids)


if __name__ == "__main__":
    unittest.main()
