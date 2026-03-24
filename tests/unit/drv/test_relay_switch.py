# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Test relay_switch works as intended."""
import unittest

import mock
import serial

from servo.common.interface import interface
from servo.core import servo_server
from servo.drv import hw_driver
from servo.drv import relay_switch


class TestRelaySwitch(unittest.TestCase):
    """
    Unit test class for relaySwitch
    """

    def setUp(self):
        intfc = mock.Mock(interface.Interface)
        params = {"cmd": "set"}
        self.relay_switch = relay_switch.relaySwitch(
            ("localhost", 9999), ("localhost", 9999), intfc, params
        )

    def generate_comport(self, vid, pid):
        """Create a populated serial comport object."""
        fakeport = serial.tools.list_ports_common.ListPortInfo("fake_device")
        fakeport.vid = vid
        fakeport.pid = pid
        return fakeport

    @mock.patch("servo.drv.hw_driver.HwDriver._servod_set")
    @mock.patch("serial.tools.list_ports.comports")
    def test_pwrbtn_press_fail(self, comports_mock, servod_set_mock):
        """Test that Set_relay_pwrbtn_press throws error when relay switch is not present."""
        comports_mock.return_value = [self.generate_comport(vid=0x0000, pid=0x0000)]

        # Run tests
        self.assertRaises(
            relay_switch.RelaySwitchError,
            self.relay_switch._Set_relay_pwrbtn_press,
            press_secs=0,
            num_attempts=0,
        )

    @mock.patch("serial.Serial.write", mock.MagicMock())
    @mock.patch("serial.Serial.close", mock.MagicMock())
    @mock.patch("servo.drv.hw_driver.HwDriver._servod_set")
    @mock.patch("serial.Serial")
    @mock.patch("serial.tools.list_ports.comports")
    def test_pwrbtn_press_success(self, comports_mock, serial_mock, servod_set_mock):
        """Test that Set_relay_pwrbtn_press activates relay switch when it's present."""
        # Set up comport mock with a recognized vid and pid
        comport1 = self.generate_comport(vid=0x0000, pid=0x0000)
        comport2 = self.generate_comport(vid=0x1A86, pid=0x7523)
        comports_mock.return_value = [comport1, comport2]
        # Set up mock serial object whose member functions are expected to be called
        serial_mock.return_value = serial.Serial

        # Run the function being tested
        self.relay_switch._Set_relay_pwrbtn_press(0)

        # Confirm that all resultant calls occur
        write_calls = [
            mock.call(b"\xa0\x01\x01\xa2\r\n"),
            mock.call(b"\xa0\x01\x00\xa1\r\n"),
        ]
        serial_mock.return_value.write.assert_has_calls(write_calls)
        serial_mock.return_value.close.assert_called_once()
