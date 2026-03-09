# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Test dut_power_data works as intended."""

import unittest
import unittest.mock

from measurement_tools import dut_power_data
from measurement_tools import measure_power


class TestDataSampler(unittest.TestCase):
    """Test DataSampler."""

    def setUp(self):
        """Set up for each unit test."""
        unittest.TestCase.setUp(self)
        with unittest.mock.patch(
            "measurement_tools.measure_power.PowerMeasurement.__init__",
            unittest.mock.MagicMock(return_value=None),
        ):
            pm = measure_power.PowerMeasurement(None, None)
            self.data_sampler = dut_power_data.DataSampler(pm)

    @unittest.mock.patch("time.time", unittest.mock.MagicMock(return_value=12345))
    def test_get_data_sample_streaming(self):
        """Test get_data_samples."""
        self.data_sampler._data_sample = dut_power_data.DataSample(["name1", "name2"])
        self.data_sampler._pm.get_pm_status = unittest.mock.MagicMock(
            return_value=False
        )
        self.data_sampler._data_sample.to_json = unittest.mock.MagicMock(
            return_value="ok"
        )

        res = self.data_sampler.get_data_sample()
        self.data_sampler._data_sample.to_json.assert_called_once_with(
            dut_power_data.STREAMING_CHART_OUTPUT_TYPE,
            12345 - dut_power_data.SAMPLING_DELTA_PERIOD,
        )
        self.assertEqual(res, "ok")

    @unittest.mock.patch("time.time", unittest.mock.MagicMock(return_value=12345))
    def test_get_data_sample_non_streaming(self):
        """Test get_data_samples."""
        self.data_sampler._data_sample = dut_power_data.DataSample(["name1", "name2"])
        self.data_sampler._pm.get_pm_status = unittest.mock.MagicMock(return_value=True)
        self.data_sampler._data_sample.to_json = unittest.mock.MagicMock(
            return_value="ok"
        )

        res = self.data_sampler.get_data_sample()
        self.data_sampler._data_sample.to_json.assert_called_once_with(
            dut_power_data.LINE_CHART_OUTPUT_TYPE,
            12345 - dut_power_data.SAMPLING_DELTA_PERIOD,
        )
        self.assertEqual(res, "ok")

    def test_compare_data_sample_format(self):
        """Test compare_data_sample_format"""
        self.data_sampler._current_data_format = [2, 1, 3]
        self.assertTrue(self.data_sampler.compare_data_sample_format([3, 2, 1]))

    def test_get_data_sample_format(self):
        """Test get_data_sample_format."""
        samples = [("ppdut5", 3.1), ("ppservo5", 4.1), ("ppchg5", 0.0)]
        self.assertEqual(
            self.data_sampler.get_data_sample_format(samples),
            ["ppdut5", "ppservo5", "ppchg5"],
        )

    def test_define_data_sample_format(self):
        """Test define_data_sample_format"""
        self.data_sampler.define_data_sample_format(["ppdut5", "ppservo5", "ppchg5"])
        self.assertAlmostEqual(
            self.data_sampler._data_sample._meta,
            {
                "rowMeta": [
                    {"name": "time"},
                    {"name": "ppdut5"},
                    {"name": "ppservo5"},
                    {"name": "ppchg5"},
                ]
            },
        )

    # time.time is also used in unittest framework, so specifying side_effect
    # will fail the test
    @unittest.mock.patch("time.time", unittest.mock.MagicMock(return_value=12345))
    def test_sample_generator(self):
        """Test sample_generator."""
        samples1 = [("ppdut5", 3.1), ("ppservo5", 4.1), ("ppchg5", 0.0)]
        samples2 = [("ppdut5", 3.2), ("ppservo5", 4.2), ("ppchg5", 0.1)]
        self.data_sampler._pm.get_pm_status = unittest.mock.MagicMock(
            side_effect=[False, False, True]
        )
        self.data_sampler._pm.get_sample_data = unittest.mock.MagicMock(
            side_effect=[samples1, samples2]
        )
        self.data_sampler._pm.clean_sample_data = unittest.mock.MagicMock()

        self.data_sampler.sample_generator()

        self.assertEqual(
            self.data_sampler._data_sample._meta,
            {
                "rowMeta": [
                    {"name": "time"},
                    {"name": "ppdut5"},
                    {"name": "ppservo5"},
                    {"name": "ppchg5"},
                ]
            },
        )
        self.assertEqual(
            self.data_sampler._data_sample._samples,
            [[12345, 12345], [3.1, 3.2], [4.1, 4.2], [0.0, 0.1]],
        )


class TestDataSample(unittest.TestCase):
    """Test DataSample."""

    def setUp(self):
        """Set up for each unit test."""
        self.data_sample = dut_power_data.DataSample(
            ["time", "ppdut5", "ppservo5", "ppchg5"]
        )

    def test_add_samples(self):
        """Test add_samples."""
        samples1 = [12345, 3.1, 4.1, 0.0]
        samples2 = [12346, 3.2, 4.2, 0.1]

        self.data_sample.add_samples(samples1)
        self.data_sample.add_samples(samples2)

        self.assertEqual(
            self.data_sample._meta,
            {
                "rowMeta": [
                    {"name": "time"},
                    {"name": "ppdut5"},
                    {"name": "ppservo5"},
                    {"name": "ppchg5"},
                ]
            },
        )
        self.assertEqual(
            self.data_sample._samples,
            [[12345, 12346], [3.1, 3.2], [4.1, 4.2], [0.0, 0.1]],
        )

    def test_to_json(self):
        """Test to_json."""
        samples1 = [12345, 3.1, 4.1, 0.0]
        samples2 = [12346, 3.2, 4.2, 0.1]

        self.data_sample.add_samples(samples1)
        self.data_sample.add_samples(samples2)
        res = self.data_sample.to_json(dut_power_data.STREAMING_CHART_OUTPUT_TYPE)

        self.assertEqual(
            res,
            '{"type": "streaming_chart", "meta": {"rowMeta": [{"name": "time"}, '
            '{"name": "ppdut5"}, {"name": "ppservo5"}, {"name": "ppchg5"}]}, '
            '"matrix": [[12345, 12346], [3.1, 3.2], [4.1, 4.2], [0.0, 0.1]]}',
        )


if __name__ == "__main__":
    unittest.main()
