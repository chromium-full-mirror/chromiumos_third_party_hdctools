# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# pylint: disable=import-outside-toplevel

"""Fixtures for mocking SysInterface."""

import os
import socket
import termios
from unittest.mock import patch

import pytest


class MockSysInterface:
    """Mock implementation of SysInterface using socket pairs instead of PTYs."""

    def __init__(self):
        self._sockets = set()
        self._fake_pty_counter = 0
        self._fd_to_ttyname = {}

    def openpty(self):
        """Mock openpty using socket.socketpair()."""
        primary, replica = socket.socketpair()
        m_fd = primary.fileno()
        s_fd = replica.fileno()
        self._sockets.add(m_fd)
        self._sockets.add(s_fd)
        # Detach the socket objects so Python doesn't close the FD on garbage collection
        primary.detach()
        replica.detach()
        self._fake_pty_counter += 1
        fake_name = f"/dev/pts/{self._fake_pty_counter}"
        self._fd_to_ttyname[m_fd] = fake_name
        self._fd_to_ttyname[s_fd] = fake_name
        return m_fd, s_fd

    def ttyname(self, fd):
        """Mock ttyname."""
        return self._fd_to_ttyname.get(fd, f"/dev/pts/{fd}")

    def chmod(self, unused_path, unused_mode):
        """Mock chmod."""

    def fchown(self, unused_fd, unused_uid, unused_gid):
        """Mock fchown."""

    def fchmod(self, unused_fd, unused_mode):
        """Mock fchmod."""

    def close(self, fd):
        """Mock close."""
        if fd in self._sockets:
            self._sockets.discard(fd)
        try:
            os.close(fd)
        except OSError:
            pass

    def fdopen(self, fd, *args, **kwargs):
        """Mock fdopen."""
        return os.fdopen(fd, *args, **kwargs)

    def write(self, fd, data):
        """Mock write."""
        return os.write(fd, data)

    def read(self, fd, n):
        """Mock read."""
        return os.read(fd, n)

    def tcgetattr(self, fd):
        """Mock tcgetattr."""
        if fd in self._sockets:
            return [0] * 7  # Return a mock_value list that matches termios expectations
        return termios.tcgetattr(fd)

    def tcsetattr(self, fd, unused_when, unused_attributes):
        """Mock tcsetattr."""
        if fd in self._sockets:
            return
        termios.tcsetattr(fd, unused_when, unused_attributes)

    def __getattr__(self, name):
        # Fallback to the real os/subprocess methods for unmocked ones
        import servo.utils.sys_interface

        return getattr(servo.utils.sys_interface.SysInterface(), name)


@pytest.fixture(autouse=True)
def mock_sys_interface():
    """Mock the sys_interface and underlying pty/os/termios calls globally."""
    mock_instance = MockSysInterface()

    # Patch the singleton
    with patch("servo.utils.sys_interface.sys_interface", mock_instance):
        # Patch the pty.openpty used by SysInterface
        with patch("pty.openpty", side_effect=mock_instance.openpty):
            # Patch os.ttyname
            with patch("os.ttyname", side_effect=mock_instance.ttyname):
                # Patch tty.setraw
                with patch("tty.setraw", return_value=None):
                    # Patch termios calls
                    with patch(
                        "termios.tcgetattr", side_effect=mock_instance.tcgetattr
                    ):
                        with patch(
                            "termios.tcsetattr", side_effect=mock_instance.tcsetattr
                        ):
                            yield mock_instance
