from unittest.mock import MagicMock
from unittest.mock import patch

from servo.core import dut_control


# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# pylint: disable=redefined-variable-type


class TestDutControl:
    def test_build_parser(self):
        parser = dut_control._build_parser()
        assert parser is not None

    def test_display_table(self, capsys):
        table = [["A", "B"], ["1", "2"]]
        dut_control.display_table(table, "PREFIX")
        out = capsys.readouterr().out
        assert "A" in out
        assert "PREFIX" in out

    def test_display_stats(self, capsys):
        dut_control.display_stats({})
        out = capsys.readouterr().out

        dut_control.display_stats({"test": [1, 2, 3]}, prefix="PRE")
        out = capsys.readouterr().out
        assert "PRE" in out
        stats = {
            "test_key": [1.0, 2.0, 3.0],
            "dut_control.TIME_KEY": [1000, 2000, 3000],
        }
        dut_control.display_stats(stats)
        out = capsys.readouterr().out
        assert "AVERAGE" in out

    @patch("servo.core.dut_control.sys.exit")
    def test_print_gnuplot_header(self, mock_exit, capsys):
        dut_control._print_gnuplot_header(["ctrl1:val1"])
        mock_exit.assert_called_with(-1)

        dut_control._print_gnuplot_header(["ctrl1", "ctrl2"])
        out = capsys.readouterr().out
        assert "seconds" in out

    def test_pretty_print_result(self):
        assert dut_control._pretty_print_result({"k": "v"}) == "k: v"
        assert dut_control._pretty_print_result(["1", "2"]) == "1, 2"
        assert dut_control._pretty_print_result(1) == 1

    def test_do_iteration_info(self):
        sclient = MagicMock()
        options = MagicMock()
        options.info = True
        options.sleep_msecs = 0
        requests = ["get1", "set1:val1"]
        dut_control.do_iteration(requests, options, sclient, {dut_control.TIME_KEY: []})
        sclient.doc.assert_any_call("get1")

    def test_do_iteration_time_sleep(self):
        sclient = MagicMock()
        options = MagicMock()
        options.info = False
        options.print_time = False
        options.sleep_msecs = 1000000000  # Large enough to trigger sleep
        requests = ["get1"]
        stats = {"get1": [], dut_control.TIME_KEY: []}
        sclient.set_get_all.return_value = ["1"]
        with patch("servo.core.dut_control.time.sleep") as mock_sleep:
            dut_control.do_iteration(requests, options, sclient, stats)
            mock_sleep.assert_called()

    def test_do_iteration_format(self):
        sclient = MagicMock()
        options = MagicMock()
        options.info = False
        options.print_time = False
        options.sleep_msecs = 0
        options.verbose = True
        options.gnuplot = False

        requests = ["get1"]
        stats = {"get1": [], dut_control.TIME_KEY: []}
        sclient.set_get_all.return_value = ["1"]
        out_str = dut_control.do_iteration(requests, options, sclient, stats)
        assert "GET get1 -> 1" in out_str

        options.verbose = False
        options.gnuplot = True
        out_str = dut_control.do_iteration(requests, options, sclient, stats)
        assert "1" in out_str

    def test_do_iteration_time(self):
        sclient = MagicMock()
        options = MagicMock()
        options.info = False
        options.print_time = True
        options.sleep_msecs = 0
        requests = ["get1"]
        stats = {"get1": [], dut_control.TIME_KEY: []}
        sclient.set_get_all.return_value = ["1"]
        with patch("servo.core.dut_control.time.sleep"):
            dut_control.do_iteration(requests, options, sclient, stats)

    def test_do_iteration_exceptions(self):
        sclient = MagicMock()
        options = MagicMock()
        options.info = False
        options.print_time = False
        options.sleep_msecs = 0
        requests = ["get1", "get2"]
        stats = {"get1": [], "get2": [], dut_control.TIME_KEY: []}

        # Test ValueError and TypeError in stats append
        sclient.set_get_all.return_value = ["not_a_float", None]
        dut_control.do_iteration(requests, options, sclient, stats)

    def test_do_iteration(self):
        sclient = MagicMock()
        options = MagicMock()
        options.sleep_msecs = 0
        options.print_time = False
        options.verbose = False
        options.gnuplot = False
        options.value_only = False
        options.info = False
        options.time_in_secs = 0
        options.repeat = 1
        options.sleep_msecs = 0
        options.gnuplot = False

        requests = ["get1", "get2", "set1:val1"]
        stats = {"get1": [], "get2": [], dut_control.TIME_KEY: []}

        sclient.set_get_all.return_value = [1.0, 2.0, "ok"]

        dut_control.do_iteration(requests, options, sclient, stats)

        assert sclient.set_get_all.call_count == 1
        assert len(stats["get1"]) == 1

    @patch("servo.core.dut_control.do_iteration")
    def test_iterate(self, mock_do_iteration):
        options = MagicMock()
        options.time_in_secs = 0
        options.repeat = 1
        options.sleep_msecs = 0
        options.gnuplot = False
        options.hwinit = False
        options.info = False

        sclient = MagicMock()

        requests = ["ctrl"]
        dut_control.iterate(requests, options, sclient)

        mock_do_iteration.assert_called_once()

    @patch("servo.core.dut_control.client.ServoClient")
    @patch("servo.core.dut_control.iterate")
    def test_real_main_commands(self, unused_mock_iterate, unused_mock_client):
        # test hwinit
        dut_control.real_main(["--hwinit"])
        # test requests
        dut_control.real_main(["ctrl1", "ctrl2:val2"])
        # test sleep
        with patch("servo.core.dut_control.time.sleep"):
            dut_control.real_main(["--sleep", "0", "ctrl1"])

    @patch("servo.core.dut_control.client.ServoClient")
    @patch("servo.core.dut_control.sys.exit")
    def test_real_main_errors(self, mock_exit, mock_client):
        # Just call main directly and check the exit code
        exc = dut_control.ControlError("error")
        exc.message = "error"
        mock_client.return_value.doc.side_effect = exc
        dut_control.main(["-i", "ctrl1"])
        mock_exit.assert_called()

    @patch("servo.core.dut_control.client.ServoClient")
    @patch("servo.core.dut_control.sys.exit")
    def test_real_main(self, mock_exit, unused_mock_client):
        # Empty args, should just run build_parser and exit
        dut_control.real_main(["--help"])
        mock_exit.assert_called()

        # Test basic info
        dut_control.real_main(["-i"])

    @patch("servo.core.dut_control.sys.exit")
    @patch("servo.core.dut_control.real_main")
    def test_main(self, mock_real_main, mock_exit):
        dut_control.main(["ctrl"])
        mock_real_main.assert_called_with(["ctrl"])

        mock_real_main.side_effect = dut_control.client.ServoClientError("error", None)
        mock_real_main.side_effect.message = "error"
        dut_control.main(["ctrl"])
        mock_exit.assert_called_with(1)
        mock_real_main.side_effect = KeyboardInterrupt()
        dut_control.main(["ctrl"])
        mock_exit.assert_called_with(0)
