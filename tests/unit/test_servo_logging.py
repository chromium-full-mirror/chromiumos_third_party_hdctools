# Copyright 2019 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Unit-tests to ensure that servod's logging handler works as intended."""

import copy
import datetime
import hashlib
import logging
import os
import shutil
import tempfile
import unittest

from servo.common.utils import servo_logging


# There is 1 file that are exempt from the backup count.
# - the 'latest' symbolic link
# - the open file that isn't a backup
BACKUP_COUNT_EXEMPT_FILES = 2


def get_file_md5sum(path):
    """Return the md5 checksum of the file at |path|."""
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def get_rolled_fn(logfile, rotations):
    """Helper to get filename of |logfile| after |rotations| log rotations."""
    return "%s.%d" % (logfile, rotations)


class TestServodRotatingFileHandler(unittest.TestCase):
    # These are module wide attributes to cache and restore after tests
    # in case the tests wish to modify them.
    MODULE_ATTRS = [
        "MAX_LOG_BYTES",  # Max bytes a log file can grow to.
        "LOG_BACKUP_COUNT",  # Number of rotated logfiles to keep.
        "COMPRESSION_SUFFIX",  # Filetype suffix for compressed logs.
        "LOG_FILE_PREFIX",  # Log file name.
        "TS_FILE",  # File name to cache the instance's timestamp.
        "TS_FORMAT",
    ]  # Format string to for timestamps.

    def setUp(self):
        """Set up data, create logging directory, cache module data."""
        unittest.TestCase.setUp(self)
        self.logdir = tempfile.mkdtemp()
        self.loglevel = logging.DEBUG
        self.fmt = ""
        self.ts = servo_logging._generateTs()
        self.test_logger = logging.getLogger("Test")
        self.test_logger.setLevel(logging.DEBUG)
        self.test_logger.propagate = False
        self.module_defaults = {}
        # Cache the module wide attributes to restore them after each test again.
        for attr in self.MODULE_ATTRS:
            self.module_defaults[attr] = getattr(servo_logging, attr)

    def tearDown(self):
        """Delete logging directory, remove handlers,restore module data."""
        shutil.rmtree(self.logdir)
        unittest.TestCase.tearDown(self)
        for handler in self.test_logger.handlers:
            handler.close()
        self.test_logger.handlers = []
        # Restore cached module attributes.
        for attr, val in self.module_defaults.items():
            setattr(servo_logging, attr, val)

    def _generate_sorted_files_from_tags(self, tags):
        """Helper sub-test that given a tag list generates sorted log-files.
        Args:
          tags: list of tags to generate (fake) log file names for

        Returns:
          tuple t, where t[0] sorted_files: the log file names in sorted order
                         t[1] shuffled_files: the same files as t[0] but shuffled
        """
        loglevel_str = logging.getLevelName(self.loglevel)
        # Range crossing 10, as just sorting by string would place 10 above 9
        ints = [str(i) for i in range(7, 13)]
        files = []
        for tag in tags:
            tag_files = ["%s.%s.%s" % (tag, loglevel_str, i) for i in ints]
            # The open log file has no int or compression suffix. Add a sample too.
            tag_files.insert(0, "%s.%s" % (tag, loglevel_str))
            files.extend(tag_files)
        # At this point the files in files are sorted. We now need to make a copy,
        # shuffle it, and then make sure after our custom sort function, the copy
        # looks the same.
        shuffled_files = copy.copy(files)
        # Implement this shuffling instead of random.shuffle to ensure that
        # random.shuffle does not randomly generate the same sequence again.
        shuffling_iterations = len(shuffled_files)
        for i in range(shuffling_iterations):
            shuffled_files.append(shuffled_files.pop(i))
        # Assert the order is not the same anymore.
        assert shuffled_files != files
        return (files, shuffled_files)

    def test_tag_sorting(self):
        """Test the tag sorting function."""
        # Only one tag as we want to test sorting within one tag.
        tags = ["test-tag"]
        files, shuffled_files = self._generate_sorted_files_from_tags(tags)
        shuffled_files.sort(key=servo_logging._sortLogTagFn)
        # Assert the order is the same again.
        assert shuffled_files == files

    def test_logfile_sorting(self):
        """Testing sorting by tags as well as by the index within a tag."""
        # The tag in the real implementation is a time-stamp. Therefore, the
        # first element should always be "higher" element after sorting, the
        # newer timestamp. Simulate here with a z instead of a t.
        tags = ["test-zag", "test-tag"]
        loglevel_str = logging.getLevelName(self.loglevel)
        files, shuffled_files = self._generate_sorted_files_from_tags(tags)
        shuffled_files = servo_logging._sortLogs(shuffled_files, loglevel_str)
        # Assert the order is the same again.
        assert shuffled_files == files

    def test_logger_logs_to_file(self):
        """Basic testing that content is being output to the file."""
        test_str = "This is a test string to make sure there is logging."
        handler = servo_logging.ServodRotatingFileHandler(
            logdir=self.logdir, ts=self.ts, fmt=self.fmt, level=self.loglevel
        )
        self.test_logger.addHandler(handler)
        self.test_logger.info(test_str)
        with open(handler.baseFilename, "r", encoding="utf-8") as log:
            assert log.read().strip() == test_str

    def test_rotation_occurs_when_file_grows_too_large(self):
        """Growing log-file beyond limit causes a rotation."""
        test_max_log_bytes = 40
        setattr(servo_logging, "MAX_LOG_BYTES", test_max_log_bytes)
        handler = servo_logging.ServodRotatingFileHandler(
            logdir=self.logdir, ts=self.ts, fmt=self.fmt, level=self.loglevel
        )
        self.test_logger.addHandler(handler)
        # The first log is only 20 bytes and should not cause rotation.
        log1 = "Here are 20 bytes la"
        # The second log is 40 bytes and should cause rotation.
        log2 = "This is an attempt to make 40 bytes laaa"
        self.test_logger.info(log1)
        # No rolling should have occurred yet.
        assert not os.path.exists(get_rolled_fn(handler.baseFilename, 1))
        # Rolling should have occurred by now.
        self.test_logger.info(log2)
        assert os.path.exists(get_rolled_fn(handler.baseFilename, 1))

    def test_delete_multiple_past_backup_count(self):
        """No more than backup count logs are kept."""
        # Set the backup count to only be 3 compressed for this test.
        new_count = servo_logging.LOG_BACKUP_COUNT + 3
        handler = servo_logging.ServodRotatingFileHandler(
            logdir=self.logdir,
            backup_count=new_count,
            ts=self.ts,
            fmt=self.fmt,
            level=self.loglevel,
        )
        for _unused in range(2 * new_count):
            handler.doRollover()
            # The assertion checks that there are at most new_count files.
            assert len(os.listdir(handler.logdir)) <= (
                new_count + BACKUP_COUNT_EXEMPT_FILES
            )
        handler.close()

    def test_delete_multiple_instances_past_backup_count(self):
        """No more than backup count logs are kept across instances.

        Additionally, this test validates that the oldest get deleted.
        """
        new_count = servo_logging.LOG_BACKUP_COUNT + 20
        handler = servo_logging.ServodRotatingFileHandler(
            logdir=self.logdir,
            backup_count=new_count,
            ts=self.ts,
            fmt=self.fmt,
            level=self.loglevel,
        )
        for _unused in range(new_count):
            handler.doRollover()
            # The assertion checks that there are at most new_count files.
            assert len(os.listdir(handler.logdir)) <= (
                new_count + BACKUP_COUNT_EXEMPT_FILES
            )
        assert len(os.listdir(handler.logdir)) == (
            new_count + BACKUP_COUNT_EXEMPT_FILES
        )
        # Change the timestamp and create a new instance. Rotate out all old files.
        new_ts = servo_logging._generateTs()
        handler.close()

        handler = servo_logging.ServodRotatingFileHandler(
            logdir=self.logdir,
            backup_count=new_count,
            ts=new_ts,
            fmt=self.fmt,
            level=self.loglevel,
        )
        for _unused in range(new_count):
            handler.doRollover()
            # The assertion checks that there are at most new_count files.
            assert len(os.listdir(handler.logdir)) <= (
                new_count + BACKUP_COUNT_EXEMPT_FILES
            )
        assert len(os.listdir(handler.logdir)) == (
            new_count + BACKUP_COUNT_EXEMPT_FILES
        )
        # After two new_count rotations, the first timestamp should no longer
        # be around as it has been rotated out. Verify that.
        assert not any(self.ts in f for f in os.listdir(handler.logdir))
        handler.close()

    def test_sort_logs_one_instance(self):
        """Verify log-sorting is per instance in order of newest first."""
        loglevel = logging.getLevelName(self.loglevel)
        # Generate fake logfile names.
        instance_tag = "%s.%s" % (
            servo_logging.LOG_FILE_PREFIX,
            servo_logging._generateTs(),
        )
        # This mimics the active, open logfile.
        logfiles = ["%s.%s" % (instance_tag, loglevel)]
        # suffix .0 will never be generated if the main file still exists.
        # Start here at suffix .1 to simulate proper rotation.
        for i in range(1, 6):
            logfiles.append("%s.%s.%d" % (instance_tag, loglevel, i))
        sorted_logfiles = copy.copy(logfiles)
        # Do not use randomization but rather swap each element pair to
        # created a predictable unsorted system.
        for idx in range(0, len(logfiles), 2):
            placeholder = logfiles[idx]
            logfiles[idx] = logfiles[idx + 1]
            logfiles[idx + 1] = placeholder
        allegedly_sorted_logfiles = servo_logging._sortLogs(logfiles, loglevel)
        assert allegedly_sorted_logfiles == sorted_logfiles

    def test_sort_logs_across_instances(self):
        """Verify log-sorting is across instances newest first."""
        loglevel = logging.getLevelName(self.loglevel)
        # Generate fake logfile names.
        stale_tag = "%s.%s" % (
            servo_logging.LOG_FILE_PREFIX,
            servo_logging._generateTs(),
        )
        fresh_tag = "%s.%s" % (
            servo_logging.LOG_FILE_PREFIX,
            servo_logging._generateTs(
                datetime.datetime.now() + datetime.timedelta(seconds=1)
            ),
        )
        # This mimics the active, open logfiles.
        logfiles = ["%s.%s" % (fresh_tag, loglevel)]
        logfiles.append("%s.%s" % (stale_tag, loglevel))
        for i in range(1, 6):
            # Adding them both at the same time here ensures a predictable way of
            # having the list be unsorted.
            logfiles.append("%s.%s.%d" % (fresh_tag, loglevel, i))
            logfiles.append("%s.%s.%d" % (stale_tag, loglevel, i))
        unsorted_logfiles = copy.copy(logfiles)
        # The fresh tags are every odd element in the list.
        sorted_logfiles = unsorted_logfiles[0::2] + unsorted_logfiles[1::2]
        # Do not use randomization but rather swap each element pair to
        # created a predictable unsorted system.
        for idx in range(0, len(logfiles), 2):
            placeholder = logfiles[idx]
            logfiles[idx] = logfiles[idx + 1]
            logfiles[idx + 1] = placeholder
        # The expectation here is that at first all fresh_tags show up, followed
        # by all state_tags, and within those, there is ordering.
        allegedly_sorted_logfiles = servo_logging._sortLogs(logfiles, loglevel)
        self.assertEqual(allegedly_sorted_logfiles, sorted_logfiles)

    def test_rotation_moves_files_along(self):
        """Rotation moves the same logfile's sequence number forward."""
        # Number of times this test will rotate out the log file after its first
        # compression.
        rotations = 3
        # The rotation starts at 2 as the first compression happens at index 1.
        start_rotation = 2
        handler = servo_logging.ServodRotatingFileHandler(
            logdir=self.logdir, ts=self.ts, fmt=self.fmt, level=self.loglevel
        )
        self.test_logger.addHandler(handler)
        self.test_logger.info("This is just some test content.")
        handler.doRollover()
        # At this point the compressed log-file should exist.
        rolled_fn = get_rolled_fn(handler.baseFilename, 1)
        assert os.path.exists(rolled_fn)
        md5sum = get_file_md5sum(rolled_fn)
        for i in range(start_rotation, start_rotation + rotations):
            handler.doRollover()
            rolled_fn = get_rolled_fn(handler.baseFilename, i)
            # Ensure that the file was rotated properly.
            assert os.path.exists(rolled_fn)
            # Ensure that the file is the same that started the rotation by validating
            # the checksum.
            assert md5sum == get_file_md5sum(rolled_fn)
        handler.close()

    def test_handle_existing_log_dir(self):
        """The output directory for a specific port already existing is fine."""
        output_dir = servo_logging._buildLogdirName(self.logdir, "servod", 9998)
        os.makedirs(output_dir)
        handler = servo_logging.ServodRotatingFileHandler(
            logdir=self.logdir, ts=self.ts, fmt=self.fmt, level=self.loglevel
        )
        assert os.path.isdir(output_dir)
        handler.close()


if __name__ == "__main__":
    unittest.main()
