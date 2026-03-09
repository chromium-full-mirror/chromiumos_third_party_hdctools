# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Unit-tests to ensure that servodtool instance works as intended."""

import argparse
import os
import signal
import time
import unittest
import unittest.mock

from servo.tools import instance
from servo.utils import scratch


class TestInstance(unittest.TestCase):
    """Test instance.py."""

    def test_help(self):
        """Test help()."""
        self.assertEqual(instance.Instance().help, "Manage running servod instances.")

    def test_show(self):
        """Test show()."""
        i = instance.Instance()
        i._scratch.find_by_id = unittest.mock.MagicMock(
            return_value={
                "active": True,
                "port": 9998,
                "serials": "sa2143",
                "pid": 21411,
            }
        )
        i._logger.info = unittest.mock.MagicMock()
        args = argparse.Namespace()
        args.id = "id"

        i.show(args)

        i._scratch.find_by_id.assert_called_once_with("id")
        i._logger.info.assert_called_once_with(
            "port : 9998\nserials : sa2143\npid : 21411"
        )

    def test_show_error(self):
        """Test show()."""
        i = instance.Instance()
        i._scratch.find_by_id = unittest.mock.MagicMock(
            side_effect=scratch.ScratchError("scratch error")
        )
        i.error = unittest.mock.MagicMock()

        args = argparse.Namespace()
        args.id = "id"

        i.show(args)

        i._scratch.find_by_id.assert_called_once_with("id")
        i.error.assert_called_once_with("scratch error")

    def test_show_all(self):
        """Test show_all()."""
        i = instance.Instance()
        i._scratch.get_all_entries = unittest.mock.MagicMock(
            return_value=[
                {"active": True, "port": 9998, "serials": "sa2143", "pid": 21411},
                {"active": True, "port": 9997, "serials": "sa2142", "pid": 21410},
                {"active": True, "port": 9996, "serials": "sa2141", "pid": 21412},
            ]
        )
        i._logger.info = unittest.mock.MagicMock()
        args = argparse.Namespace()

        i.show_all(args)

        i._scratch.get_all_entries.assert_called_once()
        i._logger.info.assert_called_once_with(
            "port : 9998\nserials : sa2143\npid : 21411\n---\n"
            "port : 9997\nserials : sa2142\npid : 21410\n---\n"
            "port : 9996\nserials : sa2141\npid : 21412"
        )

    def test_show_all_no_entries(self):
        """Test show_all()."""
        i = instance.Instance()
        i._scratch.get_all_entries = unittest.mock.MagicMock(return_value=[])
        i._logger.info = unittest.mock.MagicMock()
        args = argparse.Namespace()

        i.show_all(args)

        i._scratch.get_all_entries.assert_called_once()
        i._logger.info.assert_called_once_with("No entries found.")

    @unittest.mock.patch("time.sleep", unittest.mock.MagicMock())
    def test_wait_for_active(self):
        """Test wait_for_active()."""
        i = instance.Instance()
        i._scratch.find_by_id = unittest.mock.MagicMock(
            side_effect=[
                {"active": False, "port": 9998, "serials": "sa2143", "pid": 21411},
                {"active": False, "port": 9998, "serials": "sa2143", "pid": 21411},
                {"active": True, "port": 9998, "serials": "sa2143", "pid": 21411},
            ]
        )
        i._logger.info = unittest.mock.MagicMock()
        i._logger.debug = unittest.mock.MagicMock()
        i.error = unittest.mock.MagicMock()
        args = argparse.Namespace()
        args.id = "id"
        args.timeout = -10

        with unittest.mock.patch(
            "time.time",
            unittest.mock.MagicMock(
                side_effect=[1, 1, 2, 3, 1 + i._WAIT_ACTIVE_DEFAULT_TIMEOUT_S]
            ),
        ):
            i.wait_for_active(args)

        i._scratch.find_by_id.assert_has_calls(
            [
                unittest.mock.call("id"),
                unittest.mock.call("id"),
                unittest.mock.call("id"),
            ]
        )
        time.sleep.assert_has_calls(
            [
                unittest.mock.call(i._WAIT_ACTIVE_POLLING_S),
                unittest.mock.call(i._WAIT_ACTIVE_POLLING_S),
            ]
        )
        i._logger.info.assert_has_calls(
            [
                unittest.mock.call(
                    "Ignoring negative timeout %d, using default %d.", -10, 30
                ),
                unittest.mock.call("Instance associated with id %r ready.", "id"),
            ]
        )
        i._logger.debug.assert_not_called()
        i.error.assert_not_called()

    @unittest.mock.patch("time.sleep", unittest.mock.MagicMock())
    def test_wait_for_active_no_active(self):
        """Test wait_for_active()."""
        i = instance.Instance()
        i._scratch.find_by_id = unittest.mock.MagicMock(
            side_effect=[
                {"active": False, "port": 9998, "serials": "sa2143", "pid": 21411},
                {"active": False, "port": 9998, "serials": "sa2143", "pid": 21411},
                {"active": False, "port": 9998, "serials": "sa2143", "pid": 21411},
            ]
        )
        i._logger.info = unittest.mock.MagicMock()
        i._logger.debug = unittest.mock.MagicMock()
        i.error = unittest.mock.MagicMock()
        args = argparse.Namespace()
        args.id = "id"
        args.timeout = -10

        with unittest.mock.patch(
            "time.time",
            unittest.mock.MagicMock(
                side_effect=[1, 1, 2, 3, 1 + i._WAIT_ACTIVE_DEFAULT_TIMEOUT_S]
            ),
        ):
            i.wait_for_active(args)

        i._scratch.find_by_id.assert_has_calls(
            [
                unittest.mock.call("id"),
                unittest.mock.call("id"),
                unittest.mock.call("id"),
            ]
        )
        time.sleep.assert_has_calls(
            [
                unittest.mock.call(i._WAIT_ACTIVE_POLLING_S),
                unittest.mock.call(i._WAIT_ACTIVE_POLLING_S),
                unittest.mock.call(i._WAIT_ACTIVE_POLLING_S),
            ]
        )
        i._logger.info.assert_called_once_with(
            "Ignoring negative timeout %d, using default %d.", -10, 30
        )
        i._logger.debug.assert_not_called()
        i.error.assert_called_once_with(
            "Instance associated with id %r failed to be marked active "
            "after %ds. Giving up.",
            "id",
            i._WAIT_ACTIVE_DEFAULT_TIMEOUT_S,
        )

    @unittest.mock.patch("time.sleep", unittest.mock.MagicMock())
    def test_wait_for_active_error(self):
        """Test wait_for_active()."""
        i = instance.Instance()
        i._scratch.find_by_id = unittest.mock.MagicMock(
            side_effect=[
                {"active": False, "port": 9998, "serials": "sa2143", "pid": 21411},
                {"active": False, "port": 9998, "serials": "sa2143", "pid": 21411},
                scratch.ScratchError("scratch err"),
            ]
        )
        i._logger.info = unittest.mock.MagicMock()
        i._logger.debug = unittest.mock.MagicMock()
        i.error = unittest.mock.MagicMock()
        args = argparse.Namespace()
        args.id = "id"
        args.timeout = -10

        with unittest.mock.patch(
            "time.time",
            unittest.mock.MagicMock(
                side_effect=[1, 1, 2, 3, 1 + i._WAIT_ACTIVE_DEFAULT_TIMEOUT_S]
            ),
        ):
            i.wait_for_active(args)

        i._scratch.find_by_id.assert_has_calls(
            [
                unittest.mock.call("id"),
                unittest.mock.call("id"),
                unittest.mock.call("id"),
            ]
        )
        time.sleep.assert_has_calls(
            [
                unittest.mock.call(i._WAIT_ACTIVE_POLLING_S),
                unittest.mock.call(i._WAIT_ACTIVE_POLLING_S),
            ]
        )
        i._logger.info.assert_called_once_with(
            "Ignoring negative timeout %d, using default %d.", -10, 30
        )
        i._logger.debug.assert_called_once_with("scratch err")
        i.error.assert_called_once_with(
            "Instance associated with id %r failed to be marked active "
            "after %ds. Giving up.",
            "id",
            i._WAIT_ACTIVE_DEFAULT_TIMEOUT_S,
        )

    @unittest.mock.patch("os.kill", unittest.mock.MagicMock())
    @unittest.mock.patch("time.sleep", unittest.mock.MagicMock())
    def test_stop(self):
        """Test stop()."""
        i = instance.Instance()
        i._scratch.find_by_id = unittest.mock.MagicMock(
            return_value={
                "active": True,
                "port": 9998,
                "serials": "sa2143",
                "pid": 21411,
            }
        )
        i._scratch.remove_entry = unittest.mock.MagicMock()
        i._logger.info = unittest.mock.MagicMock()
        args = argparse.Namespace()
        args.id = "id"

        with unittest.mock.patch(
            "time.time",
            unittest.mock.MagicMock(
                side_effect=[1, 1, 2, 3, 1 + i._SIGTERM_RETRY_TIMEOUT_S]
            ),
        ):
            i.stop(args)

        i._scratch.find_by_id.assert_called_once_with("id")
        os.kill.assert_has_calls(
            [
                unittest.mock.call(21411, signal.SIGTERM),
                unittest.mock.call(21411, 0),
                unittest.mock.call(21411, 0),
                unittest.mock.call(21411, 0),
                unittest.mock.call(21411, signal.SIGKILL),
            ]
        )
        time.sleep.assert_has_calls(
            [
                unittest.mock.call(i._SIGTERM_RETRY_WAIT_S),
                unittest.mock.call(i._SIGTERM_RETRY_WAIT_S),
                unittest.mock.call(i._SIGTERM_RETRY_WAIT_S),
            ]
        )
        i._logger.info.assert_has_calls(
            [
                unittest.mock.call(
                    "SIGTERM sent to servod instance associated with id %r.", "id"
                ),
                unittest.mock.call(
                    (
                        "Servod instance associated with %r (pid %r) did not turn down "
                        "after SIGTERM. Sending SIGKILL."
                    ),
                    "id",
                    "21411",
                ),
            ]
        )
        i._scratch.remove_entry.assert_called_once_with("id")

    def test_stop_scratch_error(self):
        """Test stop()."""
        i = instance.Instance()
        i._scratch.find_by_id = unittest.mock.MagicMock(
            side_effect=scratch.ScratchError("scratch err")
        )
        i._logger.info = unittest.mock.MagicMock()
        args = argparse.Namespace()
        args.id = "id"

        i.stop(args)

        i._scratch.find_by_id.assert_called_once_with("id")
        i._logger.info.assert_called_once_with("scratch err")

    @unittest.mock.patch(
        "os.kill", unittest.mock.MagicMock(side_effect=[None, OSError()])
    )
    @unittest.mock.patch("time.sleep", unittest.mock.MagicMock())
    def test_stop_os_error(self):
        """Test stop()."""
        i = instance.Instance()
        i._scratch.find_by_id = unittest.mock.MagicMock(
            side_effect=[
                {"active": True, "port": 9998, "serials": "sa2143", "pid": 21411}
            ]
        )
        i._scratch.remove_entry = unittest.mock.MagicMock()
        i._logger.info = unittest.mock.MagicMock()
        args = argparse.Namespace()
        args.id = "id"

        with unittest.mock.patch(
            "time.time",
            unittest.mock.MagicMock(
                side_effect=[1, 1, 2, 3, 1 + i._SIGTERM_RETRY_TIMEOUT_S]
            ),
        ):
            i.stop(args)

        i._scratch.find_by_id.assert_called_once_with("id")
        os.kill.assert_has_calls(
            [unittest.mock.call(21411, signal.SIGTERM), unittest.mock.call(21411, 0)]
        )
        i._logger.info.assert_has_calls(
            [
                unittest.mock.call(
                    "SIGTERM sent to servod instance associated with id %r.", "id"
                ),
                unittest.mock.call(
                    "Servod instance associated with id %r turned down.", "id"
                ),
            ]
        )
        i._scratch.remove_entry.assert_called_once_with("id")

    def test_rebuild(self):
        """Test rebuild()."""
        i = instance.Instance()
        i._scratch.get_all_entries = unittest.mock.MagicMock(
            return_value=[
                {"active": True, "port": 9998, "serials": "sa2143", "pid": 21411},
                {"active": True, "port": 9997, "serials": "sa2142", "pid": 21410},
                {"active": True, "port": 9996, "serials": "sa2141", "pid": 21412},
            ]
        )
        i._scratch.GenerateEntryFromPort = unittest.mock.MagicMock(return_value=True)
        i._logger.info = unittest.mock.MagicMock()
        i.error = unittest.mock.MagicMock()
        args = argparse.Namespace()
        args.port = 9998

        i.rebuild(args)

        self.assertEqual(i._scratch.get_all_entries.call_count, 2)
        i._logger.info.assert_called_once_with("port %r already known.", 9998)
        self.assertEqual(
            i._scratch.GenerateEntryFromPort.call_count,
            instance.PORT_RANGE[1] - instance.PORT_RANGE[0] - 2,
        )
        for port in range(instance.PORT_RANGE[0], instance.PORT_RANGE[1] + 1):
            if port not in [9998, 9997, 9996]:
                i._scratch.GenerateEntryFromPort.assert_any_call(port)

    def test_rebuild_unknown_port(self):
        """Test rebuild()."""
        i = instance.Instance()
        i._scratch.get_all_entries = unittest.mock.MagicMock(
            return_value=[
                {"active": True, "port": 9998, "serials": "sa2143", "pid": 21411},
                {"active": True, "port": 9997, "serials": "sa2142", "pid": 21410},
                {"active": True, "port": 9996, "serials": "sa2141", "pid": 21412},
            ]
        )
        i._scratch.GenerateEntryFromPort = unittest.mock.MagicMock(return_value=True)
        i._logger.info = unittest.mock.MagicMock()
        i.error = unittest.mock.MagicMock()
        args = argparse.Namespace()
        args.port = 9990

        i.rebuild(args)

        self.assertEqual(i._scratch.get_all_entries.call_count, 2)
        i._logger.info.assert_not_called()
        self.assertEqual(
            i._scratch.GenerateEntryFromPort.call_count,
            instance.PORT_RANGE[1] - instance.PORT_RANGE[0] - 1,
        )
        for port in range(instance.PORT_RANGE[0], instance.PORT_RANGE[1] + 1):
            if port not in [9998, 9997, 9996]:
                i._scratch.GenerateEntryFromPort.assert_any_call(port)

    def test_rebuild_no_port(self):
        """Test rebuild()."""
        i = instance.Instance()
        i._scratch.get_all_entries = unittest.mock.MagicMock(
            return_value=[
                {"active": True, "port": 9998, "serials": "sa2143", "pid": 21411},
                {"active": True, "port": 9997, "serials": "sa2142", "pid": 21410},
                {"active": True, "port": 9996, "serials": "sa2141", "pid": 21412},
            ]
        )
        i._scratch.GenerateEntryFromPort = unittest.mock.MagicMock(return_value=True)
        i._logger.info = unittest.mock.MagicMock()
        i.error = unittest.mock.MagicMock()
        args = argparse.Namespace()
        args.port = None

        i.rebuild(args)

        i._scratch.get_all_entries.assert_called_once()
        i._logger.info.assert_not_called()
        self.assertEqual(
            i._scratch.GenerateEntryFromPort.call_count,
            instance.PORT_RANGE[1] - instance.PORT_RANGE[0] - 2,
        )
        for port in range(instance.PORT_RANGE[0], instance.PORT_RANGE[1] + 1):
            if port not in [9998, 9997, 9996]:
                i._scratch.GenerateEntryFromPort.assert_any_call(port)

    def test_rebuild_failure(self):
        """Test rebuild()."""
        i = instance.Instance()
        i._scratch.get_all_entries = unittest.mock.MagicMock(
            return_value=[
                {"active": True, "port": 9998, "serials": "sa2143", "pid": 21411},
                {"active": True, "port": 9997, "serials": "sa2142", "pid": 21410},
                {"active": True, "port": 9996, "serials": "sa2141", "pid": 21412},
            ]
        )
        i._scratch.GenerateEntryFromPort = unittest.mock.MagicMock(return_value=False)
        i._logger.info = unittest.mock.MagicMock()
        i.error = unittest.mock.MagicMock(side_effect=SystemExit(1))
        args = argparse.Namespace()
        args.port = 9990

        with self.assertRaises(SystemExit) as cm:
            i.rebuild(args)

        self.assertEqual(cm.exception.code, 1)
        i._scratch.get_all_entries.assert_called_once()
        i._logger.info.assert_not_called()
        i._scratch.GenerateEntryFromPort.assert_called_once_with(9990)
        i.error.assert_called_once_with("Could not rebuild entry for port %r", 9990)

    def test_add_args(self):
        """Test add_args()."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="tool")
        tparser = subparsers.add_parser("instance")
        instance.Instance().add_args(tparser)

        self.assertEqual(
            parser.parse_args(["instance", "show", "-s", "id"]).command, "show"
        )
        self.assertEqual(parser.parse_args(["instance", "show", "-s", "id"]).id, "id")
        self.assertEqual(
            parser.parse_args(["instance", "show", "--serial", "id"]).id, "id"
        )
        self.assertEqual(parser.parse_args(["instance", "show", "-p", "9999"]).id, 9999)
        self.assertEqual(
            parser.parse_args(["instance", "show", "--port", "9999"]).id, 9999
        )

        self.assertEqual(
            parser.parse_args(["instance", "stop", "-s", "id"]).command, "stop"
        )
        self.assertEqual(parser.parse_args(["instance", "stop", "-s", "id"]).id, "id")
        self.assertEqual(
            parser.parse_args(["instance", "stop", "--serial", "id"]).id, "id"
        )
        self.assertEqual(parser.parse_args(["instance", "stop", "-p", "9999"]).id, 9999)
        self.assertEqual(
            parser.parse_args(["instance", "stop", "--port", "9999"]).id, 9999
        )

        self.assertEqual(
            parser.parse_args(["instance", "wait-for-active", "-s", "id"]).command,
            "wait-for-active",
        )
        self.assertEqual(
            parser.parse_args(["instance", "wait-for-active", "-s", "id"]).id, "id"
        )
        self.assertEqual(
            parser.parse_args(["instance", "wait-for-active", "--serial", "id"]).id,
            "id",
        )
        self.assertEqual(
            parser.parse_args(["instance", "wait-for-active", "-p", "9999"]).id, 9999
        )
        self.assertEqual(
            parser.parse_args(["instance", "wait-for-active", "--port", "9999"]).id,
            9999,
        )
        self.assertEqual(
            parser.parse_args(["instance", "wait-for-active", "-p", "9999"]).timeout,
            instance.Instance._WAIT_ACTIVE_DEFAULT_TIMEOUT_S,
        )
        self.assertEqual(
            parser.parse_args(
                ["instance", "wait-for-active", "-p", "9999", "--timeout", "1.2"]
            ).timeout,
            1.2,
        )

        self.assertEqual(parser.parse_args(["instance", "rebuild"]).command, "rebuild")
        self.assertEqual(parser.parse_args(["instance", "rebuild"]).port, None)
        self.assertEqual(
            parser.parse_args(["instance", "rebuild", "-p", "9999"]).port, 9999
        )
        self.assertEqual(
            parser.parse_args(["instance", "rebuild", "--port", "9999"]).port, 9999
        )

        self.assertEqual(
            parser.parse_args(["instance", "show-all"]).command, "show-all"
        )


if __name__ == "__main__":
    unittest.main()
