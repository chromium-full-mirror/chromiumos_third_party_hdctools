# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Test dut_power works as intended."""

import argparse
import logging
import shutil
import signal
import sys
import tempfile
import threading
import unittest

from measurement_tools import dut_power
from measurement_tools import dut_power_data
from measurement_tools import http_server
from measurement_tools import measure_power
from measurement_tools import servo_parsing


class TestProgressPrinter(unittest.TestCase):
    """Test ProgressPrinter."""

    @unittest.mock.patch("sys.stdout.write", unittest.mock.MagicMock())
    @unittest.mock.patch("sys.stdout.flush", unittest.mock.MagicMock())
    def test_run_stop_signal(self):
        """Test run() that terminates with stop signal."""
        printer = dut_power.ProgressPrinter()
        printer.stop.is_set = unittest.mock.MagicMock(side_effect=[False, False, True])
        printer.stop.wait = unittest.mock.MagicMock()

        printer.run()

        sys.stdout.write.assert_has_calls(
            [
                unittest.mock.call(dut_power.ProgressPrinter.PROGRESS_MARKER),
                unittest.mock.call(dut_power.ProgressPrinter.PROGRESS_MARKER),
            ]
        )
        self.assertEqual(sys.stdout.flush.call_count, 2)
        printer.stop.wait.assert_has_calls(
            [
                unittest.mock.call(dut_power.ProgressPrinter.PROGRESS_UPDATE_RATE),
                unittest.mock.call(dut_power.ProgressPrinter.PROGRESS_UPDATE_RATE),
            ]
        )

    @unittest.mock.patch("sys.stdout.write", unittest.mock.MagicMock())
    @unittest.mock.patch("sys.stdout.flush", unittest.mock.MagicMock())
    def test_run_duration(self):
        """Test run() that terminates with a certain duration."""
        printer = dut_power.ProgressPrinter(max_duration=2)
        printer.stop.is_set = unittest.mock.MagicMock(return_value=False)
        printer.stop.wait = unittest.mock.MagicMock()

        printer.run()

        sys.stdout.write.assert_has_calls(
            [
                unittest.mock.call(dut_power.ProgressPrinter.PROGRESS_MARKER),
                unittest.mock.call(dut_power.ProgressPrinter.PROGRESS_MARKER),
            ]
        )
        self.assertEqual(sys.stdout.flush.call_count, 2)
        printer.stop.wait.assert_has_calls(
            [
                unittest.mock.call(dut_power.ProgressPrinter.PROGRESS_UPDATE_RATE),
                unittest.mock.call(dut_power.ProgressPrinter.PROGRESS_UPDATE_RATE),
            ]
        )


class TestDutPower(unittest.TestCase):
    """Test DutPower."""

    class MockGroup:
        """Mock group of argparse."""

        def add_argument(self):
            pass

    def test_add_mutually_exclusive_action(self):
        """Test _add_mutually_exclusive_action()."""

        parser = servo_parsing.ServodClientParser()
        dp = dut_power.DutPower()
        saver = TestDutPower.MockGroup()
        parser.add_mutually_exclusive_group = unittest.mock.MagicMock(
            return_value=saver
        )
        saver.add_argument = unittest.mock.MagicMock()

        dp._add_mutually_exclusive_action("name", parser, True, "save")

        saver.add_argument.assert_has_calls(
            [
                unittest.mock.call(
                    "--save-name",
                    action="store_true",
                    default=True,
                    dest="save_name",
                    help="save name",
                ),
                unittest.mock.call(
                    "--no-save-name",
                    action="store_false",
                    default="==SUPPRESS==",
                    dest="save_name",
                    help="don't save name",
                ),
            ]
        )

    def test_build_parser(self):
        """Test _build_parser()."""
        dp = dut_power.DutPower()
        parser = dp._build_parser()
        self.assertTrue(isinstance(parser, servo_parsing.ServodClientParser))

    def test_parse_cmdline(self):
        """Test _parse_cmdline()."""
        dp = dut_power.DutPower()
        parser = dp._build_parser()

        default = dp._parse_cmdline(parser, [])
        self.assertListEqual(
            [
                default.powerstate,
                default.board,
                default.fast,
                default.wait,
                default.time,
                default.filter_out,
                default.filter,
                default.adc_rate,
                default.adc_accum_rate,
                default.vbat_rate,
                default.no_output,
                default.outdir,
                default.message,
                default.save_raw_data,
                default.save_summary,
                default.save_json,
                default.save_logs,
                default.save_all,
                default.visualization,
                default.visualization_port,
            ],
            [
                "S?",
                "unknown",
                False,
                0,
                60,
                None,
                None,
                1,
                30,
                60,
                False,
                None,
                None,
                False,
                True,
                False,
                True,
                False,
                False,
                9998,
            ],
        )
        for state in measure_power.POWERSTATES:
            self.assertEqual(
                dp._parse_cmdline(parser, (["--powerstate", state])).powerstate, state
            )
        self.assertEqual(dp._parse_cmdline(parser, (["-b", "hana"])).board, "hana")
        self.assertEqual(dp._parse_cmdline(parser, (["--board", "hana"])).board, "hana")
        self.assertTrue(dp._parse_cmdline(parser, (["-f"])).fast)
        self.assertTrue(dp._parse_cmdline(parser, (["--fast"])).fast)
        self.assertEqual(dp._parse_cmdline(parser, (["-w", "3.2"])).wait, 3.2)
        self.assertEqual(dp._parse_cmdline(parser, (["--wait", "3.2"])).wait, 3.2)
        self.assertEqual(dp._parse_cmdline(parser, (["-t", "32.2"])).time, 32.2)
        self.assertEqual(dp._parse_cmdline(parser, (["--time", "32.2"])).time, 32.2)
        self.assertEqual(
            dp._parse_cmdline(parser, (["--filter-out", "regex"])).filter_out, "regex"
        )
        self.assertEqual(
            dp._parse_cmdline(parser, (["--filter", "regex"])).filter, "regex"
        )
        self.assertEqual(
            dp._parse_cmdline(parser, (["--ina-rate", "23.3"])).adc_rate, 23.3
        )
        self.assertEqual(
            dp._parse_cmdline(parser, (["--adc-rate", "23.3"])).adc_rate, 23.3
        )
        self.assertEqual(
            dp._parse_cmdline(parser, (["--adc-accum-rate", "23.3"])).adc_accum_rate,
            23.3,
        )
        self.assertEqual(
            dp._parse_cmdline(parser, (["--vbat-rate", "23.3"])).vbat_rate, 23.3
        )
        self.assertTrue(dp._parse_cmdline(parser, (["--no-output"])).no_output)
        self.assertEqual(dp._parse_cmdline(parser, (["-o", "dir"])).outdir, "dir")
        self.assertEqual(dp._parse_cmdline(parser, (["--outdir", "dir"])).outdir, "dir")
        self.assertEqual(dp._parse_cmdline(parser, (["-m", "msg"])).message, "msg")
        self.assertEqual(
            dp._parse_cmdline(parser, (["--message", "msg"])).message, "msg"
        )
        self.assertTrue(dp._parse_cmdline(parser, (["--save-raw-data"])).save_raw_data)
        self.assertFalse(
            dp._parse_cmdline(parser, (["--no-save-raw-data"])).save_raw_data
        )
        self.assertTrue(dp._parse_cmdline(parser, (["--save-summary"])).save_summary)
        self.assertFalse(
            dp._parse_cmdline(parser, (["--no-save-summary"])).save_summary
        )
        self.assertTrue(dp._parse_cmdline(parser, (["--save-json"])).save_json)
        self.assertFalse(dp._parse_cmdline(parser, (["--no-save-json"])).save_json)
        self.assertTrue(dp._parse_cmdline(parser, (["--save-logs"])).save_logs)
        self.assertFalse(dp._parse_cmdline(parser, (["--no-save-logs"])).save_logs)
        self.assertTrue(dp._parse_cmdline(parser, (["--save-all"])).save_all)
        self.assertTrue(dp._parse_cmdline(parser, (["--save-all"])).save_logs)
        self.assertTrue(dp._parse_cmdline(parser, (["--save-all"])).save_raw_data)
        self.assertTrue(dp._parse_cmdline(parser, (["--save-all"])).save_summary)
        self.assertTrue(dp._parse_cmdline(parser, (["--save-all"])).save_json)
        self.assertTrue(dp._parse_cmdline(parser, (["--visualization"])).visualization)
        self.assertEqual(
            dp._parse_cmdline(
                parser, (["--visualization-port", "2233"])
            ).visualization_port,
            2233,
        )

    def test_setup_logging(self):
        """Test _setup_logging()."""
        dp = dut_power.DutPower()
        args = argparse.Namespace()
        args.port = None
        args.debug = False
        args.no_output = False
        args.save_logs = True
        args.time = 10
        args.adc_accum_rate = 12
        tmplogfile = tempfile.NamedTemporaryFile(mode="w+")
        with unittest.mock.patch(
            "tempfile.NamedTemporaryFile",
            unittest.mock.MagicMock(return_value=tmplogfile),
        ):
            dp._setup_logging(args)

        self.assertEqual(dp.pm_logger.getEffectiveLevel(), logging.INFO)
        self.assertEqual(len(dp.pm_logger.handlers), 2)
        self.assertEqual(dp.pm_logger.handlers[0].stream, sys.stdout)
        self.assertEqual(dp.pm_logger.handlers[1].stream, tmplogfile)
        self.assertEqual(args.adc_accum_rate, 8)
        self.assertEqual(dp.tmplogfile, tmplogfile)

    @unittest.mock.patch(
        "measurement_tools.measure_power.PowerMeasurement.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    @unittest.mock.patch(
        "measurement_tools.http_server.ThreadedTCPServer.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    @unittest.mock.patch(
        "measurement_tools.http_server.HttpRequestHandler.is_port_used",
        unittest.mock.MagicMock(return_value=False),
    )
    @unittest.mock.patch(
        "measurement_tools.http_server.HttpRequestHandler.get_visualization_html_exist",
        unittest.mock.MagicMock(return_value="path"),
    )
    @unittest.mock.patch(
        "threading.Thread.__init__", unittest.mock.MagicMock(return_value=None)
    )
    @unittest.mock.patch("threading.Thread.start", unittest.mock.MagicMock())
    def test_setup_visualization(self):
        """Test _setup_visualization()."""
        dp = dut_power.DutPower()
        dp.pm_logger = logging.getLogger("")
        args = argparse.Namespace()
        args.visualization_port = 0
        pm = measure_power.PowerMeasurement()
        http_server.ThreadedTCPServer.server_address = ("localhost", 9998)

        dp._setup_visualization(args, pm)

        self.assertTrue(isinstance(dp.power_data, dut_power_data.DataSampler))
        self.assertEqual(dp.power_data._pm, pm)
        self.assertTrue(
            isinstance(dp.http_server_handler, http_server.HttpRequestHandler)
        )
        self.assertEqual(dp.http_server_handler._data_sampler, dp.power_data)
        self.assertTrue(
            isinstance(dp.visualization_server, http_server.ThreadedTCPServer)
        )
        http_server.ThreadedTCPServer.__init__.assert_called_once_with(
            ("localhost", args.visualization_port), dp.http_server_handler
        )
        threading.Thread.__init__.assert_called_once_with(
            target=dp.visualization_server.serve_forever, daemon=True
        )
        threading.Thread.start.assert_called_once()

    @unittest.mock.patch(
        "measurement_tools.measure_power.PowerMeasurement.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    @unittest.mock.patch(
        "measurement_tools.http_server.HttpRequestHandler.is_port_used",
        unittest.mock.MagicMock(return_value=True),
    )
    def test_setup_visualization_port_used(self):
        """Test _setup_visualization() fails if the http server port is already used."""
        dp = dut_power.DutPower()
        dp.pm_logger = logging.getLogger("")
        args = argparse.Namespace()
        args.visualization_port = 0
        pm = measure_power.PowerMeasurement()

        with self.assertRaises(SystemExit) as exc:
            dp._setup_visualization(args, pm)
        self.assertEqual(exc.exception.code, 1)

    @unittest.mock.patch(
        "measurement_tools.measure_power.PowerMeasurement.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    @unittest.mock.patch(
        "measurement_tools.http_server.HttpRequestHandler.is_port_used",
        unittest.mock.MagicMock(return_value=False),
    )
    @unittest.mock.patch(
        "measurement_tools.http_server.HttpRequestHandler.get_visualization_html_exist",
        unittest.mock.MagicMock(return_value=None),
    )
    def test_setup_visualization_no_visualization_file(self):
        """Test _setup_visualization() if there is no visualization file."""
        dp = dut_power.DutPower()
        dp.pm_logger = logging.getLogger("")
        args = argparse.Namespace()
        args.visualization_port = 0
        pm = measure_power.PowerMeasurement()

        with self.assertRaises(SystemExit) as exc:
            dp._setup_visualization(args, pm)
        self.assertEqual(exc.exception.code, 1)

    @unittest.mock.patch(
        "measurement_tools.measure_power.PowerMeasurement.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    @unittest.mock.patch(
        "measurement_tools.http_server.ThreadedTCPServer.__init__",
        unittest.mock.MagicMock(side_effect=NotImplementedError()),
    )
    @unittest.mock.patch(
        "measurement_tools.http_server.HttpRequestHandler.is_port_used",
        unittest.mock.MagicMock(return_value=False),
    )
    @unittest.mock.patch(
        "measurement_tools.http_server.HttpRequestHandler.get_visualization_html_exist",
        unittest.mock.MagicMock(return_value="path"),
    )
    def test_setup_visualization_server_failure(self):
        """Test _setup_visualization() if http server fails setup."""
        dp = dut_power.DutPower()
        dp.pm_logger = logging.getLogger("")
        args = argparse.Namespace()
        args.visualization_port = 0
        pm = measure_power.PowerMeasurement()

        with self.assertRaises(SystemExit) as exc:
            dp._setup_visualization(args, pm)
        self.assertEqual(exc.exception.code, 1)

    @unittest.mock.patch(
        "measurement_tools.dut_power.ProgressPrinter.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    @unittest.mock.patch(
        "measurement_tools.dut_power.ProgressPrinter.start", unittest.mock.MagicMock()
    )
    @unittest.mock.patch(
        "measurement_tools.measure_power.PowerMeasurement.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    @unittest.mock.patch(
        "threading.Thread.__init__", unittest.mock.MagicMock(return_value=None)
    )
    @unittest.mock.patch("threading.Thread.start", unittest.mock.MagicMock())
    @unittest.mock.patch(
        "threading.Event.__init__", unittest.mock.MagicMock(return_value=None)
    )
    @unittest.mock.patch("threading.Event.set", unittest.mock.MagicMock())
    @unittest.mock.patch("threading.Event.wait", unittest.mock.MagicMock())
    @unittest.mock.patch("signal.signal", unittest.mock.MagicMock())
    def test_measure_power_visualization(self):
        """Test _measure_power()."""
        dp = dut_power.DutPower()
        dp.visualization_server = unittest.mock.MagicMock()
        dp.visualization_server.server_close = unittest.mock.MagicMock()
        dp.visualization_server.shutdown = unittest.mock.MagicMock()
        args = argparse.Namespace()
        args.visualization = True
        args.no_output = False
        args.powerstate = measure_power.DEFAULT_POWERSTATE
        args.wait = 10
        args.time = 60
        pm = measure_power.PowerMeasurement()
        pm.measure_power = unittest.mock.MagicMock(return_value=threading.Event())
        pm.finish_measurement = unittest.mock.MagicMock()
        dp.power_data = dut_power_data.DataSampler(pm)
        dp.power_data.sample_generator = unittest.mock.MagicMock()

        dp._measure_power(args, pm)

        pm.measure_power.assert_called_once_with(
            wait=args.wait, powerstate=args.powerstate
        )
        signal.signal.assert_has_calls(
            [
                unittest.mock.call(signal.SIGINT, unittest.mock.ANY),
                unittest.mock.call(signal.SIGTERM, unittest.mock.ANY),
            ]
        )
        dut_power.ProgressPrinter.__init__.assert_has_calls(
            [
                unittest.mock.call(
                    marker=dut_power.ProgressPrinter.WAIT_MARKER,
                    stop_signal=unittest.mock.ANY,
                    max_duration=args.wait,
                ),
                unittest.mock.call(
                    stop_signal=unittest.mock.ANY, max_duration=args.time
                ),
            ]
        )
        dut_power.ProgressPrinter.start.assert_has_calls(
            [unittest.mock.call(), unittest.mock.call()]
        )
        threading.Event.wait.assert_has_calls(
            [unittest.mock.call(), unittest.mock.call(args.wait), unittest.mock.call()],
            any_order=True,
        )  # unittest framework also uses threading.Event.wait
        threading.Event.set.assert_has_calls(
            [unittest.mock.call(), unittest.mock.call()]
        )

    @unittest.mock.patch(
        "measurement_tools.measure_power.PowerMeasurement.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    def test_save_results(self):
        """Test _save_results()."""
        dp = dut_power.DutPower()
        dp.pm_logger = logging.getLogger("")
        dp.tmplogfile = tempfile.NamedTemporaryFile(mode="w+")
        dp.http_server_handler = unittest.mock.MagicMock()
        args = argparse.Namespace()
        args.save_summary = True
        args.save_raw_data = True
        args.save_json = True
        args.save_logs = True
        args.visualization = True
        args.outdir = "dir"
        args.message = "msg"
        pm = measure_power.PowerMeasurement()
        pm._outdir = None
        pm.save_summary = unittest.mock.MagicMock()
        pm.save_raw_data = unittest.mock.MagicMock()
        pm.save_summary_json = unittest.mock.MagicMock()
        dp.http_server_handler.save_visualization_html = unittest.mock.MagicMock()

        with unittest.mock.patch(
            "os.path.isdir", unittest.mock.MagicMock(return_value=True)
        ):
            with unittest.mock.patch(
                "os.path.join", unittest.mock.MagicMock(return_value="logfile")
            ):
                with unittest.mock.patch("shutil.move", unittest.mock.MagicMock()):
                    dp._save_results(args, pm)

                    pm.save_summary.assert_called_once_with("dir", "msg")
                    pm.save_raw_data.assert_called_once_with("dir")
                    pm.save_summary_json.assert_called_once_with("dir")
                    shutil.move.assert_called_once_with(dp.tmplogfile.name, "logfile")
                    dp.http_server_handler.save_visualization_html.assert_called_once_with(  # pylint: disable=line-too-long
                        None
                    )

    @unittest.mock.patch(
        "measurement_tools.measure_power.PowerMeasurement.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    @unittest.mock.patch(
        "measurement_tools.measure_power.PowerMeasurement.process_measurement",
        unittest.mock.MagicMock(),
    )
    @unittest.mock.patch(
        "measurement_tools.measure_power.PowerMeasurement.display_summary",
        unittest.mock.MagicMock(),
    )
    def test_main(self):
        """Test main()."""
        dp = dut_power.DutPower()
        args = argparse.Namespace()
        args.visualization = True
        dp._build_parser = unittest.mock.MagicMock()
        dp._setup_logging = unittest.mock.MagicMock()
        dp._build_parser = unittest.mock.MagicMock()
        dp._setup_visualization = unittest.mock.MagicMock()
        dp._measure_power = unittest.mock.MagicMock()
        dp._save_results = unittest.mock.MagicMock()

        dp.main(["--visualization"])

        dp._build_parser.assert_called_once()
        dp._setup_logging.assert_called_once()
        dp._setup_visualization.assert_called_once()
        dp._measure_power.assert_called_once()
        measure_power.PowerMeasurement.process_measurement.assert_called_once()
        measure_power.PowerMeasurement.display_summary.assert_called_once()
        dp._save_results.assert_called_once()

    @unittest.mock.patch(
        "measurement_tools.measure_power.PowerMeasurement.__init__",
        unittest.mock.MagicMock(side_effect=measure_power.NoSourceError()),
    )
    def test_main_failure(self):
        """Test main() with measure_power failure."""
        dp = dut_power.DutPower()
        dp.pm_logger = logging.getLogger("")
        args = argparse.Namespace()
        args.visualization = True
        dp._build_parser = unittest.mock.MagicMock()
        dp._setup_logging = unittest.mock.MagicMock()
        dp._build_parser = unittest.mock.MagicMock()

        with self.assertRaises(SystemExit) as exc:
            dp.main([])
        self.assertEqual(exc.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
