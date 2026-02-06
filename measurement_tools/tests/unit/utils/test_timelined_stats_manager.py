# Copyright 2018 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for TimelinedStatsManager."""

import copy
import math
import shutil
import tempfile
import time
import unittest

from measurement_tools.utils import stats_manager
from measurement_tools.utils import timelined_stats_manager


class TestTimelinedStatsManager(unittest.TestCase):
    def setUp(self):
        """Set up data and create a temporary directory to save data and stats."""
        unittest.TestCase.setUp(self)
        self.tempdir = tempfile.mkdtemp()
        self.data = timelined_stats_manager.TimelinedStatsManager()

    def tearDown(self):
        """Delete the temporary directory and its content."""
        shutil.rmtree(self.tempdir)
        unittest.TestCase.tearDown(self)

    def assert_column_height(self):
        """Helper to assert that all domains have the same number of samples."""
        heights = set([len(samples) for samples in self.data._data.values()])
        self.assertEqual(1, len(heights))

    def test_nan_added_on_missing_domain(self):
        """NaN is added when known domain is missing from samples."""
        samples = [("A", 10), ("B", 10)]
        self.data.add_samples(samples)
        samples = [("B", 20)]
        self.data.add_samples(samples)
        # NaN was added as the 2nd sample for A
        self.assertTrue(math.isnan(self.data._data["A"][1]))
        # make sure each column is of the same height
        self.assert_column_height()

    def test_nan_prefill_on_new_domain(self):
        """NaN is prefilled for timeline when encountering new domain."""
        samples = [("B", 20)]
        self.data.add_samples(samples)
        samples = [("A", 10), ("B", 10)]
        self.data.add_samples(samples)
        self.assertTrue(math.isnan(self.data._data["A"][0]))
        self.assertEqual(10, self.data._data["A"][1])
        self.assert_column_height()

    def test_timeline_is_relative_to_time(self):
        """Timeline key has the same step-size as Time key, just starts at 0."""
        samples = [("A", 10), ("B", 10)]
        # adding using copy to ensure that the same list doesn't get added multiple
        # times.
        self.data.add_samples(copy.copy(samples))
        self.data.add_samples(copy.copy(samples))
        time.sleep(0.005)
        self.data.add_samples(copy.copy(samples))
        time.sleep(0.01)
        self.data.add_samples(copy.copy(samples))
        self.data.calculate_stats()
        timepoints = self.data._data[timelined_stats_manager.TIME_KEY]
        timeline = self.data._data[timelined_stats_manager.TLINE_KEY]
        own_tl = [tp - timepoints[0] for tp in timepoints]
        self.assertEqual(own_tl, timeline)

    def test_duplicate_keys(self):
        """Error raised when adding samples with a duplicate key."""
        samples = [("A", 10), ("B", 10), ("A", 20)]
        with self.assertRaises(stats_manager.StatsManagerError):
            self.data.add_samples(samples)

    def test_trim_samples(self):
        """Ensure that trimming works as expected."""
        self.data.add_samples([("A", 10)])
        tstart = time.time()
        time.sleep(0.01)
        self.data.add_samples([("A", 23)])
        self.data.add_samples([("A", 20)])
        tend = time.time()
        time.sleep(0.01)
        self.data.add_samples([("A", 10)])
        self.data.trim_samples(tstart=tstart, tend=tend)
        self.data.calculate_stats()
        # Verify that only the samples between the timestamps are left
        self.assertEqual([23, 20], self.data._data["A"])
        for samples in self.data._data.values():
            # Verify that all domains were trimmed to size 2
            self.assertEqual(2, len(samples))

    def test_trim_samples_no_start_no_end(self):
        """Ensure that the trimming encompasses the whole dataset."""
        orig_samples = [10, 23, 20, 10]
        for sample in orig_samples:
            self.data.add_samples([("A", sample)])
        self.data.calculate_stats()
        self.data.trim_samples()
        self.assertEqual(orig_samples, self.data._data["A"])
        for samples in self.data._data.values():
            # Verify that all domains were not trimmed
            self.assertEqual(len(orig_samples), len(samples))

    def test_trim_samples_domain_empty(self):
        """Ensure that the domain is removed if it becomes empty post trimming."""
        self.data.add_samples([("A", 10)])
        time.sleep(0.01)
        tstart = time.time()
        self.data.trim_samples(tstart=tstart)
        self.data.calculate_stats()
        # Verify that 'A' has been removed
        self.assertNotIn("A", self.data._data)

    def test_trim_samples_functionally_not_empty(self):
        """Test |functionally_empty()| after trimming out only data domain."""
        self.data.add_samples([("A", 10)])
        time.sleep(0.01)
        tstart = time.time()
        time.sleep(0.01)
        self.data.add_samples([("A", 20)])
        self.data.trim_samples(tstart=tstart)
        self.data.calculate_stats()
        # Verify that 'A' is still present
        self.assertIn("A", self.data._data)
        # Verify that this means the stats manager is not functionally empty
        self.assertFalse(self.data.functionally_empty())

    def test_trim_samples_functionally_empty(self):
        """Test |functionally_empty()| after trimming out only data domain."""
        self.data.add_samples([("A", 10)])
        time.sleep(0.01)
        tstart = time.time()
        self.data.trim_samples(tstart=tstart)
        self.data.calculate_stats()
        # Verify that 'A' has been removed
        self.assertNotIn("A", self.data._data)
        self.assertTrue(self.data.functionally_empty())

    def test_trim_samples_with_padding(self):
        """Ensure that trimming with offset works as expected."""
        tstart = time.time()
        self.data.add_samples([("A", 10)], tstart)
        tinter = tstart + 0.02
        self.data.add_samples([("A", 23)], tinter)
        tend = tinter + 0.01
        self.data.add_samples([("A", 20)], tend)
        self.data.trim_samples(tstart=tstart, tend=tend, offset=0.02)
        self.data.calculate_stats()
        # Verify that only the samples between the timestamps are left
        self.assertEqual([23, 20], self.data._data["A"])
        for samples in self.data._data.values():
            # Verify that all domains were trimmed to size 2
            self.assertEqual(2, len(samples))


if __name__ == "__main__":
    unittest.main()
