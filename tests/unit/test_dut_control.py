# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Unit-tests to ensure that dut-control works as intended."""

import collections
import unittest
import unittest.mock

from servo.common import servo_parsing
from servo.core import client
from servo.core import dut_control


class TestDutControl(unittest.TestCase):
    """Test dut_control.py."""

    def setUp(self):
        """Set up for each unit test."""
        unittest.TestCase.setUp(self)
        dut_control._START_TIME = 0

    def test_build_parser(self):
        """Test parser is built properly."""
        parser = dut_control._build_parser()
        self.assertTrue(isinstance(parser, servo_parsing.ServodClientParser))

        default = parser.parse_args([])
        self.assertListEqual(
            [
                default.info,
                default.hwinit,
                default.value_only,
                default.get_all,
                default.gnuplot,
                default.verbose,
                default.repeat,
                default.time_in_secs,
                default.print_time,
                default.sleep_msecs,
            ],
            [False, False, False, False, False, False, 1, 0.0, False, 0.0],
        )
        self.assertTrue(parser.parse_args(["-i"]).info)
        self.assertTrue(parser.parse_args(["--info"]).info)
        self.assertTrue(parser.parse_args(["--hwinit"]).hwinit)
        self.assertTrue(parser.parse_args(["-o"]).value_only)
        self.assertTrue(parser.parse_args(["--value_only"]).value_only)
        self.assertTrue(parser.parse_args(["--get-all"]).get_all)
        self.assertTrue(parser.parse_args(["-g"]).gnuplot)
        self.assertTrue(parser.parse_args(["--gnuplot"]).gnuplot)
        self.assertTrue(parser.parse_args(["--verbose"]).verbose)
        self.assertEqual(parser.parse_args(["-r", "2"]).repeat, 2)
        self.assertEqual(parser.parse_args(["--repeat", "2"]).repeat, 2)
        self.assertEqual(parser.parse_args(["-t", "2.2"]).time_in_secs, 2.2)
        self.assertEqual(parser.parse_args(["--time_in_secs", "2.2"]).time_in_secs, 2.2)
        self.assertTrue(parser.parse_args(["-y"]).print_time)
        self.assertTrue(parser.parse_args(["--print_time"]).print_time)
        self.assertEqual(parser.parse_args(["-z", "3.3"]).sleep_msecs, 3.3)
        self.assertEqual(parser.parse_args(["--sleep_msecs", "3.3"]).sleep_msecs, 3.3)

    def test_pretty_print_result(self):
        """Test _pretty_print_result."""
        self.assertEqual(dut_control._pretty_print_result(["1", "2", "3"]), "1, 2, 3")
        self.assertEqual(
            dut_control._pretty_print_result({"0": "yes", "2": "no"}), "0: yes\n2: no"
        )

    def test_do_iteration_info(self):
        """Test do_iteration."""
        requests = ["cold_reset", "cold_reset:on", "cold_reset"]
        options = dut_control._build_parser().parse_args(["--info"])
        sclient = client.ServoClient()
        sclient.set_get_all = unittest.mock.MagicMock(return_value=["off", "on", "off"])
        sclient.doc = unittest.mock.MagicMock(return_value="control_doc")
        stats = collections.defaultdict(list)
        res = dut_control.do_iteration(requests, options, sclient, stats)
        self.assertEqual(res, "cold_reset:control_doc\ncold_reset:on:control_doc")

    @unittest.mock.patch("time.time", unittest.mock.MagicMock(return_value=12345))
    def test_do_iteration_verbose(self):
        """Test do_iteration."""
        requests = ["cold_reset", "cold_reset:on", "cold_reset"]
        options = dut_control._build_parser().parse_args(["--print_time", "--verbose"])
        sclient = client.ServoClient()
        sclient.set_get_all = unittest.mock.MagicMock(return_value=["off", "on", "off"])
        stats = collections.defaultdict(list)
        res = dut_control.do_iteration(requests, options, sclient, stats)
        self.assertEqual(
            res,
            "12345.0000 GET cold_reset -> off\n"
            "12345.0000 SET cold_reset:on -> on\n"
            "12345.0000 GET cold_reset -> off",
        )

    def test_do_iteration_gnuplot(self):
        """Test do_iteration."""
        requests = ["cold_reset", "cold_reset:on", "cold_reset"]
        options = dut_control._build_parser().parse_args(["--gnuplot"])
        sclient = client.ServoClient()
        sclient.set_get_all = unittest.mock.MagicMock(return_value=["off", "on", "off"])
        stats = collections.defaultdict(list)
        res = dut_control.do_iteration(requests, options, sclient, stats)
        self.assertEqual(res, "off off")

    def test_do_iteration_value_only(self):
        """Test do_iteration."""
        requests = ["cold_reset", "cold_reset:on", "cold_reset"]
        options = dut_control._build_parser().parse_args(["--value_only"])
        sclient = client.ServoClient()
        sclient.set_get_all = unittest.mock.MagicMock(return_value=["off", "on", "off"])
        stats = collections.defaultdict(list)
        res = dut_control.do_iteration(requests, options, sclient, stats)
        self.assertEqual(res, "off\noff")

    @unittest.mock.patch("time.time", unittest.mock.MagicMock(return_value=12345))
    def test_iterate_repeat(self):
        """Test iterate() that repeats certain times."""
        dut_control._print_gnuplot_header = unittest.mock.MagicMock()
        dut_control.do_iteration = unittest.mock.MagicMock(return_value="3")
        dut_control.display_stats = unittest.mock.MagicMock()

        controls = ["cold_reset", "cold_reset:on", "cold_reset"]
        options = dut_control._build_parser().parse_args(
            ["--gnuplot", "--print_time", "-r 3"]
        )
        sclient = client.ServoClient()
        dut_control.iterate(controls, options, sclient)

        dut_control._print_gnuplot_header.assert_called_with(controls)
        dut_control.do_iteration.assert_has_calls(
            [
                unittest.mock.call(
                    controls, options, sclient, collections.defaultdict(list)
                ),
                unittest.mock.call(
                    controls, options, sclient, collections.defaultdict(list)
                ),
                unittest.mock.call(
                    controls, options, sclient, collections.defaultdict(list)
                ),
            ]
        )
        dut_control.display_stats.assert_called_with(
            collections.defaultdict(list), prefix=dut_control.GNUPLOT_PREFIX
        )

    @unittest.mock.patch(
        "time.time", unittest.mock.MagicMock(side_effect=[1, 2, 3, 4, 5, 6])
    )
    def test_iterate_time_in_secs(self):
        """Test iterate() that iterates in a timed loop."""
        dut_control._print_gnuplot_header = unittest.mock.MagicMock()
        dut_control.do_iteration = unittest.mock.MagicMock(return_value="3")
        dut_control.display_stats = unittest.mock.MagicMock()

        controls = ["cold_reset", "cold_reset:on", "cold_reset"]
        options = dut_control._build_parser().parse_args(["--time_in_secs", "2.2"])
        sclient = client.ServoClient()
        dut_control.iterate(controls, options, sclient)
        self.assertEqual(dut_control.do_iteration.call_count, 3)
        dut_control.do_iteration.assert_has_calls(
            [
                unittest.mock.call(
                    controls, options, sclient, collections.defaultdict(list)
                ),
                unittest.mock.call(
                    controls, options, sclient, collections.defaultdict(list)
                ),
                unittest.mock.call(
                    controls, options, sclient, collections.defaultdict(list)
                ),
            ]
        )
        dut_control.display_stats.assert_called_with(
            collections.defaultdict(list), prefix=dut_control.STATS_PREFIX
        )

    def test_real_main_info(self):
        """Test real_main."""
        client.ServoClient.doc_all = unittest.mock.MagicMock()
        dut_control.real_main(["--debug", "-i"])

        client.ServoClient.doc_all.assert_called_once()

    def test_real_main_hwinit(self):
        """Test real_main."""
        client.ServoClient.hwinit = unittest.mock.MagicMock()
        dut_control.real_main(["--debug", "--hwinit"])

        client.ServoClient.hwinit.assert_called_once()

    def test_real_main_get_all(self):
        """Test real_main."""
        client.ServoClient.get_all = unittest.mock.MagicMock()
        dut_control.real_main(["--debug", "--get-all"])

        client.ServoClient.get_all.assert_called_once()

    def test_real_main(self):
        """Test real_main."""
        dut_control.iterate = unittest.mock.MagicMock()
        dut_control.real_main(["--debug", "cold_reset", "cold_reset:on"])

        dut_control.iterate.assert_called_once_with(
            ["cold_reset", "cold_reset:on"], unittest.mock.ANY, unittest.mock.ANY
        )


if __name__ == "__main__":
    unittest.main()
