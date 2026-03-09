# Copyright 2017 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for StatsManager."""


import json
import os
import re
import shutil
import tempfile
import unittest

from measurement_tools.utils import stats_manager


class TestStatsManager(unittest.TestCase):
    """Test to verify StatsManager methods work as expected.

    StatsManager should collect raw data, calculate their statistics, and save
    them in expected format.
    """

    def _populate_mock_stats(self):
        """Create a populated & processed StatsManager to test data retrieval."""
        self.data.add_sample("A", 99999.5)
        self.data.add_sample("A", 100000.5)
        self.data.set_unit("A", "uW")
        self.data.set_unit("A", "mW")
        self.data.add_sample("B", 1.5)
        self.data.add_sample("B", 2.5)
        self.data.add_sample("B", 3.5)
        self.data.set_unit("B", "mV")
        self.data.calculate_stats()

    def _populate_mock_stats_no_unit(self):
        self.data.add_sample("B", 1000)
        self.data.add_sample("A", 200)
        self.data.set_unit("A", "blue")

    def setUp(self):
        """Set up StatsManager and create a temporary directory for test."""
        unittest.TestCase.setUp(self)
        self.tempdir = tempfile.mkdtemp()
        self.data = stats_manager.StatsManager()

    def tearDown(self):
        """Delete the temporary directory and its content."""
        shutil.rmtree(self.tempdir)
        unittest.TestCase.tearDown(self)

    def test_add_sample(self):
        """Adding a sample successfully adds a sample."""
        self.data.add_sample("Test", 1000)
        self.data.set_unit("Test", "test")
        self.data.calculate_stats()
        summary = self.data.get_summary()
        self.assertEqual(1, summary["Test"]["count"])

    def test_add_sample_no_float_accept_nan(self):
        """Adding a non-number adds 'NaN' and doesn't raise an exception."""
        self.data.add_sample("Test", 10)
        self.data.add_sample("Test", 20)
        # adding a fake NaN: one that gets converted into NaN internally
        self.data.add_sample("Test", "fiesta")
        # adding a real NaN
        self.data.add_sample("Test", float("NaN"))
        self.data.set_unit("Test", "test")
        self.data.calculate_stats()
        summary = self.data.get_summary()
        # assert that 'NaN' as added.
        self.assertEqual(4, summary["Test"]["count"])
        # assert that mean, min, and max calculations ignore the 'NaN'
        self.assertEqual(10, summary["Test"]["min"])
        self.assertEqual(20, summary["Test"]["max"])
        self.assertEqual(15, summary["Test"]["mean"])

    def test_add_sample_no_float_not_accept_nan(self):
        """Adding a non-number raises a StatsManagerError if accept_nan is False."""
        self.data = stats_manager.StatsManager(accept_nan=False)
        with self.assertRaisesRegex(
            stats_manager.StatsManagerError,
            "accept_nan is false. Cannot add NaN sample.",
        ):
            # adding a fake NaN: one that gets converted into NaN internally
            self.data.add_sample("Test", "fiesta")
        with self.assertRaisesRegex(
            stats_manager.StatsManagerError,
            "accept_nan is false. Cannot add NaN sample.",
        ):
            # adding a real NaN
            self.data.add_sample("Test", float("NaN"))

    def test_add_sample_no_unit(self):
        """Not adding a unit does not cause an exception on calculate_stats()."""
        self.data.add_sample("Test", 17)
        self.data.calculate_stats()
        summary = self.data.get_summary()
        self.assertEqual(1, summary["Test"]["count"])

    def test_unit_suffix(self):
        """Unit gets appended as a suffix in the displayed summary."""
        self.data.add_sample("test", 250)
        self.data.set_unit("test", "mw")
        self.data.calculate_stats()
        summary_str = self.data.summary_to_string()
        self.assertIn("test_mw", summary_str)

    def test_double_unit_suffix(self):
        """If domain already ends in unit, verify that unit doesn't get appended."""
        self.data.add_sample("test_mw", 250)
        self.data.set_unit("test_mw", "mw")
        self.data.calculate_stats()
        summary_str = self.data.summary_to_string()
        self.assertIn("test_mw", summary_str)
        self.assertNotIn("test_mw_mw", summary_str)

    def test_get_raw_data(self):
        """get_raw_data returns exact same data as fed in."""
        self._populate_mock_stats()
        raw_data = self.data.get_raw_data()
        self.assertListEqual([99999.5, 100000.5], raw_data["A"])
        self.assertListEqual([1.5, 2.5, 3.5], raw_data["B"])

    def test_get_summary(self):
        """get_summary returns expected stats about the data fed in."""
        self._populate_mock_stats()
        summary = self.data.get_summary()
        self.assertEqual(2, summary["A"]["count"])
        self.assertAlmostEqual(100000.5, summary["A"]["max"])
        self.assertAlmostEqual(99999.5, summary["A"]["min"])
        self.assertAlmostEqual(0.5, summary["A"]["stddev"])
        self.assertAlmostEqual(100000.0, summary["A"]["mean"])
        self.assertEqual(3, summary["B"]["count"])
        self.assertAlmostEqual(3.5, summary["B"]["max"])
        self.assertAlmostEqual(1.5, summary["B"]["min"])
        self.assertAlmostEqual(0.81649658092773, summary["B"]["stddev"])
        self.assertAlmostEqual(2.5, summary["B"]["mean"])

    def test_save_raw_data(self):
        """save_raw_data stores same data as fed in."""
        self._populate_mock_stats()
        dirname = "unittest_raw_data"
        expected_files = set(["A_mW.txt", "B_mV.txt"])
        fnames = self.data.save_raw_data(self.tempdir, dirname)
        files_returned = set([os.path.basename(f) for f in fnames])
        # Assert that only the expected files got returned.
        self.assertEqual(expected_files, files_returned)
        # Assert that only the returned files are in the outdir.
        self.assertEqual(
            set(os.listdir(os.path.join(self.tempdir, dirname))), files_returned
        )
        for fname in fnames:
            with open(fname, "r", encoding="utf-8") as f:
                if "A_mW" in fname:
                    self.assertEqual("99999.50", f.readline().strip())
                    self.assertEqual("100000.50", f.readline().strip())
                if "B_mV" in fname:
                    self.assertEqual("1.50", f.readline().strip())
                    self.assertEqual("2.50", f.readline().strip())
                    self.assertEqual("3.50", f.readline().strip())

    def test_save_raw_data_no_unit(self):
        """save_raw_data appends no unit suffix if the unit is not specified."""
        self._populate_mock_stats_no_unit()
        self.data.calculate_stats()
        outdir = "unittest_raw_data"
        files = self.data.save_raw_data(self.tempdir, outdir)
        files = [os.path.basename(f) for f in files]
        # Verify nothing gets appended to domain for filename if no unit exists.
        self.assertIn("B.txt", files)

    def test_save_raw_data_smid(self):
        """save_raw_data uses the smid when creating output filename."""
        identifier = "ec"
        self.data = stats_manager.StatsManager(smid=identifier)
        self._populate_mock_stats()
        files = self.data.save_raw_data(self.tempdir)
        for fname in files:
            self.assertTrue(os.path.basename(fname).startswith(identifier))

    def test_summary_to_string_nan_help(self):
        """NaN containing row gets tagged with *, help banner gets added."""
        help_banner_exp = "%s %s" % (
            stats_manager.STATS_PREFIX,
            stats_manager.NAN_DESCRIPTION,
        )
        nan_domain = "A-domain"
        nan_domain_exp = "%s%s" % (nan_domain, stats_manager.NAN_TAG)
        # NaN helper banner is added when a NaN domain is found & domain gets tagged
        data = stats_manager.StatsManager()
        data.add_sample(nan_domain, float("NaN"))
        data.add_sample(nan_domain, 17)
        data.add_sample("B-domain", 17)
        data.calculate_stats()
        summarystr = data.summary_to_string()
        self.assertIn(help_banner_exp, summarystr)
        self.assertIn(nan_domain_exp, summarystr)
        # NaN helper banner is not added when no NaN domain output, no tagging
        data = stats_manager.StatsManager()
        # nan_domain in this scenario does not contain any NaN
        data.add_sample(nan_domain, 19)
        data.add_sample("B-domain", 17)
        data.calculate_stats()
        summarystr = data.summary_to_string()
        self.assertNotIn(help_banner_exp, summarystr)
        self.assertNotIn(nan_domain_exp, summarystr)

    def test_summary_to_string_title(self):
        """Title shows up in summary_to_string if title specified."""
        title = "titulo"
        data = stats_manager.StatsManager(title=title)
        self._populate_mock_stats()
        summary_str = data.summary_to_string()
        self.assertIn(title, summary_str)

    def test_summary_to_string_hide_domains(self):
        """Keys indicated in hide_domains are not printed in the summary."""
        data = stats_manager.StatsManager(hide_domains=["A-domain"])
        data.add_sample("A-domain", 17)
        data.add_sample("B-domain", 17)
        data.calculate_stats()
        summary_str = data.summary_to_string()
        self.assertIn("B-domain", summary_str)
        self.assertNotIn("A-domain", summary_str)

    def test_summary_to_string_order(self):
        """Order passed into StatsManager is honoured when formatting summary."""
        # StatsManager that should print D & B first, and the subsequent elements
        # are sorted.
        d_b_a_c_regexp = re.compile("D-domain.*B-domain.*A-domain.*C-domain", re.DOTALL)
        data = stats_manager.StatsManager(order=["D-domain", "B-domain"])
        data.add_sample("A-domain", 17)
        data.add_sample("B-domain", 17)
        data.add_sample("C-domain", 17)
        data.add_sample("D-domain", 17)
        data.calculate_stats()
        summary_str = data.summary_to_string()
        self.assertRegex(summary_str, d_b_a_c_regexp)

    def test_make_unique_fname(self):
        data = stats_manager.StatsManager()
        testfile = os.path.join(self.tempdir, "testfile.txt")
        with open(testfile, "w", encoding="utf-8") as f:
            f.write("")
        expected_fname = os.path.join(self.tempdir, "testfile0.txt")
        self.assertEqual(expected_fname, data._make_unique_fname(testfile))

    def test_save_summary(self):
        """save_summary properly dumps the summary into a file."""
        self._populate_mock_stats()
        fname = "unittest_summary.txt"
        expected_fname = os.path.join(self.tempdir, fname)
        fname = self.data.save_summary(self.tempdir, fname)
        # Assert the reported fname is the same as the expected fname
        self.assertEqual(expected_fname, fname)
        # Assert only the reported fname is output (in the tempdir)
        self.assertEqual(set([os.path.basename(fname)]), set(os.listdir(self.tempdir)))
        with open(fname, "r", encoding="utf-8") as f:
            self.assertEqual(
                "@@   NAME  COUNT       MEAN  STDDEV        MAX       MIN\n",
                f.readline(),
            )
            self.assertEqual(
                "@@   A_mW      2  100000.00    0.50  100000.50  99999.50\n",
                f.readline(),
            )
            self.assertEqual(
                "@@   B_mV      3       2.50    0.82       3.50      1.50\n",
                f.readline(),
            )

    def test_save_summary_smid(self):
        """save_summary uses the smid when creating output filename."""
        identifier = "ec"
        self.data = stats_manager.StatsManager(smid=identifier)
        self._populate_mock_stats()
        fname = os.path.basename(self.data.save_summary(self.tempdir))
        self.assertTrue(fname.startswith(identifier))

    def test_save_summary_json(self):
        """save_summary_json saves the added data properly in JSON format."""
        self._populate_mock_stats()
        fname = "unittest_summary.json"
        expected_fname = os.path.join(self.tempdir, fname)
        fname = self.data.save_summary_json(self.tempdir, fname)
        # Assert the reported fname is the same as the expected fname
        self.assertEqual(expected_fname, fname)
        # Assert only the reported fname is output (in the tempdir)
        self.assertEqual(set([os.path.basename(fname)]), set(os.listdir(self.tempdir)))
        with open(fname, "r", encoding="utf-8") as f:
            summary = json.load(f)
            self.assertAlmostEqual(100000.0, summary["A"]["mean"])
            self.assertEqual("milliwatt", summary["A"]["unit"])
            self.assertAlmostEqual(2.5, summary["B"]["mean"])
            self.assertEqual("millivolt", summary["B"]["unit"])

    def test_save_summary_json_smid(self):
        """save_summary_json uses the smid when creating output filename."""
        identifier = "ec"
        self.data = stats_manager.StatsManager(smid=identifier)
        self._populate_mock_stats()
        fname = os.path.basename(self.data.save_summary_json(self.tempdir))
        self.assertTrue(fname.startswith(identifier))

    def test_save_summary_json_no_unit(self):
        """save_summary_json marks unknown units properly as N/A."""
        self._populate_mock_stats_no_unit()
        self.data.calculate_stats()
        fname = "unittest_summary.json"
        fname = self.data.save_summary_json(self.tempdir, fname)
        with open(fname, "r", encoding="utf-8") as f:
            summary = json.load(f)
            self.assertEqual("blue", summary["A"]["unit"])
            # if no unit is specified, JSON should save 'N/A' as the unit.
            self.assertEqual("N/A", summary["B"]["unit"])


if __name__ == "__main__":
    unittest.main()
