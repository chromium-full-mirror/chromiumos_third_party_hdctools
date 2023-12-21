# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import time
from typing import Optional
import unittest

from servo_mfg import exec_util


def _runShortlivedProcess(cmd: str) -> Optional[int]:
    """Runs a process using the non-blocking API and kills it after at most 1 second.

    This is explicitly using exec_nonblocking to facilitate its
    testing, so don't replace with a call to exec_blocking, tempting
    as it may be.
    """
    process = exec_util.exec_nonblocking([cmd])
    graceTime = time.time() + 1
    while process.poll() is None:
        if time.time() > graceTime:
            raise ValueError("test timed out")
    return process.poll()


class TestHelpers(unittest.TestCase):
    """Test helper functions."""

    def test_Passthrough(self):
        """Test that hint returns the first element of cmd verbatim by default."""
        assert exec_util._exec_line(["a"]) == "a"
        assert exec_util._exec_line(["a", "b"]) == "a"
        assert exec_util._exec_line(["a"], hint=None) == "a"
        assert exec_util._exec_line(["a", "b"], hint=None) == "a"

    def test_Hint(self):
        """Test that the hint ends up at the right location."""
        assert exec_util._exec_line(["a"], hint="first hint"), "a (first hint)"
        assert exec_util._exec_line(["a", "b"], hint="another hint"), "a (another hint)"


class TestNonBlocking(unittest.TestCase):
    """Test non-blocking execution."""

    def test_ExitCode(self):
        """Test that we can eventually get the exit code of a process."""
        ret = _runShortlivedProcess("/usr/bin/true")
        assert ret == 0
        ret = _runShortlivedProcess("/usr/bin/false")
        assert ret == 1


class TestBlocking(unittest.TestCase):
    """Test blocking execution."""

    def test_QuickExit(self):
        """Test that a quickly exiting process just runs and exits cleanly."""
        (ret, _unused, _unused) = exec_util.exec_blocking(["/usr/bin/false"])
        assert ret == 1

    def test_Warning(self):
        """Test that after |timeout| seconds there's a warning on the log."""
        timeout = 2
        exceedTimeout = 1.5 * timeout
        doubleTimeout = 2 * timeout
        now = time.time()
        (ret, _unused, _unused) = exec_util.exec_blocking(
            ["/usr/bin/sleep", f"{exceedTimeout}"], timeout=timeout
        )
        then = time.time()
        assert ret == 0
        assert then - now >= exceedTimeout
        assert then - now < doubleTimeout

    def test_KilledProcess(self):
        """Test that the process is killed after 2*|timeout| seconds."""
        timeout = 2
        doubleTimeout = 2 * timeout
        exceedDouble = 1.5 * doubleTimeout
        now = time.time()
        (ret, _unused, _unused) = exec_util.exec_blocking(
            ["/usr/bin/sleep", f"{exceedDouble}"], timeout=timeout
        )
        then = time.time()
        assert ret is None
        assert then - now < exceedDouble

    def test_ConsoleOutput(self):
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
