# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from unittest.mock import MagicMock
from unittest.mock import patch

from servo.core import watchdog


class TestDeviceWatchdog:

    def test_init(self):
        mock_servod = MagicMock()
        dev1 = MagicMock()
        dev2 = MagicMock()
        dev1.reinit_ok.return_value = True
        dev1.REINIT_ATTEMPTS = 5
        dev2.reinit_ok.return_value = False
        mock_servod.get_devices.return_value = [dev1, dev2]
        wd = watchdog.DeviceWatchdog(mock_servod, reconnect_timeout=1.0)

        assert wd.done.is_set() is False
        assert wd._rate == 0.2
        assert wd._devices == [dev1, dev2]

    def test_deactivate(self):
        mock_servod = MagicMock()
        wd = watchdog.DeviceWatchdog(mock_servod)
        wd.deactivate()
        assert wd.done.is_set() is True

    @patch("servo.core.watchdog.os.kill")
    @patch("servo.core.watchdog.os.getpid")
    def test_disconnect(self, mock_getpid, mock_kill):
        mock_servod = MagicMock()
        wd = watchdog.DeviceWatchdog(mock_servod)
        mock_getpid.return_value = 1234

        wd.disconnect("test_device")

        mock_kill.assert_called_with(1234, watchdog.signal.SIGTERM)
        assert wd.done.is_set() is True

    @patch("servo.core.watchdog.os.kill")
    @patch("servo.core.watchdog.os.getpid")
    def test_run_success(self, unused_mock_getpid, unused_mock_kill):
        mock_servod = MagicMock()
        mock_dev = MagicMock()
        mock_dev.get_id.return_value = (0x18D1, 0x501A, "12345")
        mock_servod.get_devices.return_value = [mock_dev]

        wd = watchdog.DeviceWatchdog(mock_servod)
        wd._rate = 0.01

        with patch.object(wd.done, "is_set", side_effect=[False, True]):
            wd.run()
        assert mock_dev.is_connected.called

    @patch("servo.core.watchdog.os.kill")
    @patch("servo.core.watchdog.os.getpid")
    def test_run_reconnect(self, unused_mock_getpid, unused_mock_kill):
        mock_servod = MagicMock()
        mock_dev = MagicMock()
        mock_dev.get_id.return_value = (0x18D1, 0x501A, "12345")
        mock_dev.reinit_ok.return_value = True
        mock_dev.REINIT_ATTEMPTS = 5
        mock_dev.usb_devnum.side_effect = [1, 2, 2]
        mock_dev.is_connected.return_value = True
        mock_servod.get_devices.return_value = [mock_dev]

        wd = watchdog.DeviceWatchdog(mock_servod, reconnect_timeout=10.0)
        wd._rate = 0.01

        with patch.object(wd.done, "is_set", side_effect=[False, True]):
            mock_servod.reinitialize.side_effect = Exception("error")
            wd.run()

    def test_run_reconnect_success(self):
        mock_servod = MagicMock()
        mock_dev = MagicMock()
        mock_dev.get_id.return_value = (0x18D1, 0x501A, "12345")
        mock_dev.reinit_ok.return_value = True
        mock_dev.REINIT_ATTEMPTS = 5
        mock_dev.usb_devnum.side_effect = [1, 1, 1]
        mock_dev.is_connected.side_effect = [False, True]
        mock_servod.get_devices.return_value = [mock_dev]

        wd = watchdog.DeviceWatchdog(mock_servod, reconnect_timeout=10.0)
        wd._rate = 0.01

        with patch.object(wd.done, "is_set", side_effect=[False, False, True]):
            wd.run()
            mock_dev.disconnect.assert_called()

    @patch("servo.core.watchdog.os.kill")
    @patch("servo.core.watchdog.os.getpid")
    def test_run_reconnect_fail(self, unused_mock_getpid, unused_mock_kill):
        mock_servod = MagicMock()
        mock_dev = MagicMock()
        mock_dev.get_id.return_value = (0x18D1, 0x501A, "12345")
        mock_dev.reinit_ok.return_value = False
        mock_dev.REINIT_ATTEMPTS = 5
        mock_dev.usb_devnum.side_effect = [1, 2, 2]
        mock_dev.is_connected.return_value = True
        mock_servod.get_devices.return_value = [mock_dev]

        wd = watchdog.DeviceWatchdog(mock_servod)
        wd._rate = 0.01

        with patch.object(wd.done, "is_set", side_effect=[False, True]):
            wd.run()

    @patch("servo.core.watchdog.os.kill")
    @patch("servo.core.watchdog.os.getpid")
    def test_run_disconnect(self, unused_mock_getpid, unused_mock_kill):
        mock_servod = MagicMock()
        mock_dev = MagicMock()
        mock_dev.get_id.return_value = (0x18D1, 0x501A, "12345")
        mock_dev.reinit_ok.return_value = False
        mock_dev.is_connected.return_value = False
        mock_servod.get_devices.return_value = [mock_dev]

        wd = watchdog.DeviceWatchdog(mock_servod, reconnect_timeout=0.05)
        wd._rate = 0.01

        with patch.object(wd.done, "is_set", side_effect=[False, True]):
            wd.run()

    def test_duplicate_filter(self):
        log_filter = watchdog.DeviceWatchdog.DuplicateFilter()

        record1 = MagicMock()
        record1.msg = "test msg"
        record1.levelno = 20
        record1.args = ()

        assert log_filter.filter(record1) is True
        assert log_filter.filter(record1) is False

        record2 = MagicMock()
        record2.msg = "test msg 2"
        record2.levelno = 20
        record2.args = ()

        assert log_filter.filter(record2) is True
