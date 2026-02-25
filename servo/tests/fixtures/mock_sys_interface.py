# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Fixtures for mocking SysInterface."""

import logging
import os
import socket
from unittest.mock import patch

import pytest


class MockSysInterface:
    def __init__(self):
        self._sockets = {}
        self._fake_pty_counter = 0
        self._fd_to_ttyname = {}

    def openpty(self):
        primary, replica = socket.socketpair()
        m_fd = primary.fileno()
        s_fd = replica.fileno()
        self._sockets[m_fd] = primary
        self._sockets[s_fd] = replica
        self._fake_pty_counter += 1
        fake_name = f"/dev/pts/{self._fake_pty_counter}"
        self._fd_to_ttyname[m_fd] = fake_name
        self._fd_to_ttyname[s_fd] = fake_name
        return m_fd, s_fd

    def ttyname(self, fd):
        return self._fd_to_ttyname.get(fd, f"/dev/pts/{fd}")

    def chmod(self, path, mode):
        pass

    def fchown(self, _fd, _uid, _gid):
        pass

    def close(self, fd):
        if fd in self._sockets:
            self._sockets[fd].close()
            del self._sockets[fd]
        else:
            try:
                os.close(fd)
            except OSError as e:
                logging.debug("MockSysInterface failed to close real fd %s: %s", fd, e)

    def __getattr__(self, name):
        # pylint: disable=import-outside-toplevel
        # Fallback to the real os/subprocess methods for unmocked ones
        import servo.utils.sys_interface

        # Avoid recursion by bypassing our own wrapper and going to the standard library
        return getattr(servo.utils.sys_interface.SysInterface(), name)


@pytest.fixture(autouse=True)
def mock_sys_interface():
    """Mock the sys_interface singleton to use fast memory sockets."""
    mock_instance = MockSysInterface()
    with patch("servo.utils.sys_interface.sys_interface", mock_instance):
        yield mock_instance
