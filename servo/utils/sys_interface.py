# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""System Interface wrapper for mocking."""

import contextlib
import os
import pty
import subprocess
from typing import Any, BinaryIO, Iterator, TextIO, Tuple, Union


class SysInterface:
    """Wrapper class for system calls to facilitate testing."""

    @contextlib.contextmanager
    def managed_pty(self) -> Iterator[Tuple[int, int]]:
        """Context manager for a PTY pair."""
        m_fd, s_fd = self.openpty()
        try:
            yield m_fd, s_fd
        finally:
            try:
                self.close(m_fd)
            except OSError:
                pass
            try:
                self.close(s_fd)
            except OSError:
                pass

    @contextlib.contextmanager
    def managed_pipe(self) -> Iterator[Tuple[int, int]]:
        """Context manager for a pipe."""
        r_fd, w_fd = self.pipe()
        try:
            yield r_fd, w_fd
        finally:
            try:
                self.close(r_fd)
            except OSError:
                pass
            try:
                self.close(w_fd)
            except OSError:
                pass

    @contextlib.contextmanager
    def managed_open(
        self, path: Union[str, bytes, os.PathLike], flags: int, mode: int = 0o777
    ) -> Iterator[int]:
        """Context manager for a file descriptor."""
        fd = self.open(path, flags, mode)
        try:
            yield fd
        finally:
            try:
                self.close(fd)
            except OSError:
                pass

    def system(self, command: str) -> int:
        return os.system(command)

    def openpty(self) -> Tuple[int, int]:
        return pty.openpty()

    def open(
        self, path: Union[str, bytes, os.PathLike], flags: int, mode: int = 0o777
    ) -> int:
        return os.open(path, flags, mode)

    def close(self, fd: int) -> None:
        os.close(fd)

    def pipe(self) -> Tuple[int, int]:
        return os.pipe()

    def fdopen(
        self, fd: int, *args: Any, **kwargs: Any
    ) -> Union[TextIO, BinaryIO, Any]:
        return os.fdopen(fd, *args, **kwargs)

    def write(self, fd: int, data: bytes) -> int:
        return os.write(fd, data)

    def read(self, fd: int, n: int) -> bytes:
        return os.read(fd, n)

    def chmod(self, path: Union[str, bytes, os.PathLike], mode: int) -> None:
        os.chmod(path, mode)

    def fchmod(self, fd: int, mode: int) -> None:
        os.fchmod(fd, mode)

    def fchown(self, fd: int, uid: int, gid: int) -> None:
        os.fchown(fd, uid, gid)

    def ttyname(self, fd: int) -> str:
        return os.ttyname(fd)

    def statvfs(self, path: Union[str, bytes, os.PathLike]) -> os.statvfs_result:
        return os.statvfs(path)

    def kill(self, pid: int, sig: int) -> None:
        os.kill(pid, sig)

    def rmdir(self, path: Union[str, bytes, os.PathLike]) -> None:
        os.rmdir(path)

    def remove(self, path: Union[str, bytes, os.PathLike]) -> None:
        os.remove(path)

    def call(self, *args: Any, **kwargs: Any) -> int:
        return subprocess.call(*args, **kwargs)

    def check_call(self, *args: Any, **kwargs: Any) -> int:
        return subprocess.check_call(*args, **kwargs)

    def check_output(self, *args: Any, **kwargs: Any) -> bytes:
        return subprocess.check_output(*args, **kwargs)

    def run(
        self, *args: Any, check: bool = False, **kwargs: Any
    ) -> subprocess.CompletedProcess:
        return subprocess.run(*args, check=check, **kwargs)

    def popen(self, *args: Any, **kwargs: Any) -> subprocess.Popen:
        return subprocess.Popen(*args, **kwargs)


sys_interface = SysInterface()
