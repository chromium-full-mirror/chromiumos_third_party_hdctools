# Copyright 2016 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Terminal Freezer utility"""


import logging
import os
import re
import signal
import subprocess
import time

from servo.utils.sys_interface import sys_interface


def pid_namespace_used():
    """Checks to see if we are running with PID namespaces."""
    with open("/proc/1/cmdline", encoding="utf-8") as f:
        if "cros_sdk" in f.readline():
            return True
    return False


class TerminalFreezer:
    """SIGSTOP all processes (and their parents) that have the TTY open."""

    def __init__(self, tty):
        self._tty = tty
        self._logger = logging.getLogger("Terminal Freezer (%s)" % self._tty)
        self._processes = None
        if pid_namespace_used():
            self._logger.warning(
                "This chroot was not entered with"
                ' "cros_sdk --no-ns-pid", make sure not to interfere'
                " on ptys used by servod."
                ' Also note that "fwgdb" or "flash_ec" might not work'
                " (crbug.com/444931)."
            )

    def __enter__(self):
        ret = ""
        try:
            ret = sys_interface.check_output(
                ["lsof", "-FR", self._tty], stderr=subprocess.STDOUT, encoding="utf-8"
            )
        except subprocess.CalledProcessError:
            # Ignore non-zero return codes.
            pass

        self._processes = re.findall(r"^(?:R|p)(\d+)$", ret, re.MULTILINE)

        # Don't kill servod, we need that.
        servod_processes = []
        for p in self._processes:
            with open("/proc/%s/cmdline" % p, encoding="utf-8") as f:
                if "servod" in f.readline():
                    servod_processes.append(p)

        self._logger.debug("servod processes: %r", servod_processes)
        for p in servod_processes:
            self._processes.remove(p)

        # SIGSTOP parents before children.
        try:
            for p in reversed(self._processes):
                self._logger.debug("Sending SIGSTOP to process %s!", p)
                time.sleep(0.02)
                os.kill(int(p), signal.SIGSTOP)
        except OSError:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, _t, _v, _b):
        # ...and wake 'em up again in reverse order.
        for p in self._processes:
            self._logger.debug("Sending SIGCONT to process %s!", p)
            try:
                os.kill(int(p), signal.SIGCONT)
            except OSError as e:
                self._logger.error("Error when trying to unfreeze process %s: %s", p, e)
