# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import time
from typing import Optional
import unittest

from servo_mfg import exec_util


def _run_shortlived_process(cmd: str) -> Optional[int]:
    """Runs a process using the non-blocking API and kills it after at most 1 second.

    This is explicitly using exec_nonblocking to facilitate its
    testing, so don't replace with a call to exec_blocking, tempting
    as it may be.
    """
    process = exec_util.exec_nonblocking([cmd])
    grace_time = time.time() + 1
    while process.poll() is None:
        if time.time() > grace_time:
            raise ValueError("test timed out")
    return process.poll()


class TestHelpers(unittest.TestCase):
    """Test helper functions."""

    def test_passthrough(self):
        """Test that hint returns the first element of cmd verbatim by default."""
        assert exec_util._exec_line(["a"]) == "a"
        assert exec_util._exec_line(["a", "b"]) == "a"
        assert exec_util._exec_line(["a"], hint=None) == "a"
        assert exec_util._exec_line(["a", "b"], hint=None) == "a"

    def test_hint(self):
        """Test that the hint ends up at the right location."""
        assert exec_util._exec_line(["a"], hint="first hint"), "a (first hint)"
        assert exec_util._exec_line(["a", "b"], hint="another hint"), "a (another hint)"


class TestNonBlocking(unittest.TestCase):
    """Test non-blocking execution."""

    def test_exit_code(self):
        """Test that we can eventually get the exit code of a process."""
        ret = _run_shortlived_process("/usr/bin/true")
        assert ret == 0
        ret = _run_shortlived_process("/usr/bin/false")
        assert ret == 1


class TestBlocking(unittest.TestCase):
    """Test blocking execution."""

    def test_quick_exit(self):
        """Test that a quickly exiting process just runs and exits cleanly."""
        (ret, _unused, _unused) = exec_util.exec_blocking(["/usr/bin/false"])
        assert ret == 1

    def test_warning(self):
        """Test that after |timeout| seconds there's a warning on the log."""
        timeout = 2
        exceed_timeout = 1.5 * timeout
        double_timeout = 2 * timeout
        now = time.time()
        (ret, _unused, _unused) = exec_util.exec_blocking(
            ["/usr/bin/sleep", f"{exceed_timeout}"], timeout=timeout
        )
        then = time.time()
        assert ret == 0
        assert then - now >= exceed_timeout
        assert then - now < double_timeout

    def test_killed_process(self):
        """Test that the process is killed after 2*|timeout| seconds."""
        timeout = 2
        double_timeout = 2 * timeout
        exceed_double = 1.5 * double_timeout
        now = time.time()
        (ret, _unused, _unused) = exec_util.exec_blocking(
            ["/usr/bin/sleep", f"{exceed_double}"], timeout=timeout
        )
        then = time.time()
        assert ret is None
        assert then - now < exceed_double

    def test_console_output(self):
        """Test that stdout and stderr are reported back."""
        (ret, stdout, stderr) = exec_util.exec_blocking(
            ["/bin/sh", "-c", "echo foo && echo bar"]
        )
        assert ret == 0
        assert stdout.decode("utf-8") == "foo\nbar\n"
        assert stderr.decode("utf-8") == ""

        (ret, stdout, stderr) = exec_util.exec_blocking(
            ["/bin/sh", "-c", "echo foo >&2 && echo bar >&2"]
        )
        assert ret == 0
        assert stdout.decode("utf-8") == ""
        assert stderr.decode("utf-8") == "foo\nbar\n"

        (ret, stdout, stderr) = exec_util.exec_blocking(
            ["/bin/sh", "-c", "echo foo && echo bar >&2"]
        )
        assert ret == 0
        assert stdout.decode("utf-8") == "foo\n"
        assert stderr.decode("utf-8") == "bar\n"


if __name__ == "__main__":
    unittest.main()
