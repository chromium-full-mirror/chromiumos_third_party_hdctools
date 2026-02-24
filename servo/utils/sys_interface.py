# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""System Interface wrapper for mocking."""

import os
import pty
import subprocess


class SysInterface:
    """Wrapper class for system calls to facilitate testing."""

    def system(self, command):
        return os.system(command)

    def openpty(self):
        return pty.openpty()

    def open(self, path, flags, mode=0o777):
        return os.open(path, flags, mode)

    def close(self, fd):
        os.close(fd)

    def pipe(self):
        return os.pipe()

    def fdopen(self, fd, *args, **kwargs):
        return os.fdopen(fd, *args, **kwargs)

    def write(self, fd, data):
        return os.write(fd, data)

    def read(self, fd, n):
        return os.read(fd, n)

    def chmod(self, path, mode):
        os.chmod(path, mode)

    def fchown(self, fd, uid, gid):
        os.fchown(fd, uid, gid)

    def ttyname(self, fd):
        return os.ttyname(fd)

    def statvfs(self, path):
        return os.statvfs(path)

    def kill(self, pid, sig):
        os.kill(pid, sig)

    def rmdir(self, path):
        os.rmdir(path)

    def remove(self, path):
        os.remove(path)

    def call(self, *args, **kwargs):
        return subprocess.call(*args, **kwargs)

    def check_call(self, *args, **kwargs):
        return subprocess.check_call(*args, **kwargs)

    def check_output(self, *args, **kwargs):
        return subprocess.check_output(*args, **kwargs)

    def run(self, *args, check=False, **kwargs):
        return subprocess.run(*args, check=check, **kwargs)

    def popen(self, *args, **kwargs):
        return subprocess.Popen(*args, **kwargs)


sys_interface = SysInterface()
