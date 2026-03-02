# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# pylint: disable=line-too-long
"""Test measure_power works as intended."""

import math
import threading
import time
import unittest
import unittest.mock

from measurement_tools import measure_power
from measurement_tools.utils import stats_manager
from servo.core import client


class TestServodPowerTracker(unittest.TestCase):
    """Test ServodPowerTracker."""

    def setUp(self):
        """Set up for each unit test."""
        unittest.TestCase.setUp(self)
        self.mock_servo_client = unittest.mock.MagicMock()
        self.mock_servo_client.clone.return_value = self.mock_servo_client
        with unittest.mock.patch(
            (
                "measurement_tools.utils.timelined_stats_manager."
                "TimelinedStatsManager.__init__"
            ),
            unittest.mock.MagicMock(return_value=None),
        ):
            self.tracker = measure_power.ServodPowerTracker(
                self.mock_servo_client,
                ["avg_rail_name_avg_mw", "avg_rail_name2_avg_mw"],
                threading.Event(),
                2,
            )
            self.tracker._stats = unittest.mock.MagicMock()

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
        self.tracker.verify()
        self.tracker._sclient.set_get_all.assert_called_once_with(self.tracker._ctrls)

    def test_verify_fail(self):
        """Test verify() failure scenario."""
        self.tracker._sclient.set_get_all.side_effect = client.ServoClientError(
            None, None
        )
        with self.assertRaises(measure_power.PowerTrackerError) as cm:
            self.tracker.verify()
        self.assertEqual(
            str(cm.exception),
            (
                "Failed to test servod commands. Tested: "
                "['avg_rail_name_avg_mw', 'avg_rail_name2_avg_mw']"
            ),
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
        self.tracker._stats.add_samples.assert_has_calls(
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
        self.tracker._sclient.set_get_all.return_value = [1, 2]
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
        self.tracker._sclient.set_get_all.side_effect = client.ServoClientError(
            None, None
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
        self.tracker._stats.trim_samples = unittest.mock.MagicMock()
        self.tracker._stats.calculate_stats = unittest.mock.MagicMock()

        res = self.tracker.process_measurement(123, 456)
        self.tracker._stats.trim_samples.assert_called_once_with(123, 456)
        self.tracker._stats.calculate_stats.assert_called_once()
        self.assertEqual(res, self.tracker._stats)

    def test_str(self):
        """Test __str__()."""
        self.assertEqual(str(self.tracker), "unnamed (mw)")


class TestHighResServodPowerTracker(unittest.TestCase):
    """Test HighResServodPowerTracker."""

    def setUp(self):
        """Set up for each unit test."""
        unittest.TestCase.setUp(self)
        self.mock_servo_client = unittest.mock.MagicMock()
        self.mock_servo_client.clone.return_value = self.mock_servo_client
        with unittest.mock.patch(
            (
                "measurement_tools.utils.timelined_stats_manager."
                "TimelinedStatsManager.__init__"
            ),
            unittest.mock.MagicMock(return_value=None),
        ):
            self.tracker = measure_power.HighResServodPowerTracker(
                self.mock_servo_client,
                ["avg_rail_name_avg_mw", "avg_rail_name2_avg_mw"],
                threading.Event(),
                2,
            )
            self.tracker._stats = unittest.mock.MagicMock()
        self.tracker.set_sample_data = unittest.mock.MagicMock()
        self.tracker._sample_ctrls = unittest.mock.MagicMock(
            return_value=(
                [("rail_name", 1), ("rail_name2", 2), ("Sample_msecs", 43.3)],
                33.2,
            )
        )

    def test_run(self):
        """Test run()."""
        self.tracker._stop_signal.is_set = unittest.mock.MagicMock(
            side_effect=[False, False, True]
        )
        with unittest.mock.patch(
            "time.time",
            unittest.mock.MagicMock(side_effect=[12345, 12347, 12349, 12349]),
        ):
            self.tracker.run()

        self.tracker._sample_ctrls.assert_has_calls(
            [
                unittest.mock.call(["avg_rail_name_avg_mw", "avg_rail_name2_avg_mw"]),
                unittest.mock.call(["avg_rail_name_avg_mw", "avg_rail_name2_avg_mw"]),
            ]
        )
        self.tracker.set_sample_data.assert_has_calls(
            [
                unittest.mock.call(
                    [("rail_name", 1), ("rail_name2", 2), ("Sample_msecs", 43.3)]
                ),
                unittest.mock.call(
                    [("rail_name", 1), ("rail_name2", 2), ("Sample_msecs", 43.3)]
                ),
            ]
        )

    def test_record_mean_samples(self):
        """Test _record_mean_samples()."""
        temp_stats = stats_manager.StatsManager()
        temp_stats.add_sample("rail_name", 1)
        temp_stats.add_sample("rail_name2", 2)
        temp_stats.add_sample("rail_name", 3)
        temp_stats.add_sample("rail_name2", 4)

        self.tracker._record_mean_samples(temp_stats)
        self.tracker._stats.add_samples.assert_called_once_with(
            [("rail_name", 2.0), ("rail_name2", 3.0)]
        )

    def test_process_measurement(self):
        """Test process_measurement()."""
        self.tracker._stats.trim_samples = unittest.mock.MagicMock()
        self.tracker._stats.calculate_stats = unittest.mock.MagicMock()

        res = self.tracker.process_measurement(123, 456)
        self.tracker._stats.trim_samples.assert_called_once_with(123, 456, 1)
        self.tracker._stats.calculate_stats.assert_called_once()
        self.assertEqual(res, self.tracker._stats)


class TestOnboardADCPowerTracker(unittest.TestCase):
    """Test OnboardADCPowerTracker."""

    def setUp(self):
        """Set up for each unit test."""
        unittest.TestCase.setUp(self)
        self.mock_servo_client = unittest.mock.MagicMock()
        self.mock_servo_client.clone.return_value = self.mock_servo_client
        results = {
            "power_rails": ["ppchg5_mw", "ppservo5_mw", "ppdut5_mw"],
            "adc_ez_config_ctrls": [
                "ppchg5_ez_config",
                "ppservo5_ez_config",
                "ppdut5_ez_config",
            ],
        }
        self.mock_servo_client.get.side_effect = lambda x: results[x]
        with unittest.mock.patch(
            (
                "measurement_tools.utils.timelined_stats_manager."
                "TimelinedStatsManager.__init__"
            ),
            unittest.mock.MagicMock(return_value=None),
        ):
            self.tracker = measure_power.OnboardADCPowerTracker(
                self.mock_servo_client,
                threading.Event(),
                measure_power.RegexFilter(None, "ppd.*"),
                2,
            )
            self.tracker._stats = unittest.mock.MagicMock()

    def test_prepare(self):
        """Test prepare()."""
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
        self.mock_servo_client = unittest.mock.MagicMock()
        self.mock_servo_client.clone.return_value = self.mock_servo_client
        results = {
            "avg_power_rails": ["ppchg5_mw", "ppservo5_mw"],
            "accum_clear_ctrls": ["ppdut5_mw"],
            "adc_ez_config_ctrls": [
                "ppchg5_ez_config",
                "ppservo5_ez_config",
                "ppdut5_ez_config",
            ],
        }
        self.mock_servo_client.get.side_effect = lambda x: results[x]
        with unittest.mock.patch(
            (
                "measurement_tools.utils.timelined_stats_manager."
                "TimelinedStatsManager.__init__"
            ),
            unittest.mock.MagicMock(return_value=None),
        ):
            self.tracker = measure_power.OnboardADCAccumPowerTracker(
                self.mock_servo_client,
                threading.Event(),
                measure_power.RegexFilter(None, "pps.*"),
                2,
            )
            self.tracker._stats = unittest.mock.MagicMock()

    def test_prepare(self):
        """Test prepare()."""
        self.tracker.prepare()
        self.tracker._sclient.set_get_all.assert_called_once_with(
            ["ppchg5_ez_config:on", "ppdut5_ez_config:on"]
        )

    def test_clear_accum(self):
        """Test _clear_accum()."""
        self.tracker.prepare()
        self.tracker._sclient.set_get_all.assert_called_once_with(
            ["ppchg5_ez_config:on", "ppdut5_ez_config:on"]
        )

    @unittest.mock.patch("time.time", unittest.mock.MagicMock(return_value=12345))
    def test_sample_ctrls(self):
        """Test _sample_ctrls()."""
        self.tracker._sclient.set_get_all.return_value = [1, 2]
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
        self.tracker._stats.add_samples.assert_has_calls(
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
        self.mock_servo_client = unittest.mock.MagicMock()
        self.mock_servo_client.clone.return_value = self.mock_servo_client
        with unittest.mock.patch(
            (
                "measurement_tools.utils.timelined_stats_manager."
                "TimelinedStatsManager.__init__"
            ),
            unittest.mock.MagicMock(return_value=None),
        ):
            self.tracker = measure_power.ECPowerTracker(
                self.mock_servo_client,
                threading.Event(),
                measure_power.RegexFilter(None, "pp.*"),
                2,
            )
            self.tracker._stats = unittest.mock.MagicMock()

    def test_verify(self):
        """Test verify()."""
        self.tracker._sclient.set_get_all.side_effect = [None, None]
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
        self.tracker._sclient.set_get_all.side_effect = [
            None,
            measure_power.PowerTrackerError("msg"),
        ]
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
        self.tracker._stats.add_samples.assert_has_calls(
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
        regexp_filter = measure_power.RegexFilter("pp.*", "pps.*")
        self.assertEqual(
            regexp_filter(["abc", "ppas", "ppsa", "ppvs"]), ["ppas", "ppsa", "ppvs"]
        )

        filter2 = measure_power.RegexFilter("pps.*", "pp.*")
        self.assertEqual(filter2(["abc", "ppas", "ppsa", "ppvs"]), ["ppsa"])


class TestPowerMeasurement(unittest.TestCase):
    """Test PowerMeasurement."""

    def setUp(self):
        """Set up for each unit test."""
        unittest.TestCase.setUp(self)
        self.mock_servo_client = unittest.mock.MagicMock()
        self.mock_servo_client.clone.return_value = self.mock_servo_client
        results = {"ec_board": "atlas", "servo_adcs_enabled": "on"}
        self.mock_servo_client.get.side_effect = lambda x: results[x]

        # Use patch.object to avoid leaking mocks to other tests.
        self._adc_patcher = unittest.mock.patch(
            "measurement_tools.measure_power.OnboardADCPowerTracker"
        )
        self.mock_adc_class = self._adc_patcher.start()
        self.addCleanup(self._adc_patcher.stop)

        self._adc_accum_patcher = unittest.mock.patch(
            "measurement_tools.measure_power.OnboardADCAccumPowerTracker"
        )
        self.mock_adc_accum_class = self._adc_accum_patcher.start()
        self.addCleanup(self._adc_accum_patcher.stop)

        self._ec_patcher = unittest.mock.patch(
            "measurement_tools.measure_power.ECPowerTracker"
        )
        self.mock_ec_class = self._ec_patcher.start()
        self.addCleanup(self._ec_patcher.stop)

        # Mock tracker instances
        self.mock_adc_tracker = self.mock_adc_class.return_value
        self.mock_adc_tracker.empty = False
        self.mock_adc_tracker.title = "onboard"
        self.mock_adc_tracker.rails = ["rail1", "rail2"]
        self.mock_adc_tracker.is_alive.return_value = True

        self.mock_adc_accum_tracker = self.mock_adc_accum_class.return_value
        self.mock_adc_accum_tracker.empty = False
        self.mock_adc_accum_tracker.title = "onboard.accum"
        self.mock_adc_accum_tracker.rails = ["abc"]
        self.mock_adc_accum_tracker.is_alive.return_value = False

        self.mock_ec_tracker = self.mock_ec_class.return_value
        self.mock_ec_tracker.empty = False
        self.mock_ec_tracker.title = "ec"
        self.mock_ec_tracker.rails = ["vbat"]
        self.mock_ec_tracker.is_alive.return_value = True

    def test_init(self):
        """Test __init__()."""
        pm = measure_power.PowerMeasurement(self.mock_servo_client)
        self.mock_servo_client.get.assert_has_calls(
            [unittest.mock.call("ec_board"), unittest.mock.call("servo_adcs_enabled")]
        )
        pm._sclient.set.assert_called_once_with("servo_adcs_enabled", "on")
        self.mock_adc_class.assert_called_once_with(
            self.mock_servo_client,
            pm._stop_signal,
            unittest.mock.ANY,  # cfilter
            measure_power.DEFAULT_ADC_RATE,
        )
        self.mock_adc_accum_class.assert_called_once_with(
            self.mock_servo_client,
            pm._stop_signal,
            unittest.mock.ANY,  # cfilter
            measure_power.DEFAULT_ADC_ACCUM_RATE,
        )
        self.mock_ec_class.assert_called_once_with(
            self.mock_servo_client,
            pm._stop_signal,
            unittest.mock.ANY,  # cfilter
            measure_power.DEFAULT_VBAT_RATE,
        )
        self.mock_adc_tracker.remove_rail.assert_called_once_with("abc")
        self.mock_adc_tracker.verify.assert_called_once()
        self.mock_adc_accum_tracker.verify.assert_called_once()
        self.mock_ec_tracker.verify.assert_called_once()

    def test_init_adc_disabled(self):
        """Test __init__()."""
        results = {"ec_board": "atlas", "servo_adcs_enabled": "off"}
        self.mock_servo_client.get.side_effect = lambda x: results[x]
        with self.assertRaises(measure_power.PowerMeasurementError) as cm:
            measure_power.PowerMeasurement(self.mock_servo_client)
        self.assertEqual(str(cm.exception), "ADCs setup failed.")
        self.mock_servo_client.get.assert_has_calls(
            [unittest.mock.call("ec_board"), unittest.mock.call("servo_adcs_enabled")]
        )

    def test_init_no_tracker(self):
        """Test __init__()."""
        with self.assertRaises(measure_power.NoSourceError) as cm:
            measure_power.PowerMeasurement(
                self.mock_servo_client, adc_rate=0, adc_accum_rate=0, vbat_rate=0
            )
        self.assertEqual(
            str(cm.exception), "No power measurement source successfully setup."
        )
        self.mock_servo_client.get.assert_has_calls(
            [unittest.mock.call("ec_board"), unittest.mock.call("servo_adcs_enabled")]
        )

    def test_init_tracker_error(self):
        """Test __init__()."""
        self.mock_adc_class.side_effect = measure_power.PowerTrackerError()
        self.mock_adc_accum_class.side_effect = measure_power.PowerTrackerError()
        self.mock_ec_class.side_effect = measure_power.PowerTrackerError()
        with self.assertRaises(measure_power.NoSourceError) as cm:
            measure_power.PowerMeasurement(self.mock_servo_client)
        self.assertEqual(
            str(cm.exception), "No power measurement source successfully setup."
        )
        self.mock_servo_client.get.assert_has_calls(
            [unittest.mock.call("ec_board"), unittest.mock.call("servo_adcs_enabled")]
        )
        self.mock_adc_class.assert_called_once_with(
            self.mock_servo_client,
            unittest.mock.ANY,
            unittest.mock.ANY,
            measure_power.DEFAULT_ADC_RATE,
        )
        self.mock_adc_accum_class.assert_called_once_with(
            self.mock_servo_client,
            unittest.mock.ANY,
            unittest.mock.ANY,
            measure_power.DEFAULT_ADC_ACCUM_RATE,
        )
        self.mock_ec_class.assert_called_once_with(
            self.mock_servo_client,
            unittest.mock.ANY,
            unittest.mock.ANY,
            measure_power.DEFAULT_VBAT_RATE,
        )

    def test_init_tracker_empty(self):
        """Test __init__()."""
        self.mock_adc_tracker.empty = True
        self.mock_adc_accum_tracker.empty = True
        self.mock_ec_tracker.empty = True
        with self.assertRaises(measure_power.NoSourceError) as cm:
            measure_power.PowerMeasurement(self.mock_servo_client)
        self.assertEqual(
            str(cm.exception), "No power measurement source successfully setup."
        )
        self.mock_servo_client.get.assert_has_calls(
            [unittest.mock.call("ec_board"), unittest.mock.call("servo_adcs_enabled")]
        )
        self.mock_adc_class.assert_called_once_with(
            self.mock_servo_client,
            unittest.mock.ANY,
            unittest.mock.ANY,
            measure_power.DEFAULT_ADC_RATE,
        )
        self.mock_adc_accum_class.assert_called_once_with(
            self.mock_servo_client,
            unittest.mock.ANY,
            unittest.mock.ANY,
            measure_power.DEFAULT_ADC_ACCUM_RATE,
        )
        self.mock_ec_class.assert_called_once_with(
            self.mock_servo_client,
            unittest.mock.ANY,
            unittest.mock.ANY,
            measure_power.DEFAULT_VBAT_RATE,
        )

    def test_init_fail_verification(self):
        """Test __init__()."""
        self.mock_adc_tracker.verify.side_effect = measure_power.PowerTrackerError()
        self.mock_adc_accum_tracker.verify.side_effect = (
            measure_power.PowerTrackerError()
        )
        self.mock_ec_tracker.verify.side_effect = measure_power.PowerTrackerError()
        with self.assertRaises(measure_power.NoSourceError) as cm:
            measure_power.PowerMeasurement(self.mock_servo_client)
        self.assertEqual(
            str(cm.exception), "No power measurement source successfully setup."
        )
        self.mock_servo_client.get.assert_has_calls(
            [unittest.mock.call("ec_board"), unittest.mock.call("servo_adcs_enabled")]
        )
        self.mock_adc_class.assert_called_once_with(
            self.mock_servo_client,
            unittest.mock.ANY,
            unittest.mock.ANY,
            measure_power.DEFAULT_ADC_RATE,
        )
        self.mock_adc_accum_class.assert_called_once_with(
            self.mock_servo_client,
            unittest.mock.ANY,
            unittest.mock.ANY,
            measure_power.DEFAULT_ADC_ACCUM_RATE,
        )
        self.mock_ec_class.assert_called_once_with(
            self.mock_servo_client,
            unittest.mock.ANY,
            unittest.mock.ANY,
            measure_power.DEFAULT_VBAT_RATE,
        )
        self.mock_adc_tracker.verify.assert_called_once()
        self.mock_adc_accum_tracker.verify.assert_called_once()
        self.mock_ec_tracker.verify.assert_called_once()

    def test_reset(self):
        """Test Reset()."""
        pm = measure_power.PowerMeasurement(self.mock_servo_client)
        pm._stats = {"a": "testing"}
        pm._setup_done.set()
        pm._stop_signal.set()
        pm._processing_done = True

        pm.reset()

        self.assertEqual(pm._stats, {})
        self.assertFalse(pm._setup_done.is_set())
        self.assertFalse(pm._stop_signal.is_set())
        self.assertFalse(pm._processing_done)

    def test_measure_timed_power(self):
        """Test measure_timed_power()."""
        setup_done = threading.Event()
        setup_done.wait = unittest.mock.MagicMock()
        pm = measure_power.PowerMeasurement(self.mock_servo_client)
        pm.measure_power = unittest.mock.MagicMock(return_value=setup_done)
        pm.finish_measurement = unittest.mock.MagicMock()

        with unittest.mock.patch("time.sleep", unittest.mock.MagicMock()):
            pm.measure_timed_power()
            time.sleep.assert_any_call(60 + 0)

        pm.measure_power.assert_called_once_with(
            wait=0, powerstate=measure_power.UNKNOWN_POWERSTATE
        )
        setup_done.wait.assert_called_once()
        pm.finish_measurement.assert_called_once()

    def test_measure_power(self):
        """Test measure_power()."""
        pm = measure_power.PowerMeasurement(self.mock_servo_client)

        with unittest.mock.patch(
            "threading.Thread.__init__", unittest.mock.MagicMock(return_value=None)
        ):
            with unittest.mock.patch("threading.Thread.daemon", True):
                with unittest.mock.patch(
                    "threading.Thread.start", unittest.mock.MagicMock()
                ):
                    res = pm.measure_power()

                    threading.Thread.__init__.assert_called_once_with(
                        target=pm._measure_power,
                        kwargs={
                            "wait": 0,
                            "powerstate": measure_power.UNKNOWN_POWERSTATE,
                        },
                    )
                    threading.Thread.start.assert_called_once()
                    self.assertEqual(res, pm._setup_done)

    def test__measure_power(self):
        """Test _measure_power()."""
        pm = measure_power.PowerMeasurement(self.mock_servo_client)
        pm._fast = False
        pm._setup_done.set = unittest.mock.MagicMock()
        pm._stop_signal = threading.Event()
        pm._stop_signal.wait = unittest.mock.MagicMock()
        pm._stop_signal.is_set = unittest.mock.MagicMock(return_value=False)

        with unittest.mock.patch(
            "time.strftime", unittest.mock.MagicMock(return_value="19700101-032545")
        ):
            pm._measure_power(10, "S0")
            self.mock_adc_tracker.prepare.assert_called_once_with(False, "S0")
            self.mock_adc_accum_tracker.prepare.assert_called_once_with(False, "S0")
            self.mock_ec_tracker.prepare.assert_called_once_with(False, "S0")
            self.assertEqual(
                pm._outdir, "/tmp/power_measurements/atlas/S0_19700101-032545"
            )
            pm._setup_done.set.assert_called_once()
            pm._stop_signal.wait.assert_called_once_with(10)
            self.mock_adc_tracker.start.assert_called_once()
            self.mock_adc_accum_tracker.start.assert_called_once()
            self.mock_ec_tracker.start.assert_called_once()

    def test__measure_power_unknown(self):
        """Test _measure_power()."""
        results = {
            "ec_board": "atlas",
            "servo_adcs_enabled": "on",
            "ec_system_powerstate": "S0",
        }
        self.mock_servo_client.get.side_effect = lambda x: results[x]
        pm = measure_power.PowerMeasurement(self.mock_servo_client)
        pm._fast = False
        pm._setup_done.set = unittest.mock.MagicMock()
        pm._stop_signal = threading.Event()
        pm._stop_signal.wait = unittest.mock.MagicMock()
        pm._stop_signal.is_set = unittest.mock.MagicMock(return_value=False)

        with unittest.mock.patch(
            "time.strftime", unittest.mock.MagicMock(return_value="19700101-032545")
        ):
            pm._measure_power(10)
            self.mock_adc_tracker.prepare.assert_called_once_with(False, "S0")
            self.mock_adc_accum_tracker.prepare.assert_called_once_with(False, "S0")
            self.mock_ec_tracker.prepare.assert_called_once_with(False, "S0")
            self.assertEqual(
                pm._outdir, "/tmp/power_measurements/atlas/S0_19700101-032545"
            )
            pm._setup_done.set.assert_called_once()
            pm._stop_signal.wait.assert_called_once_with(10)
            self.mock_adc_tracker.start.assert_called_once()
            self.mock_adc_accum_tracker.start.assert_called_once()
            self.mock_ec_tracker.start.assert_called_once()

    def test__measure_power_unknown_failure(self):
        """Test _measure_power()."""
        # Constructor calls get("ec_board") then set("servo_adcs_enabled", "on")
        # then get("servo_adcs_enabled")
        # We want constructor to have board "atlas" but _measure_power to fail.
        self.mock_servo_client.get.side_effect = ["atlas", "on", "on"]
        pm = measure_power.PowerMeasurement(self.mock_servo_client)

        # Now mock it for _measure_power
        pm._sclient.get = unittest.mock.MagicMock(
            side_effect=client.ServoClientError(None, None)
        )
        pm._fast = False
        pm._setup_done.set = unittest.mock.MagicMock()
        pm._stop_signal = threading.Event()
        pm._stop_signal.wait = unittest.mock.MagicMock()
        pm._stop_signal.is_set = unittest.mock.MagicMock(return_value=False)

        with unittest.mock.patch(
            "time.strftime", unittest.mock.MagicMock(return_value="19700101-032545")
        ):
            pm._measure_power(10)
            self.mock_adc_tracker.prepare.assert_called_once_with(
                False, measure_power.UNKNOWN_POWERSTATE
            )
            self.mock_adc_accum_tracker.prepare.assert_called_once_with(
                False, measure_power.UNKNOWN_POWERSTATE
            )
            self.mock_ec_tracker.prepare.assert_called_once_with(
                False, measure_power.UNKNOWN_POWERSTATE
            )
            self.assertEqual(
                pm._outdir, "/tmp/power_measurements/atlas/S?_19700101-032545"
            )
            pm._setup_done.set.assert_called_once()
            pm._stop_signal.wait.assert_called_once_with(10)
            self.mock_adc_tracker.start.assert_called_once()
            self.mock_adc_accum_tracker.start.assert_called_once()
            self.mock_ec_tracker.start.assert_called_once()

    def test__measure_power_fast_stop(self):
        """Test _measure_power()."""
        pm = measure_power.PowerMeasurement(self.mock_servo_client)
        pm._fast = True
        pm._setup_done.set = unittest.mock.MagicMock()
        pm._stop_signal = threading.Event()
        pm._stop_signal.wait = unittest.mock.MagicMock()
        pm._stop_signal.is_set = unittest.mock.MagicMock(return_value=True)

        with unittest.mock.patch(
            "time.strftime", unittest.mock.MagicMock(return_value="19700101-032545")
        ):
            pm._measure_power(10, "S0")
            self.mock_adc_tracker.prepare.assert_called_once_with(True, "S0")
            self.mock_adc_accum_tracker.prepare.assert_called_once_with(True, "S0")
            self.mock_ec_tracker.prepare.assert_called_once_with(True, "S0")
            self.assertEqual(
                pm._outdir, "/tmp/power_measurements/atlas/S0_19700101-032545"
            )
            pm._setup_done.set.assert_called_once()
            pm._stop_signal.wait.assert_called_once_with(10)
            self.mock_adc_tracker.start.assert_not_called()
            self.mock_adc_accum_tracker.start.assert_not_called()
            self.mock_ec_tracker.start.assert_not_called()

    def test_finish_measurement(self):
        """Test finish_measurement()."""
        pm = measure_power.PowerMeasurement(self.mock_servo_client)
        pm._stop_signal.set = unittest.mock.MagicMock()

        pm.finish_measurement()

        pm._stop_signal.set.assert_called_once()
        self.mock_adc_tracker.join.assert_called_once()
        self.mock_adc_accum_tracker.join.assert_not_called()
        self.mock_ec_tracker.join.assert_called_once()

    def test_get_pm_status(self):
        """Test get_pm_status()."""
        pm = measure_power.PowerMeasurement(self.mock_servo_client)
        pm._stop_signal.is_set = unittest.mock.MagicMock(
            side_effect=[True, False, True]
        )

        self.assertTrue(pm.get_pm_status())
        self.assertFalse(pm.get_pm_status())
        self.assertTrue(pm.get_pm_status())

    def test_process_measurement(self):
        """Test process_measurement()."""
        pm = measure_power.PowerMeasurement(self.mock_servo_client)
        pm.finish_measurement = unittest.mock.MagicMock()
        stats_manager1 = stats_manager.StatsManager()
        stats_manager2 = stats_manager.StatsManager()
        stats_manager3 = stats_manager.StatsManager()
        self.mock_adc_tracker.process_measurement.return_value = stats_manager1
        self.mock_adc_accum_tracker.process_measurement.return_value = stats_manager2
        self.mock_ec_tracker.process_measurement.return_value = stats_manager3

        pm.process_measurement(123, 456)

        self.mock_adc_tracker.process_measurement.assert_called_once_with(123, 456)
        self.mock_adc_accum_tracker.process_measurement.assert_called_once_with(
            123, 456
        )
        self.mock_ec_tracker.process_measurement.assert_called_once_with(123, 456)
        self.assertEqual(pm._stats["onboard"], stats_manager1)
        self.assertEqual(pm._stats["onboard.accum"], stats_manager2)
        self.assertEqual(pm._stats["ec"], stats_manager3)
        self.assertTrue(pm._processing_done)

    def test_save_raw_data(self):
        """Test save_raw_data()."""
        pm = measure_power.PowerMeasurement(self.mock_servo_client)
        pm._processing_done = True
        stats_manager1 = stats_manager.StatsManager(title="adc")
        stats_manager2 = stats_manager.StatsManager(title="ec")
        pm._stats = {"adc": stats_manager1, "ec": stats_manager2}
        stats_manager1.save_raw_data = unittest.mock.MagicMock(
            return_value=["raw1.txt"]
        )
        stats_manager2.save_raw_data = unittest.mock.MagicMock(
            return_value=["raw2.txt"]
        )

        self.assertEqual(pm.save_raw_data(), ["raw1.txt", "raw2.txt"])
        stats_manager1.save_raw_data.assert_called_once_with(None)
        stats_manager2.save_raw_data.assert_called_once_with(None)

    def test_save_raw_data_failure(self):
        """Test save_raw_data()."""
        pm = measure_power.PowerMeasurement(self.mock_servo_client)
        pm._processing_done = False

        with self.assertRaises(measure_power.PowerMeasurementError) as cm:
            pm.save_raw_data()
        self.assertEqual(str(cm.exception), pm.PREMATURE_RETRIEVAL_MSG)

    def test_get_raw_data(self):
        """Test get_raw_data()."""
        pm = measure_power.PowerMeasurement(self.mock_servo_client)
        pm._processing_done = True
        stats_manager1 = stats_manager.StatsManager(title="adc")
        stats_manager2 = stats_manager.StatsManager(title="ec")
        pm._stats = {"adc": stats_manager1, "ec": stats_manager2}
        stats_manager1.get_raw_data = unittest.mock.MagicMock(return_value="raw1")
        stats_manager2.get_raw_data = unittest.mock.MagicMock(return_value="raw2")

        self.assertEqual(pm.get_raw_data(), {"adc": "raw1", "ec": "raw2"})

    def test_get_raw_data_failure(self):
        """Test get_raw_data()."""
        pm = measure_power.PowerMeasurement(self.mock_servo_client)
        pm._processing_done = False

        with self.assertRaises(measure_power.PowerMeasurementError) as cm:
            pm.get_raw_data()
        self.assertEqual(str(cm.exception), pm.PREMATURE_RETRIEVAL_MSG)

    def test_save_trimmed_summary(self):
        """Test save_trimmed_summary()."""
        pm = measure_power.PowerMeasurement(self.mock_servo_client)
        pm._processing_done = True
        pm._save_summary = unittest.mock.MagicMock(return_value=["file1.txt"])
        stats_manager1 = stats_manager.StatsManager(title="adc")
        stats_manager2 = stats_manager.StatsManager(title="ec")
        pm._stats = {"adc": stats_manager1, "ec": stats_manager2}
        stats_manager1.trimmed_copy = unittest.mock.MagicMock(
            return_value=stats_manager1
        )
        stats_manager2.trimmed_copy = unittest.mock.MagicMock(return_value=None)

        res = pm.save_trimmed_summary("tag", 123, 456)

        stats_manager1.trimmed_copy.assert_called_once_with(
            tag="tag", tstart=123, tend=456
        )
        stats_manager2.trimmed_copy.assert_called_once_with(
            tag="tag", tstart=123, tend=456
        )
        self.assertEqual(stats_manager1._title, "adc(tag)")
        self.assertEqual(stats_manager2._title, "ec")
        pm._save_summary.assert_called_once()
        _unused, kwargs = pm._save_summary.call_args
        self.assertEqual(kwargs["stats_managers"], [stats_manager1])
        self.assertEqual(res, ["file1.txt"])

    def test_save_trimmed_summary_failure(self):
        """Test save_trimmed_summary()."""
        pm = measure_power.PowerMeasurement(self.mock_servo_client)
        pm._processing_done = False

        with self.assertRaises(measure_power.PowerMeasurementError) as cm:
            pm.save_trimmed_summary("tag", 123, 456)
        self.assertEqual(str(cm.exception), pm.PREMATURE_RETRIEVAL_MSG)

    def test_save_summary(self):
        """Test save_summary()."""
        pm = measure_power.PowerMeasurement(self.mock_servo_client)
        pm._processing_done = True
        stats_manager1 = stats_manager.StatsManager()
        stats_manager2 = stats_manager.StatsManager()
        pm._stats = {"adc": stats_manager1, "ec": stats_manager2}
        pm._save_summary = unittest.mock.MagicMock(
            return_value=["file1.txt", "file2.txt"]
        )

        res = pm.save_summary()

        pm._save_summary.assert_called_once()
        _unused, kwargs = pm._save_summary.call_args
        self.assertEqual(
            list(kwargs["stats_managers"]), [stats_manager1, stats_manager2]
        )
        self.assertEqual(res, ["file1.txt", "file2.txt"])

    def test_save_summary_failure(self):
        """Test save_summary()."""
        pm = measure_power.PowerMeasurement(self.mock_servo_client)
        pm._processing_done = False

        with self.assertRaises(measure_power.PowerMeasurementError) as cm:
            pm.save_summary()
        self.assertEqual(str(cm.exception), pm.PREMATURE_RETRIEVAL_MSG)

    def test__save_summary(self):
        """Test _save_summary()."""
        pm = measure_power.PowerMeasurement(self.mock_servo_client)
        stats_manager1 = stats_manager.StatsManager()
        stats_manager2 = stats_manager.StatsManager()
        stats_manager1.save_summary = unittest.mock.MagicMock(return_value="file1.txt")
        stats_manager2.save_summary = unittest.mock.MagicMock(return_value="file2.txt")
        stats_manager1.save_summary_md = unittest.mock.MagicMock(
            return_value="file1.md"
        )
        stats_manager2.save_summary_md = unittest.mock.MagicMock(
            return_value="file2.md"
        )

        res = pm._save_summary([stats_manager1, stats_manager2])

        stats_manager1.save_summary_md.assert_called_once_with(pm._outdir)
        stats_manager2.save_summary_md.assert_called_once_with(pm._outdir)
        self.assertEqual(res, ["file1.txt", "file2.txt"])

    def test_get_summary(self):
        """Test get_summary()."""
        pm = measure_power.PowerMeasurement(self.mock_servo_client)
        pm._processing_done = True
        stats_manager1 = stats_manager.StatsManager()
        stats_manager2 = stats_manager.StatsManager()
        stats_manager1.get_summary = unittest.mock.MagicMock(return_value="testing1")
        stats_manager2.get_summary = unittest.mock.MagicMock(return_value="testing2")
        pm._stats = {"adc": stats_manager1, "ec": stats_manager2}

        res = pm.get_summary()

        stats_manager1.get_summary.assert_called_once()
        stats_manager2.get_summary.assert_called_once()
        self.assertEqual(res, {"adc": "testing1", "ec": "testing2"})

    def test_get_summary_failure(self):
        """Test get_summary()."""
        pm = measure_power.PowerMeasurement(self.mock_servo_client)
        pm._processing_done = False

        with self.assertRaises(measure_power.PowerMeasurementError) as cm:
            pm.get_summary()
        self.assertEqual(str(cm.exception), pm.PREMATURE_RETRIEVAL_MSG)

    def test_get_formatted_summary(self):
        """Test get_formatted_summary()."""
        pm = measure_power.PowerMeasurement(self.mock_servo_client)
        pm._processing_done = True
        stats_manager1 = stats_manager.StatsManager()
        stats_manager2 = stats_manager.StatsManager()
        stats_manager1.summary_to_string = unittest.mock.MagicMock(
            return_value="testing1"
        )
        stats_manager2.summary_to_string = unittest.mock.MagicMock(
            return_value="testing2"
        )
        pm._stats = {"adc": stats_manager1, "ec": stats_manager2}

        res = pm.get_formatted_summary()

        stats_manager1.summary_to_string.assert_called_once()
        stats_manager2.summary_to_string.assert_called_once()
        self.assertEqual(res, "testing1\ntesting2")

    def test_get_formatted_summary_failure(self):
        """Test get_formatted_summary()."""
        pm = measure_power.PowerMeasurement(self.mock_servo_client)
        pm._processing_done = False

        with self.assertRaises(measure_power.PowerMeasurementError) as cm:
            pm.get_formatted_summary()
        self.assertEqual(str(cm.exception), pm.PREMATURE_RETRIEVAL_MSG)

    def test_display_summary(self):
        """Test display_summary()."""
        pm = measure_power.PowerMeasurement(self.mock_servo_client)
        pm.get_formatted_summary = unittest.mock.MagicMock(return_value="summary")

        with unittest.mock.patch("builtins.print", unittest.mock.MagicMock()):
            pm.display_summary()
            pm.get_formatted_summary.assert_called_once()
            print.assert_called_with("\nsummary")

    def test_save_summary_json(self):
        """Test save_summary_json()."""
        pm = measure_power.PowerMeasurement(self.mock_servo_client)
        pm._processing_done = True
        pm._save_summary_json = unittest.mock.MagicMock(return_value=["testing.json"])

        res = pm.save_summary_json()

        pm._save_summary_json.assert_called_once()
        self.assertEqual(res, ["testing.json"])

    def test_save_summary_json_failure(self):
        """Test save_summary_json()."""
        pm = measure_power.PowerMeasurement(self.mock_servo_client)
        pm._processing_done = False

        with self.assertRaises(measure_power.PowerMeasurementError) as cm:
            pm.save_summary_json()
        self.assertEqual(str(cm.exception), pm.PREMATURE_RETRIEVAL_MSG)

    def test__save_summary_json(self):
        """Test _save_summary_json()."""
        pm = measure_power.PowerMeasurement(self.mock_servo_client)
        stats_manager1 = stats_manager.StatsManager()
        stats_manager2 = stats_manager.StatsManager()
        stats_manager1.save_summary_json = unittest.mock.MagicMock(
            return_value="file1.json"
        )
        stats_manager2.save_summary_json = unittest.mock.MagicMock(
            return_value="file2.json"
        )

        res = pm._save_summary_json([stats_manager1, stats_manager2])

        stats_manager1.save_summary_json.assert_called_once_with(pm._outdir)
        stats_manager2.save_summary_json.assert_called_once_with(pm._outdir)
        self.assertEqual(res, ["file1.json", "file2.json"])

    def test_get_sample_data(self):
        """Test get_sample_data()."""
        pm = measure_power.PowerMeasurement(self.mock_servo_client)
        self.mock_adc_tracker.get_sample_data.return_value = ["1"]
        self.mock_adc_accum_tracker.get_sample_data.return_value = []
        self.mock_ec_tracker.get_sample_data.return_value = ["3"]

        res = pm.get_sample_data()

        self.mock_adc_tracker.get_sample_data.assert_called_once()
        self.mock_adc_accum_tracker.get_sample_data.assert_called_once()
        self.mock_ec_tracker.get_sample_data.assert_called_once()
        self.assertEqual(res, ["1", "3"])

    def test_clean_sample_data(self):
        """Test clean_sample_data()."""
        pm = measure_power.PowerMeasurement(self.mock_servo_client)
        pm.clean_sample_data()

        self.mock_adc_tracker.clean_sample_data.assert_called_once()
        self.mock_adc_accum_tracker.clean_sample_data.assert_called_once()
        self.mock_ec_tracker.clean_sample_data.assert_called_once()


if __name__ == "__main__":
    unittest.main()
