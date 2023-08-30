# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Test measure_power works as intended."""

import math
import threading
import time
import unittest
import unittest.mock

from servo import client
from servo import measure_power
from servo.utils import stats_manager
from servo.utils import timelined_stats_manager


class TestServodPowerTracker(unittest.TestCase):
    """Test ServodPowerTracker."""

    def setUp(self):
        """Set up for each unit test."""
        unittest.TestCase.setUp(self)
        client.ServoClient.__init__ = unittest.mock.MagicMock(return_value=None)
        with unittest.mock.patch(
            "servo.utils.timelined_stats_manager.TimelinedStatsManager.__init__",
            unittest.mock.MagicMock(return_value=None),
        ):
            self.tracker = measure_power.ServodPowerTracker(
                "localhost",
                9990,
                threading.Event(),
                ["avg_rail_name_avg_mw", "avg_rail_name2_avg_mw"],
                2,
            )

    def test_empty(self):
        """Test empty()."""
        self.assertFalse(self.tracker.empty)
        self.tracker._ctrls = []
        self.assertTrue(self.tracker.empty)

    def test_rail_name(self):
        """Test _rail_name()."""
        self.assertEqual(self.tracker._rail_name("avg_rail_name_avg_mw"), "rail_name")

    def test_rails(self):
        """Test rails()."""
        self.assertEqual(self.tracker.rails, ["rail_name", "rail_name2"])

    def test_remove_rail(self):
        """Test remove_rail()."""
        self.tracker.remove_rail("rail_name")
        self.assertEqual(self.tracker._ctrls, ["avg_rail_name2_avg_mw"])

    def test_verify(self):
        """Test verify()."""
        self.tracker._sclient.set_get_all = unittest.mock.MagicMock()
        self.tracker.verify()
        self.tracker._sclient.set_get_all.assert_called_once_with(self.tracker._ctrls)

    def test_verify_fail(self):
        """Test verify() failure scenario."""
        self.tracker._sclient.set_get_all = unittest.mock.MagicMock(
            side_effect=[client.ServoClientError(None, None)]
        )
        with self.assertRaises(measure_power.PowerTrackerError) as cm:
            self.tracker.verify()
        self.assertEqual(
            str(cm.exception),
            "Failed to test servod commands. Tested: ['avg_rail_name_avg_mw', 'avg_rail_name2_avg_mw']",
        )

    def test_run(self):
        """Test run()."""
        self.tracker._skip_first = True
        self.tracker._stop_signal.is_set = unittest.mock.MagicMock(
            side_effect=[False, False, False, True]
        )
        self.tracker._stop_signal.wait = unittest.mock.MagicMock()
        self.tracker._sample_ctrls = unittest.mock.MagicMock(
            side_effect=[
                ([("rail_name", 1), ("rail_name2", 2), ("Sample_msecs", 43.3)], 33.2),
                ([("rail_name", 3), ("rail_name2", 4), ("Sample_msecs", 43.5)], 33.1),
            ]
        )
        self.tracker._stats.AddSamples = unittest.mock.MagicMock()
        self.tracker.set_sample_data = unittest.mock.MagicMock()

        self.tracker.run()

        self.tracker._stop_signal.wait.assert_has_calls(
            [
                unittest.mock.call(2.0),
                unittest.mock.call(1.9668),
                unittest.mock.call(1.9669),
            ]
        )
        self.tracker._sample_ctrls.assert_has_calls(
            [
                unittest.mock.call(["avg_rail_name_avg_mw", "avg_rail_name2_avg_mw"]),
                unittest.mock.call(["avg_rail_name_avg_mw", "avg_rail_name2_avg_mw"]),
            ]
        )
        self.tracker._stats.AddSamples.assert_has_calls(
            [
                unittest.mock.call(
                    [("rail_name", 1), ("rail_name2", 2), ("Sample_msecs", 43.3)]
                ),
                unittest.mock.call(
                    [("rail_name", 3), ("rail_name2", 4), ("Sample_msecs", 43.5)]
                ),
            ]
        )
        self.tracker.set_sample_data.assert_has_calls(
            [
                unittest.mock.call(
                    [("rail_name", 1), ("rail_name2", 2), ("Sample_msecs", 43.3)]
                ),
                unittest.mock.call(
                    [("rail_name", 3), ("rail_name2", 4), ("Sample_msecs", 43.5)]
                ),
            ]
        )

    def test_set_sample_data(self):
        """Test set_sample_data()."""
        self.tracker._sample_data = []
        self.tracker.set_sample_data(["current"])
        self.assertEqual(self.tracker._sample_data, ["current"])

    def test_get_sample_data(self):
        """Test get_sample_data()."""
        self.tracker._previous_sample_data = ["previous"]
        self.tracker._sample_data = ["current"]
        self.assertEqual(self.tracker.get_sample_data(), ["current"])
        self.assertEqual(self.tracker._previous_sample_data, ["current"])

    def test_get_sample_data_no_data(self):
        """Test get_sample_data()."""
        self.tracker._previous_sample_data = ["previous"]
        self.tracker._sample_data = []
        self.assertEqual(self.tracker.get_sample_data(), ["previous"])
        self.assertEqual(self.tracker._previous_sample_data, ["previous"])

    def test_clean_sample_data(self):
        """Test clean_sample_data()."""
        self.tracker._sample_data = ["testing"]
        self.tracker.clean_sample_data()
        self.assertEqual(self.tracker._sample_data, [])

    @unittest.mock.patch("time.time", unittest.mock.MagicMock(return_value=12345))
    def test_sample_ctrls(self):
        """Test _sample_ctrls()."""
        self.tracker._sclient.set_get_all = unittest.mock.MagicMock(return_value=[1, 2])
        res = self.tracker._sample_ctrls(
            ["avg_rail_name_avg_mw", "avg_rail_name2_avg_mw"]
        )
        self.tracker._sclient.set_get_all.assert_called_once_with(
            ["avg_rail_name_avg_mw", "avg_rail_name2_avg_mw"]
        )
        self.assertEqual(
            res, ([("rail_name", 1), ("rail_name2", 2), ("Sample_msecs", 0)], 0)
        )

    @unittest.mock.patch("time.time", unittest.mock.MagicMock(return_value=12345))
    def test_sample_ctrls_failure(self):
        """Test _sample_ctrls() failure scenario."""
        self.tracker._sclient.set_get_all = unittest.mock.MagicMock(
            side_effect=[client.ServoClientError(None, None)]
        )
        (sample_tuples, duration_ms) = self.tracker._sample_ctrls(
            ["avg_rail_name_avg_mw", "avg_rail_name2_avg_mw"]
        )
        self.tracker._sclient.set_get_all.assert_called_once_with(
            ["avg_rail_name_avg_mw", "avg_rail_name2_avg_mw"]
        )
        self.assertEqual(sample_tuples[0][0], "rail_name")
        self.assertTrue(math.isnan(sample_tuples[0][1]))
        self.assertEqual(sample_tuples[1][0], "rail_name2")
        self.assertTrue(math.isnan(sample_tuples[1][1]))
        self.assertEqual(sample_tuples[2], ("Sample_msecs", 0))
        self.assertEqual(duration_ms, 0)

    def test_process_measurement(self):
        """Test process_measurement()."""
        self.tracker._stats.TrimSamples = unittest.mock.MagicMock()
        self.tracker._stats.CalculateStats = unittest.mock.MagicMock()

        res = self.tracker.process_measurement(123, 456)
        self.tracker._stats.TrimSamples.assert_called_once_with(123, 456)
        self.tracker._stats.CalculateStats.assert_called_once()
        self.assertEqual(res, self.tracker._stats)

    def test_str(self):
        """Test __str__()."""
        self.assertEqual(str(self.tracker), "unnamed (mw)")


class TestHighResServodPowerTracker(unittest.TestCase):
    """Test HighResServodPowerTracker."""

    def setUp(self):
        """Set up for each unit test."""
        unittest.TestCase.setUp(self)
        client.ServoClient.__init__ = unittest.mock.MagicMock(return_value=None)
        with unittest.mock.patch(
            "servo.utils.timelined_stats_manager.TimelinedStatsManager.__init__",
            unittest.mock.MagicMock(return_value=None),
        ):
            self.tracker = measure_power.HighResServodPowerTracker(
                "localhost",
                9990,
                threading.Event(),
                ["avg_rail_name_avg_mw", "avg_rail_name2_avg_mw"],
                2,
            )

    def test_run(self):
        """Test run()."""
        self.tracker._stop_signal.is_set = unittest.mock.MagicMock(
            side_effect=[False, False, False, True]
        )
        self.tracker._stop_signal.wait = unittest.mock.MagicMock()
        self.tracker._sample_ctrls = unittest.mock.MagicMock(
            side_effect=[
                ([("rail_name", 1), ("rail_name2", 2), ("Sample_msecs", 43.3)], 33.2),
                ([("rail_name", 3), ("rail_name2", 4), ("Sample_msecs", 43.5)], 33.1),
                ([("rail_name", 5), ("rail_name2", 6), ("Sample_msecs", 43.5)], 33.1),
            ]
        )
        self.tracker._record_mean_samples = unittest.mock.MagicMock()
        self.tracker.set_sample_data = unittest.mock.MagicMock()

        with unittest.mock.patch(
            "time.time",
            unittest.mock.MagicMock(side_effect=[12345, 12347, 12349, 12349]),
        ):
            self.tracker.run()

        self.tracker._sample_ctrls.assert_has_calls(
            [
                unittest.mock.call(["avg_rail_name_avg_mw", "avg_rail_name2_avg_mw"]),
                unittest.mock.call(["avg_rail_name_avg_mw", "avg_rail_name2_avg_mw"]),
                unittest.mock.call(["avg_rail_name_avg_mw", "avg_rail_name2_avg_mw"]),
            ]
        )
        self.assertEqual(self.tracker._record_mean_samples.call_count, 3)
        self.tracker.set_sample_data.assert_has_calls(
            [
                unittest.mock.call(
                    [("rail_name", 1), ("rail_name2", 2), ("Sample_msecs", 43.3)]
                ),
                unittest.mock.call(
                    [("rail_name", 3), ("rail_name2", 4), ("Sample_msecs", 43.5)]
                ),
            ]
        )

    def test_record_mean_samples(self):
        """Test _record_mean_samples()."""
        temp_stats = stats_manager.StatsManager()
        temp_stats.AddSample("rail_name", 1)
        temp_stats.AddSample("rail_name2", 2)
        temp_stats.AddSample("rail_name", 3)
        temp_stats.AddSample("rail_name2", 4)
        self.tracker._stats.AddSamples = unittest.mock.MagicMock()

        self.tracker._record_mean_samples(temp_stats)
        self.tracker._stats.AddSamples.assert_called_once_with(
            [("rail_name", 2.0), ("rail_name2", 3.0)]
        )

    def test_process_measurement(self):
        """Test process_measurement()."""
        self.tracker._stats.TrimSamples = unittest.mock.MagicMock()
        self.tracker._stats.CalculateStats = unittest.mock.MagicMock()

        res = self.tracker.process_measurement(123, 456)
        self.tracker._stats.TrimSamples.assert_called_once_with(123, 456, 1)
        self.tracker._stats.CalculateStats.assert_called_once()
        self.assertEqual(res, self.tracker._stats)


class TestOnboardADCPowerTracker(unittest.TestCase):
    """Test OnboardADCPowerTracker."""

    def setUp(self):
        """Set up for each unit test."""
        unittest.TestCase.setUp(self)
        client.ServoClient.__init__ = unittest.mock.MagicMock(return_value=None)
        results = {
            "power_rails": ["ppchg5_mw", "ppservo5_mw", "ppdut5_mw"],
            "adc_ez_config_ctrls": [
                "ppchg5_ez_config",
                "ppservo5_ez_config",
                "ppdut5_ez_config",
            ],
        }
        client.ServoClient.get = unittest.mock.MagicMock(
            side_effect=lambda x: results[x]
        )
        with unittest.mock.patch(
            "servo.utils.timelined_stats_manager.TimelinedStatsManager.__init__",
            unittest.mock.MagicMock(return_value=None),
        ):
            self.tracker = measure_power.OnboardADCPowerTracker(
                "localhost",
                9990,
                threading.Event(),
                measure_power.RegexFilter(None, "ppd.*"),
                2,
            )

    def test_prepare(self):
        """Test prepare()."""
        self.tracker._sclient.set_get_all = unittest.mock.MagicMock()
        self.tracker.prepare()
        self.tracker._sclient.set_get_all.assert_called_once_with(
            ["ppchg5_ez_config:on", "ppservo5_ez_config:on"]
        )

    def test_run(self):
        """Test run()."""
        self.tracker._stop_signal.is_set = unittest.mock.MagicMock(
            side_effect=[False, False, False, True]
        )
        self.tracker._stop_signal.wait = unittest.mock.MagicMock()
        self.tracker._sample_ctrls = unittest.mock.MagicMock(
            side_effect=[
                ([("rail_name", 1), ("rail_name2", 2), ("Sample_msecs", 43.3)], 33.2),
                ([("rail_name", 3), ("rail_name2", 4), ("Sample_msecs", 43.5)], 33.1),
                ([("rail_name", 5), ("rail_name2", 6), ("Sample_msecs", 43.5)], 33.1),
            ]
        )
        self.tracker._record_mean_samples = unittest.mock.MagicMock()
        self.tracker.set_sample_data = unittest.mock.MagicMock()

        with unittest.mock.patch(
            "time.time",
            unittest.mock.MagicMock(side_effect=[12345, 12347, 12349, 12349]),
        ):
            self.tracker.run()

        self.tracker._sample_ctrls.assert_has_calls(
            [
                unittest.mock.call(["ppchg5_mw", "ppservo5_mw"]),
                unittest.mock.call(["ppchg5_mw", "ppservo5_mw"]),
                unittest.mock.call(["ppchg5_mw", "ppservo5_mw"]),
            ]
        )
        self.assertEqual(self.tracker._record_mean_samples.call_count, 3)
        self.tracker.set_sample_data.assert_has_calls(
            [
                unittest.mock.call(
                    [("rail_name", 1), ("rail_name2", 2), ("Sample_msecs", 43.3)]
                ),
                unittest.mock.call(
                    [("rail_name", 3), ("rail_name2", 4), ("Sample_msecs", 43.5)]
                ),
            ]
        )


class TestOnboardADCAccumPowerTracker(unittest.TestCase):
    """Test OnboardADCAccumPowerTracker."""

    def setUp(self):
        """Set up for each unit test."""
        unittest.TestCase.setUp(self)
        client.ServoClient.__init__ = unittest.mock.MagicMock(return_value=None)
        results = {
            "avg_power_rails": ["ppchg5_mw", "ppservo5_mw"],
            "accum_clear_ctrls": ["ppdut5_mw"],
            "adc_ez_config_ctrls": [
                "ppchg5_ez_config",
                "ppservo5_ez_config",
                "ppdut5_ez_config",
            ],
        }
        client.ServoClient.get = unittest.mock.MagicMock(
            side_effect=lambda x: results[x]
        )
        with unittest.mock.patch(
            "servo.utils.timelined_stats_manager.TimelinedStatsManager.__init__",
            unittest.mock.MagicMock(return_value=None),
        ):
            self.tracker = measure_power.OnboardADCAccumPowerTracker(
                "localhost",
                9990,
                threading.Event(),
                measure_power.RegexFilter(None, "pps.*"),
                2,
            )

    def test_prepare(self):
        """Test prepare()."""
        self.tracker._sclient.set_get_all = unittest.mock.MagicMock()
        self.tracker.prepare()
        self.tracker._sclient.set_get_all.assert_called_once_with(
            ["ppchg5_ez_config:on", "ppdut5_ez_config:on"]
        )

    def test_clear_accum(self):
        """Test _clear_accum()."""
        self.tracker._sclient.set_get_all = unittest.mock.MagicMock()
        self.tracker.prepare()
        self.tracker._sclient.set_get_all.assert_called_once_with(
            ["ppchg5_ez_config:on", "ppdut5_ez_config:on"]
        )

    @unittest.mock.patch("time.time", unittest.mock.MagicMock(return_value=12345))
    def test_sample_ctrls(self):
        """Test _sample_ctrls()."""
        self.tracker._sclient.set_get_all = unittest.mock.MagicMock(return_value=[1, 2])
        self.tracker._clear_accum = unittest.mock.MagicMock()
        res = self.tracker._sample_ctrls(
            ["avg_rail_name_avg_mw", "avg_rail_name2_avg_mw"]
        )
        self.tracker._sclient.set_get_all.assert_called_once_with(
            ["avg_rail_name_avg_mw", "avg_rail_name2_avg_mw"]
        )
        self.tracker._clear_accum.assert_called_once()
        self.assertEqual(
            res, ([("rail_name", 1), ("rail_name2", 2), ("Sample_msecs", 0)], 0)
        )

    def test_run(self):
        """Test run()."""
        self.tracker._skip_first = True
        self.tracker._stop_signal.is_set = unittest.mock.MagicMock(
            side_effect=[False, False, False, True]
        )
        self.tracker._stop_signal.wait = unittest.mock.MagicMock()
        self.tracker._sample_ctrls = unittest.mock.MagicMock(
            side_effect=[
                ([("rail_name", 1), ("rail_name2", 2), ("Sample_msecs", 43.3)], 33.2),
                ([("rail_name", 3), ("rail_name2", 4), ("Sample_msecs", 43.5)], 33.1),
            ]
        )
        self.tracker._stats.AddSamples = unittest.mock.MagicMock()
        self.tracker.set_sample_data = unittest.mock.MagicMock()

        self.tracker.run()

        self.tracker._stop_signal.wait.assert_has_calls(
            [
                unittest.mock.call(2.0),
                unittest.mock.call(1.9668),
                unittest.mock.call(1.9669),
            ]
        )
        self.tracker._sample_ctrls.assert_has_calls(
            [unittest.mock.call(["ppchg5_mw"]), unittest.mock.call(["ppchg5_mw"])]
        )
        self.tracker._stats.AddSamples.assert_has_calls(
            [
                unittest.mock.call(
                    [("rail_name", 1), ("rail_name2", 2), ("Sample_msecs", 43.3)]
                ),
                unittest.mock.call(
                    [("rail_name", 3), ("rail_name2", 4), ("Sample_msecs", 43.5)]
                ),
            ]
        )
        self.tracker.set_sample_data.assert_has_calls(
            [
                unittest.mock.call(
                    [("rail_name", 1), ("rail_name2", 2), ("Sample_msecs", 43.3)]
                ),
                unittest.mock.call(
                    [("rail_name", 3), ("rail_name2", 4), ("Sample_msecs", 43.5)]
                ),
            ]
        )


class TestECPowerTracker(unittest.TestCase):
    """Test ECPowerTracker."""

    def setUp(self):
        """Set up for each unit test."""
        unittest.TestCase.setUp(self)
        client.ServoClient.__init__ = unittest.mock.MagicMock(return_value=None)
        with unittest.mock.patch(
            "servo.utils.timelined_stats_manager.TimelinedStatsManager.__init__",
            unittest.mock.MagicMock(return_value=None),
        ):
            self.tracker = measure_power.ECPowerTracker(
                "localhost",
                9990,
                threading.Event(),
                measure_power.RegexFilter(None, "pp.*"),
                2,
            )

    def test_verify(self):
        """Test verify()."""
        self.tracker._sclient.set_get_all = unittest.mock.MagicMock(
            side_effect=[None, None]
        )
        self.tracker.verify()
        self.tracker._sclient.set_get_all.assert_has_calls(
            [
                unittest.mock.call(["ppvar_vbat_mw"]),
                unittest.mock.call(["avg_ppvar_vbat_mw"]),
            ]
        )
        self.assertEqual(self.tracker._ctrls, ["avg_ppvar_vbat_mw"])

    def test_verify_failure_fallback(self):
        """Test verify() fallback on failure of using avg_ppvar_vbat_mw."""
        self.tracker._sclient.set_get_all = unittest.mock.MagicMock(
            side_effect=[None, measure_power.PowerTrackerError("msg")]
        )
        self.tracker.verify()
        self.tracker._sclient.set_get_all.assert_has_calls(
            [
                unittest.mock.call(["ppvar_vbat_mw"]),
                unittest.mock.call(["avg_ppvar_vbat_mw"]),
            ]
        )
        self.assertEqual(self.tracker._ctrls, [])

    def test_prepare(self):
        """Test prepare()."""
        self.tracker._sclient.set = unittest.mock.MagicMock()
        self.tracker.prepare()
        self.tracker._sclient.set.assert_called_once_with("ec_uart_cmd", "dsleep 2")

    def test_run(self):
        """Test run()."""
        self.tracker._skip_first = True
        self.tracker._stop_signal.is_set = unittest.mock.MagicMock(
            side_effect=[False, False, False, True]
        )
        self.tracker._stop_signal.wait = unittest.mock.MagicMock()
        self.tracker._sample_ctrls = unittest.mock.MagicMock(
            side_effect=[
                ([("ppvar_vbat_mw", 22), ("Sample_msecs", 43.1)], 33.5),
                ([("avg_ppvar_vbat_mw", 1), ("Sample_msecs", 43.3)], 33.2),
                ([("avg_ppvar_vbat_mw", 3), ("Sample_msecs", 43.5)], 33.1),
            ]
        )
        self.tracker._stats.AddSamples = unittest.mock.MagicMock()
        self.tracker.set_sample_data = unittest.mock.MagicMock()
        self.tracker._ctrls = ["avg_ppvar_vbat_mw"]

        self.tracker.run()

        self.tracker._stop_signal.wait.assert_has_calls(
            [
                unittest.mock.call(1.9665),
                unittest.mock.call(2.0),
                unittest.mock.call(1.9668),
                unittest.mock.call(1.9669),
            ]
        )
        self.tracker._sample_ctrls.assert_has_calls(
            [
                unittest.mock.call(["ppvar_vbat_mw"]),
                unittest.mock.call(["avg_ppvar_vbat_mw"]),
                unittest.mock.call(["avg_ppvar_vbat_mw"]),
            ]
        )
        self.tracker._stats.AddSamples.assert_has_calls(
            [
                unittest.mock.call([("avg_ppvar_vbat_mw", 22), ("Sample_msecs", 43.1)]),
                unittest.mock.call([("avg_ppvar_vbat_mw", 1), ("Sample_msecs", 43.3)]),
                unittest.mock.call([("avg_ppvar_vbat_mw", 3), ("Sample_msecs", 43.5)]),
            ]
        )
        self.tracker.set_sample_data.assert_has_calls(
            [
                unittest.mock.call([("avg_ppvar_vbat_mw", 22), ("Sample_msecs", 43.1)]),
                unittest.mock.call([("avg_ppvar_vbat_mw", 1), ("Sample_msecs", 43.3)]),
                unittest.mock.call([("avg_ppvar_vbat_mw", 3), ("Sample_msecs", 43.5)]),
            ]
        )


class TestRegexFilter(unittest.TestCase):
    """Test RegexFilter."""

    def test_call(self):
        """Test __call__()."""
        filter = measure_power.RegexFilter("pp.*", "pps.*")
        self.assertEqual(
            filter(["abc", "ppas", "ppsa", "ppvs"]), ["ppas", "ppsa", "ppvs"]
        )

        filter2 = measure_power.RegexFilter("pps.*", "pp.*")
        self.assertEqual(filter2(["abc", "ppas", "ppsa", "ppvs"]), ["ppsa"])


class TestPowerMeasurement(unittest.TestCase):
    """Test PowerMeasurement."""

    def setUp(self):
        """Set up for each unit test."""
        unittest.TestCase.setUp(self)
        client.ServoClient.__init__ = unittest.mock.MagicMock(return_value=None)
        results = {"ec_board": "atlas", "servo_adcs_enabled": "on"}
        client.ServoClient.get = unittest.mock.MagicMock(
            side_effect=lambda x: results[x]
        )
        client.ServoClient.set = unittest.mock.MagicMock()
        measure_power.OnboardADCPowerTracker.__init__ = unittest.mock.MagicMock(
            return_value=None
        )
        measure_power.OnboardADCPowerTracker.remove_rail = unittest.mock.MagicMock()
        measure_power.OnboardADCPowerTracker.verify = unittest.mock.MagicMock()
        measure_power.OnboardADCPowerTracker.empty = False
        measure_power.OnboardADCPowerTracker.title = "onboard"
        measure_power.OnboardADCAccumPowerTracker.__init__ = unittest.mock.MagicMock(
            return_value=None
        )
        measure_power.OnboardADCAccumPowerTracker.verify = unittest.mock.MagicMock()
        measure_power.OnboardADCAccumPowerTracker.rails = ["abc"]
        measure_power.OnboardADCAccumPowerTracker.empty = False
        measure_power.OnboardADCAccumPowerTracker.title = "onboard.accum"
        measure_power.ECPowerTracker.__init__ = unittest.mock.MagicMock(
            return_value=None
        )
        measure_power.ECPowerTracker.verify = unittest.mock.MagicMock()
        measure_power.ECPowerTracker.empty = False
        measure_power.ECPowerTracker.title = "ec"

    def test_init(self):
        """Test __init__()."""
        pm = measure_power.PowerMeasurement("localhost", 9998)
        client.ServoClient.__init__.assert_called_with(host="localhost", port=9998)
        client.ServoClient.get.assert_has_calls(
            [unittest.mock.call("ec_board"), unittest.mock.call("servo_adcs_enabled")]
        )
        client.ServoClient.set.assert_called_once_with("servo_adcs_enabled", "on")
        measure_power.OnboardADCPowerTracker.__init__.assert_called_once_with(
            "localhost",
            9998,
            pm._stop_signal,
            unittest.mock.ANY,
            measure_power.DEFAULT_ADC_RATE,
        )
        measure_power.OnboardADCAccumPowerTracker.__init__.assert_called_once_with(
            "localhost",
            9998,
            pm._stop_signal,
            unittest.mock.ANY,
            measure_power.DEFAULT_ADC_ACCUM_RATE,
        )
        measure_power.ECPowerTracker.__init__.assert_called_once_with(
            "localhost",
            9998,
            pm._stop_signal,
            unittest.mock.ANY,
            measure_power.DEFAULT_VBAT_RATE,
        )
        measure_power.OnboardADCPowerTracker.remove_rail.assert_called_once_with("abc")
        measure_power.OnboardADCPowerTracker.verify.assert_called_once()
        measure_power.OnboardADCAccumPowerTracker.verify.assert_called_once()
        measure_power.ECPowerTracker.verify.assert_called_once()

    def test_init_adc_disabled(self):
        """Test __init__()."""
        results = {"ec_board": "atlas", "servo_adcs_enabled": "off"}
        client.ServoClient.get = unittest.mock.MagicMock(
            side_effect=lambda x: results[x]
        )
        with self.assertRaises(measure_power.PowerMeasurementError) as cm:
            measure_power.PowerMeasurement("localhost", 9997)
        self.assertEqual(str(cm.exception), "ADCs setup failed.")
        client.ServoClient.__init__.assert_called_once_with(host="localhost", port=9997)
        client.ServoClient.get.assert_has_calls(
            [unittest.mock.call("ec_board"), unittest.mock.call("servo_adcs_enabled")]
        )

    def test_init_no_tracker(self):
        """Test __init__()."""
        with self.assertRaises(measure_power.NoSourceError) as cm:
            pm = measure_power.PowerMeasurement("localhost", 9996, 0, 0, 0)
        self.assertEqual(
            str(cm.exception), "No power measurement source successfully setup."
        )
        client.ServoClient.__init__.assert_called_once_with(host="localhost", port=9996)
        client.ServoClient.get.assert_has_calls(
            [unittest.mock.call("ec_board"), unittest.mock.call("servo_adcs_enabled")]
        )

    def test_init_tracker_error(self):
        """Test __init__()."""
        measure_power.OnboardADCPowerTracker.__init__ = unittest.mock.MagicMock(
            side_effect=measure_power.PowerTrackerError()
        )
        measure_power.OnboardADCAccumPowerTracker.__init__ = unittest.mock.MagicMock(
            side_effect=measure_power.PowerTrackerError()
        )
        measure_power.ECPowerTracker.__init__ = unittest.mock.MagicMock(
            side_effect=measure_power.PowerTrackerError()
        )
        with self.assertRaises(measure_power.NoSourceError) as cm:
            measure_power.PowerMeasurement("localhost", 9995)
        self.assertEqual(
            str(cm.exception), "No power measurement source successfully setup."
        )
        client.ServoClient.__init__.assert_called_once_with(host="localhost", port=9995)
        client.ServoClient.get.assert_has_calls(
            [unittest.mock.call("ec_board"), unittest.mock.call("servo_adcs_enabled")]
        )
        measure_power.OnboardADCPowerTracker.__init__.assert_called_once_with(
            "localhost",
            9995,
            unittest.mock.ANY,
            unittest.mock.ANY,
            measure_power.DEFAULT_ADC_RATE,
        )
        measure_power.OnboardADCAccumPowerTracker.__init__.assert_called_once_with(
            "localhost",
            9995,
            unittest.mock.ANY,
            unittest.mock.ANY,
            measure_power.DEFAULT_ADC_ACCUM_RATE,
        )
        measure_power.ECPowerTracker.__init__.assert_called_once_with(
            "localhost",
            9995,
            unittest.mock.ANY,
            unittest.mock.ANY,
            measure_power.DEFAULT_VBAT_RATE,
        )

    def test_init_tracker_empty(self):
        """Test __init__()."""
        measure_power.OnboardADCPowerTracker.empty = True
        measure_power.OnboardADCAccumPowerTracker.empty = True
        measure_power.ECPowerTracker.empty = True
        with self.assertRaises(measure_power.NoSourceError) as cm:
            measure_power.OnboardADCPowerTracker.__repr__ = unittest.mock.MagicMock(
                return_value=""
            )
            measure_power.OnboardADCAccumPowerTracker.__repr__ = (
                unittest.mock.MagicMock(return_value="")
            )
            measure_power.ECPowerTracker.__repr__ = unittest.mock.MagicMock(
                return_value=""
            )
            measure_power.PowerMeasurement("localhost", 9994)
        self.assertEqual(
            str(cm.exception), "No power measurement source successfully setup."
        )
        client.ServoClient.__init__.assert_called_with(host="localhost", port=9994)
        client.ServoClient.get.assert_has_calls(
            [unittest.mock.call("ec_board"), unittest.mock.call("servo_adcs_enabled")]
        )
        measure_power.OnboardADCPowerTracker.__init__.assert_called_once_with(
            "localhost",
            9994,
            unittest.mock.ANY,
            unittest.mock.ANY,
            measure_power.DEFAULT_ADC_RATE,
        )
        measure_power.OnboardADCAccumPowerTracker.__init__.assert_called_once_with(
            "localhost",
            9994,
            unittest.mock.ANY,
            unittest.mock.ANY,
            measure_power.DEFAULT_ADC_ACCUM_RATE,
        )
        measure_power.ECPowerTracker.__init__.assert_called_once_with(
            "localhost",
            9994,
            unittest.mock.ANY,
            unittest.mock.ANY,
            measure_power.DEFAULT_VBAT_RATE,
        )

    def test_init_fail_verification(self):
        """Test __init__()."""
        measure_power.OnboardADCPowerTracker.verify = unittest.mock.MagicMock(
            side_effect=measure_power.PowerTrackerError()
        )
        measure_power.OnboardADCAccumPowerTracker.verify = unittest.mock.MagicMock(
            side_effect=measure_power.PowerTrackerError()
        )
        measure_power.ECPowerTracker.verify = unittest.mock.MagicMock(
            side_effect=measure_power.PowerTrackerError()
        )
        with self.assertRaises(measure_power.NoSourceError) as cm:
            measure_power.PowerMeasurement("localhost", 9993)
        self.assertEqual(
            str(cm.exception), "No power measurement source successfully setup."
        )
        client.ServoClient.__init__.assert_called_with(host="localhost", port=9993)
        client.ServoClient.get.assert_has_calls(
            [unittest.mock.call("ec_board"), unittest.mock.call("servo_adcs_enabled")]
        )
        measure_power.OnboardADCPowerTracker.__init__.assert_called_once_with(
            "localhost",
            9993,
            unittest.mock.ANY,
            unittest.mock.ANY,
            measure_power.DEFAULT_ADC_RATE,
        )
        measure_power.OnboardADCAccumPowerTracker.__init__.assert_called_once_with(
            "localhost",
            9993,
            unittest.mock.ANY,
            unittest.mock.ANY,
            measure_power.DEFAULT_ADC_ACCUM_RATE,
        )
        measure_power.ECPowerTracker.__init__.assert_called_once_with(
            "localhost",
            9993,
            unittest.mock.ANY,
            unittest.mock.ANY,
            measure_power.DEFAULT_VBAT_RATE,
        )
        measure_power.OnboardADCPowerTracker.verify.assert_called_once()
        measure_power.OnboardADCAccumPowerTracker.verify.assert_called_once()
        measure_power.ECPowerTracker.verify.assert_called_once()

    def test_Reset(self):
        """Test Reset()."""
        pm = measure_power.PowerMeasurement("localhost", 9990)
        pm._stats = {"a": "testing"}
        pm._setup_done.set()
        pm._stop_signal.set()
        pm._processing_done = True

        pm.Reset()

        self.assertEqual(pm._stats, {})
        self.assertFalse(pm._setup_done.is_set())
        self.assertFalse(pm._stop_signal.is_set())
        self.assertFalse(pm._processing_done)

    def test_MeasureTimedPower(self):
        """Test MeasureTimedPower()."""
        setup_done = threading.Event()
        setup_done.wait = unittest.mock.MagicMock()
        pm = measure_power.PowerMeasurement("localhost", 9990)
        pm.MeasurePower = unittest.mock.MagicMock(return_value=setup_done)
        pm.FinishMeasurement = unittest.mock.MagicMock()

        with unittest.mock.patch("time.sleep", unittest.mock.MagicMock()):
            pm.MeasureTimedPower()
            time.sleep.assert_any_call(60 + 0)

        pm.MeasurePower.assert_called_once_with(
            wait=0, powerstate=measure_power.UNKNOWN_POWERSTATE
        )
        setup_done.wait.assert_called_once()
        pm.FinishMeasurement.assert_called_once()

    def test_MeasurePower(self):
        """Test MeasurePower()."""
        pm = measure_power.PowerMeasurement("localhost", 9990)

        with unittest.mock.patch(
            "threading.Thread.__init__", unittest.mock.MagicMock(return_value=None)
        ):
            with unittest.mock.patch("threading.Thread.daemon", True):
                with unittest.mock.patch(
                    "threading.Thread.start", unittest.mock.MagicMock()
                ):
                    res = pm.MeasurePower()

                    threading.Thread.__init__.assert_called_once_with(
                        target=pm._MeasurePower,
                        kwargs={
                            "wait": 0,
                            "powerstate": measure_power.UNKNOWN_POWERSTATE,
                        },
                    )
                    threading.Thread.start.assert_called_once()
                    self.assertEqual(res, pm._setup_done)

    def test__MeasurePower(self):
        """Test _MeasurePower()."""
        pm = measure_power.PowerMeasurement("localhost", 9990)
        pm._fast = False
        pm._setup_done.set = unittest.mock.MagicMock()
        pm._stop_signal = threading.Event()
        pm._stop_signal.wait = unittest.mock.MagicMock()
        pm._stop_signal.is_set = unittest.mock.MagicMock(return_value=False)
        measure_power.OnboardADCPowerTracker.prepare = unittest.mock.MagicMock()
        measure_power.OnboardADCAccumPowerTracker.prepare = unittest.mock.MagicMock()
        measure_power.ECPowerTracker.prepare = unittest.mock.MagicMock()
        measure_power.OnboardADCPowerTracker.start = unittest.mock.MagicMock()
        measure_power.OnboardADCAccumPowerTracker.start = unittest.mock.MagicMock()
        measure_power.ECPowerTracker.start = unittest.mock.MagicMock()

        with unittest.mock.patch(
            "time.strftime", unittest.mock.MagicMock(return_value="19700101-032545")
        ):
            pm._MeasurePower(10, "S0")
            measure_power.OnboardADCPowerTracker.prepare.assert_called_once_with(
                False, "S0"
            )
            measure_power.OnboardADCAccumPowerTracker.prepare.assert_called_once_with(
                False, "S0"
            )
            measure_power.ECPowerTracker.prepare.assert_called_once_with(False, "S0")
            self.assertEqual(
                pm._outdir, "/tmp/power_measurements/atlas/S0_19700101-032545"
            )
            pm._setup_done.set.assert_called_once()
            pm._stop_signal.wait.assert_called_once_with(10)
            measure_power.OnboardADCPowerTracker.start.assert_called_once()
            measure_power.OnboardADCAccumPowerTracker.start.assert_called_once()
            measure_power.ECPowerTracker.start.assert_called_once()

    def test__MeasurePower_unknown(self):
        """Test _MeasurePower()."""
        results = {
            "ec_board": "atlas",
            "servo_adcs_enabled": "on",
            "ec_system_powerstate": "S0",
        }
        client.ServoClient.get = unittest.mock.MagicMock(
            side_effect=lambda x: results[x]
        )
        pm = measure_power.PowerMeasurement("localhost", 9990)
        pm._fast = False
        pm._setup_done.set = unittest.mock.MagicMock()
        pm._stop_signal = threading.Event()
        pm._stop_signal.wait = unittest.mock.MagicMock()
        pm._stop_signal.is_set = unittest.mock.MagicMock(return_value=False)
        measure_power.OnboardADCPowerTracker.prepare = unittest.mock.MagicMock()
        measure_power.OnboardADCAccumPowerTracker.prepare = unittest.mock.MagicMock()
        measure_power.ECPowerTracker.prepare = unittest.mock.MagicMock()
        measure_power.OnboardADCPowerTracker.start = unittest.mock.MagicMock()
        measure_power.OnboardADCAccumPowerTracker.start = unittest.mock.MagicMock()
        measure_power.ECPowerTracker.start = unittest.mock.MagicMock()

        with unittest.mock.patch(
            "time.strftime", unittest.mock.MagicMock(return_value="19700101-032545")
        ):
            pm._MeasurePower(10)
            measure_power.OnboardADCPowerTracker.prepare.assert_called_once_with(
                False, "S0"
            )
            measure_power.OnboardADCAccumPowerTracker.prepare.assert_called_once_with(
                False, "S0"
            )
            measure_power.ECPowerTracker.prepare.assert_called_once_with(False, "S0")
            self.assertEqual(
                pm._outdir, "/tmp/power_measurements/atlas/S0_19700101-032545"
            )
            pm._setup_done.set.assert_called_once()
            pm._stop_signal.wait.assert_called_once_with(10)
            measure_power.OnboardADCPowerTracker.start.assert_called_once()
            measure_power.OnboardADCAccumPowerTracker.start.assert_called_once()
            measure_power.ECPowerTracker.start.assert_called_once()

    def test__MeasurePower_unknown_failure(self):
        """Test _MeasurePower()."""
        pm = measure_power.PowerMeasurement("localhost", 9990)
        pm._sclient.get = unittest.mock.MagicMock(
            side_effect=client.ServoClientError(None, None)
        )
        pm._fast = False
        pm._setup_done.set = unittest.mock.MagicMock()
        pm._stop_signal = threading.Event()
        pm._stop_signal.wait = unittest.mock.MagicMock()
        pm._stop_signal.is_set = unittest.mock.MagicMock(return_value=False)
        measure_power.OnboardADCPowerTracker.prepare = unittest.mock.MagicMock()
        measure_power.OnboardADCAccumPowerTracker.prepare = unittest.mock.MagicMock()
        measure_power.ECPowerTracker.prepare = unittest.mock.MagicMock()
        measure_power.OnboardADCPowerTracker.start = unittest.mock.MagicMock()
        measure_power.OnboardADCAccumPowerTracker.start = unittest.mock.MagicMock()
        measure_power.ECPowerTracker.start = unittest.mock.MagicMock()

        with unittest.mock.patch(
            "time.strftime", unittest.mock.MagicMock(return_value="19700101-032545")
        ):
            pm._MeasurePower(10)
            measure_power.OnboardADCPowerTracker.prepare.assert_called_once_with(
                False, measure_power.UNKNOWN_POWERSTATE
            )
            measure_power.OnboardADCAccumPowerTracker.prepare.assert_called_once_with(
                False, measure_power.UNKNOWN_POWERSTATE
            )
            measure_power.ECPowerTracker.prepare.assert_called_once_with(
                False, measure_power.UNKNOWN_POWERSTATE
            )
            self.assertEqual(
                pm._outdir, "/tmp/power_measurements/atlas/S?_19700101-032545"
            )
            pm._setup_done.set.assert_called_once()
            pm._stop_signal.wait.assert_called_once_with(10)
            measure_power.OnboardADCPowerTracker.start.assert_called_once()
            measure_power.OnboardADCAccumPowerTracker.start.assert_called_once()
            measure_power.ECPowerTracker.start.assert_called_once()

    def test__MeasurePower_fast_stop(self):
        """Test _MeasurePower()."""
        pm = measure_power.PowerMeasurement("localhost", 9990)
        pm._fast = True
        pm._setup_done.set = unittest.mock.MagicMock()
        pm._stop_signal = threading.Event()
        pm._stop_signal.wait = unittest.mock.MagicMock()
        pm._stop_signal.is_set = unittest.mock.MagicMock(return_value=True)
        measure_power.OnboardADCPowerTracker.prepare = unittest.mock.MagicMock()
        measure_power.OnboardADCAccumPowerTracker.prepare = unittest.mock.MagicMock()
        measure_power.ECPowerTracker.prepare = unittest.mock.MagicMock()
        measure_power.OnboardADCPowerTracker.start = unittest.mock.MagicMock()
        measure_power.OnboardADCAccumPowerTracker.start = unittest.mock.MagicMock()
        measure_power.ECPowerTracker.start = unittest.mock.MagicMock()

        with unittest.mock.patch(
            "time.strftime", unittest.mock.MagicMock(return_value="19700101-032545")
        ):
            pm._MeasurePower(10, "S0")
            measure_power.OnboardADCPowerTracker.prepare.assert_called_once_with(
                True, "S0"
            )
            measure_power.OnboardADCAccumPowerTracker.prepare.assert_called_once_with(
                True, "S0"
            )
            measure_power.ECPowerTracker.prepare.assert_called_once_with(True, "S0")
            self.assertEqual(
                pm._outdir, "/tmp/power_measurements/atlas/S0_19700101-032545"
            )
            pm._setup_done.set.assert_called_once()
            pm._stop_signal.wait.assert_called_once_with(10)
            measure_power.OnboardADCPowerTracker.start.assert_not_called()
            measure_power.OnboardADCAccumPowerTracker.start.assert_not_called()
            measure_power.ECPowerTracker.start.assert_not_called()

    def test_FinishMeasurement(self):
        """Test FinishMeasurement()."""
        pm = measure_power.PowerMeasurement("localhost", 9990)
        pm._stop_signal.set = unittest.mock.MagicMock()
        measure_power.OnboardADCPowerTracker.is_alive = unittest.mock.MagicMock(
            return_value=True
        )
        measure_power.OnboardADCAccumPowerTracker.is_alive = unittest.mock.MagicMock(
            return_value=False
        )
        measure_power.ECPowerTracker.is_alive = unittest.mock.MagicMock(
            return_value=True
        )
        measure_power.OnboardADCPowerTracker.join = unittest.mock.MagicMock()
        measure_power.OnboardADCAccumPowerTracker.join = unittest.mock.MagicMock()
        measure_power.ECPowerTracker.join = unittest.mock.MagicMock()

        pm.FinishMeasurement()

        pm._stop_signal.set.assert_called_once()
        measure_power.OnboardADCPowerTracker.join.assert_called_once()
        measure_power.OnboardADCAccumPowerTracker.join.assert_not_called()
        measure_power.ECPowerTracker.join.assert_called_once()

    def test_GetPMStatus(self):
        """Test GetPMStatus()."""
        pm = measure_power.PowerMeasurement("localhost", 9990)
        pm._stop_signal.is_set = unittest.mock.MagicMock(
            side_effect=[True, False, True]
        )

        self.assertTrue(pm.GetPMStatus())
        self.assertFalse(pm.GetPMStatus())
        self.assertTrue(pm.GetPMStatus())

    def test_ProcessMeasurement(self):
        """Test ProcessMeasurement()."""
        pm = measure_power.PowerMeasurement("localhost", 9990)
        pm.FinishMeasurement = unittest.mock.MagicMock()
        stats_manager1 = stats_manager.StatsManager()
        stats_manager2 = stats_manager.StatsManager()
        stats_manager3 = stats_manager.StatsManager()
        measure_power.OnboardADCPowerTracker.process_measurement = (
            unittest.mock.MagicMock(return_value=stats_manager1)
        )
        measure_power.OnboardADCAccumPowerTracker.process_measurement = (
            unittest.mock.MagicMock(return_value=stats_manager2)
        )
        measure_power.ECPowerTracker.process_measurement = unittest.mock.MagicMock(
            return_value=stats_manager3
        )

        pm.ProcessMeasurement(123, 456)

        measure_power.OnboardADCPowerTracker.process_measurement.assert_called_once_with(
            123, 456
        )
        measure_power.OnboardADCAccumPowerTracker.process_measurement.assert_called_once_with(
            123, 456
        )
        measure_power.ECPowerTracker.process_measurement.assert_called_once_with(
            123, 456
        )
        self.assertEqual(pm._stats["onboard"], stats_manager1)
        self.assertEqual(pm._stats["onboard.accum"], stats_manager2)
        self.assertEqual(pm._stats["ec"], stats_manager3)
        self.assertTrue(pm._processing_done)

    def test_SaveRawData(self):
        """Test SaveRawData()."""
        pm = measure_power.PowerMeasurement("localhost", 9990)
        pm._processing_done = True
        stats_manager1 = stats_manager.StatsManager(title="adc")
        stats_manager2 = stats_manager.StatsManager(title="ec")
        pm._stats = {"adc": stats_manager1, "ec": stats_manager2}
        stats_manager1.SaveRawData = unittest.mock.MagicMock(return_value=["raw1.txt"])
        stats_manager2.SaveRawData = unittest.mock.MagicMock(return_value=["raw2.txt"])

        self.assertEqual(pm.SaveRawData(), ["raw1.txt", "raw2.txt"])
        stats_manager1.SaveRawData.assert_called_once_with(None)
        stats_manager2.SaveRawData.assert_called_once_with(None)

    def test_SaveRawData_failure(self):
        """Test SaveRawData()."""
        pm = measure_power.PowerMeasurement("localhost", 9990)
        pm._processing_done = False

        with self.assertRaises(measure_power.PowerMeasurementError) as cm:
            pm.SaveRawData()
        self.assertEqual(str(cm.exception), pm.PREMATURE_RETRIEVAL_MSG)

    def test_GetRawData(self):
        """Test GetRawData()."""
        pm = measure_power.PowerMeasurement("localhost", 9990)
        pm._processing_done = True
        stats_manager1 = stats_manager.StatsManager(title="adc")
        stats_manager2 = stats_manager.StatsManager(title="ec")
        pm._stats = {"adc": stats_manager1, "ec": stats_manager2}
        stats_manager1.GetRawData = unittest.mock.MagicMock(return_value="raw1")
        stats_manager2.GetRawData = unittest.mock.MagicMock(return_value="raw2")

        self.assertEqual(pm.GetRawData(), {"adc": "raw1", "ec": "raw2"})

    def test_GetRawData_failure(self):
        """Test GetRawData()."""
        pm = measure_power.PowerMeasurement("localhost", 9990)
        pm._processing_done = False

        with self.assertRaises(measure_power.PowerMeasurementError) as cm:
            pm.GetRawData()
        self.assertEqual(str(cm.exception), pm.PREMATURE_RETRIEVAL_MSG)

    def test_SaveTrimmedSummary(self):
        """Test SaveTrimmedSummary()."""
        pm = measure_power.PowerMeasurement("localhost", 9990)
        pm._processing_done = True
        pm._SaveSummary = unittest.mock.MagicMock(return_value=["file1.txt"])
        stats_manager1 = stats_manager.StatsManager(title="adc")
        stats_manager2 = stats_manager.StatsManager(title="ec")
        pm._stats = {"adc": stats_manager1, "ec": stats_manager2}
        stats_manager1.TrimmedCopy = unittest.mock.MagicMock(
            return_value=stats_manager1
        )
        stats_manager2.TrimmedCopy = unittest.mock.MagicMock(return_value=None)

        res = pm.SaveTrimmedSummary("tag", 123, 456)

        stats_manager1.TrimmedCopy.assert_called_once_with(
            tag="tag", tstart=123, tend=456
        )
        stats_manager2.TrimmedCopy.assert_called_once_with(
            tag="tag", tstart=123, tend=456
        )
        self.assertEqual(stats_manager1._title, "adc(tag)")
        self.assertEqual(stats_manager2._title, "ec")
        pm._SaveSummary.assert_called_once()
        _, kwargs = pm._SaveSummary.call_args
        self.assertEqual(kwargs["stats_managers"], [stats_manager1])
        self.assertEqual(res, ["file1.txt"])

    def test_SaveTrimmedSummary_failure(self):
        """Test SaveTrimmedSummary()."""
        pm = measure_power.PowerMeasurement("localhost", 9990)
        pm._processing_done = False

        with self.assertRaises(measure_power.PowerMeasurementError) as cm:
            pm.SaveTrimmedSummary("tag", 123, 456)
        self.assertEqual(str(cm.exception), pm.PREMATURE_RETRIEVAL_MSG)

    def test_SaveSummary(self):
        """Test SaveSummary()."""
        pm = measure_power.PowerMeasurement("localhost", 9990)
        pm._processing_done = True
        stats_manager1 = stats_manager.StatsManager()
        stats_manager2 = stats_manager.StatsManager()
        pm._stats = {"adc": stats_manager1, "ec": stats_manager2}
        pm._SaveSummary = unittest.mock.MagicMock(
            return_value=["file1.txt", "file2.txt"]
        )

        res = pm.SaveSummary()

        pm._SaveSummary.assert_called_once()
        _, kwargs = pm._SaveSummary.call_args
        self.assertEqual(
            list(kwargs["stats_managers"]), [stats_manager1, stats_manager2]
        )
        self.assertEqual(res, ["file1.txt", "file2.txt"])

    def test_SaveSummary_failure(self):
        """Test SaveSummary()."""
        pm = measure_power.PowerMeasurement("localhost", 9990)
        pm._processing_done = False

        with self.assertRaises(measure_power.PowerMeasurementError) as cm:
            pm.SaveSummary()
        self.assertEqual(str(cm.exception), pm.PREMATURE_RETRIEVAL_MSG)

    def test__SaveSummary(self):
        """Test _SaveSummary()."""
        pm = measure_power.PowerMeasurement("localhost", 9990)
        stats_manager1 = stats_manager.StatsManager()
        stats_manager2 = stats_manager.StatsManager()
        stats_manager1.SaveSummary = unittest.mock.MagicMock(return_value="file1.txt")
        stats_manager2.SaveSummary = unittest.mock.MagicMock(return_value="file2.txt")
        stats_manager1.SaveSummaryMD = unittest.mock.MagicMock(return_value="file1.md")
        stats_manager2.SaveSummaryMD = unittest.mock.MagicMock(return_value="file2.md")

        res = pm._SaveSummary([stats_manager1, stats_manager2])

        stats_manager1.SaveSummaryMD.assert_called_once_with(pm._outdir)
        stats_manager2.SaveSummaryMD.assert_called_once_with(pm._outdir)
        self.assertEqual(res, ["file1.txt", "file2.txt"])

    def test_GetSummary(self):
        """Test GetSummary()."""
        pm = measure_power.PowerMeasurement("localhost", 9990)
        pm._processing_done = True
        stats_manager1 = stats_manager.StatsManager()
        stats_manager2 = stats_manager.StatsManager()
        stats_manager1.GetSummary = unittest.mock.MagicMock(return_value="testing1")
        stats_manager2.GetSummary = unittest.mock.MagicMock(return_value="testing2")
        pm._stats = {"adc": stats_manager1, "ec": stats_manager2}

        res = pm.GetSummary()

        stats_manager1.GetSummary.assert_called_once()
        stats_manager2.GetSummary.assert_called_once()
        self.assertEqual(res, {"adc": "testing1", "ec": "testing2"})

    def test_GetSummary_failure(self):
        """Test GetSummary()."""
        pm = measure_power.PowerMeasurement("localhost", 9990)
        pm._processing_done = False

        with self.assertRaises(measure_power.PowerMeasurementError) as cm:
            pm.GetSummary()
        self.assertEqual(str(cm.exception), pm.PREMATURE_RETRIEVAL_MSG)

    def test_GetFormattedSummary(self):
        """Test GetFormattedSummary()."""
        pm = measure_power.PowerMeasurement("localhost", 9990)
        pm._processing_done = True
        stats_manager1 = stats_manager.StatsManager()
        stats_manager2 = stats_manager.StatsManager()
        stats_manager1.SummaryToString = unittest.mock.MagicMock(
            return_value="testing1"
        )
        stats_manager2.SummaryToString = unittest.mock.MagicMock(
            return_value="testing2"
        )
        pm._stats = {"adc": stats_manager1, "ec": stats_manager2}

        res = pm.GetFormattedSummary()

        stats_manager1.SummaryToString.assert_called_once()
        stats_manager2.SummaryToString.assert_called_once()
        self.assertEqual(res, "testing1\ntesting2")

    def test_GetFormattedSummary_failure(self):
        """Test GetFormattedSummary()."""
        pm = measure_power.PowerMeasurement("localhost", 9990)
        pm._processing_done = False

        with self.assertRaises(measure_power.PowerMeasurementError) as cm:
            pm.GetFormattedSummary()
        self.assertEqual(str(cm.exception), pm.PREMATURE_RETRIEVAL_MSG)

    def test_DisplaySummary(self):
        """Test DisplaySummary()."""
        pm = measure_power.PowerMeasurement("localhost", 9990)
        pm.GetFormattedSummary = unittest.mock.MagicMock(return_value="summary")

        with unittest.mock.patch("builtins.print", unittest.mock.MagicMock()):
            pm.DisplaySummary()
            pm.GetFormattedSummary.assert_called_once()
            print.assert_called_with("\nsummary")

    def test_SaveSummaryJSON(self):
        """Test SaveSummaryJSON()."""
        pm = measure_power.PowerMeasurement("localhost", 9990)
        pm._processing_done = True
        pm._SaveSummaryJSON = unittest.mock.MagicMock(return_value=["testing.json"])

        res = pm.SaveSummaryJSON()

        pm._SaveSummaryJSON.assert_called_once()
        self.assertEqual(res, ["testing.json"])

    def test_SaveSummaryJSON_failure(self):
        """Test SaveSummaryJSON()."""
        pm = measure_power.PowerMeasurement("localhost", 9990)
        pm._processing_done = False

        with self.assertRaises(measure_power.PowerMeasurementError) as cm:
            pm.SaveSummaryJSON()
        self.assertEqual(str(cm.exception), pm.PREMATURE_RETRIEVAL_MSG)

    def test__SaveSummaryJSON(self):
        """Test _SaveSummaryJSON()."""
        pm = measure_power.PowerMeasurement("localhost", 9990)
        stats_manager1 = stats_manager.StatsManager()
        stats_manager2 = stats_manager.StatsManager()
        stats_manager1.SaveSummaryJSON = unittest.mock.MagicMock(
            return_value="file1.json"
        )
        stats_manager2.SaveSummaryJSON = unittest.mock.MagicMock(
            return_value="file2.json"
        )

        res = pm._SaveSummaryJSON([stats_manager1, stats_manager2])

        stats_manager1.SaveSummaryJSON.assert_called_once_with(pm._outdir)
        stats_manager2.SaveSummaryJSON.assert_called_once_with(pm._outdir)
        self.assertEqual(res, ["file1.json", "file2.json"])

    def test_GetSampleData(self):
        """Test GetSampleData()."""
        pm = measure_power.PowerMeasurement("localhost", 9990)
        measure_power.OnboardADCPowerTracker.get_sample_data = unittest.mock.MagicMock(
            return_value=["1"]
        )
        measure_power.OnboardADCAccumPowerTracker.get_sample_data = (
            unittest.mock.MagicMock(return_value=[])
        )
        measure_power.ECPowerTracker.get_sample_data = unittest.mock.MagicMock(
            return_value=["3"]
        )

        res = pm.GetSampleData()

        measure_power.OnboardADCPowerTracker.get_sample_data.assert_called_once()
        measure_power.OnboardADCAccumPowerTracker.get_sample_data.assert_called_once()
        measure_power.ECPowerTracker.get_sample_data.assert_called_once()
        self.assertEqual(res, ["1", "3"])

    def test_CleanSampleData(self):
        """Test CleanSampleData()."""
        pm = measure_power.PowerMeasurement("localhost", 9990)
        measure_power.OnboardADCPowerTracker.clean_sample_data = (
            unittest.mock.MagicMock()
        )
        measure_power.OnboardADCAccumPowerTracker.clean_sample_data = (
            unittest.mock.MagicMock()
        )
        measure_power.ECPowerTracker.clean_sample_data = unittest.mock.MagicMock()

        pm.CleanSampleData()

        measure_power.OnboardADCPowerTracker.clean_sample_data.assert_called_once()
        measure_power.OnboardADCAccumPowerTracker.clean_sample_data.assert_called_once()
        measure_power.ECPowerTracker.clean_sample_data.assert_called_once()


if __name__ == "__main__":
    unittest.main()
