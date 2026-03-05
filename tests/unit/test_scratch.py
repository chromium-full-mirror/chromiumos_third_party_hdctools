# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import socket
from unittest import mock

import pytest

from servo.utils import scratch


@pytest.fixture(name="mock_scratch")
def mock_scratch_fixture(tmp_path):
    return scratch.Scratch(scratch=str(tmp_path))


def test_scratch_add_remove(mock_scratch, tmp_path):
    # pylint: disable=unused-argument
    mock_scratch.add_entry(9999, ["12345", "67890"], 123)

    entries = mock_scratch.get_all_entries()
    assert len(entries) == 1
    assert entries[0]["port"] == 9999
    assert entries[0]["serials"] == ["12345", "67890"]
    assert entries[0]["pid"] == 123

    mock_scratch.remove_entry(9999)
    assert len(mock_scratch.get_all_entries()) == 0


def test_scratch_find_by_id(mock_scratch):
    mock_scratch.add_entry(9999, ["12345"], 123)

    # Find by port
    entry = mock_scratch.find_by_id(9999)
    assert entry["port"] == 9999

    # Find by serial
    entry = mock_scratch.find_by_id("12345")
    assert entry["port"] == 9999

    # Not found
    with pytest.raises(scratch.ScratchError):
        mock_scratch.find_by_id("99999")


def test_scratch_mark_active(mock_scratch, tmp_path):
    # pylint: disable=unused-argument
    mock_scratch.add_entry(9999, ["12345"], 123)
    mock_scratch.mark_active(9999)

    # mark_active updates the entry JSON to have ACTIVE_ENTRY_KEY=True
    entry = mock_scratch.find_by_id(9999)
    assert entry["active"] is True


def test_scratch_sanitize_removes_dead(mock_scratch, tmp_path):
    # pylint: disable=unused-argument
    mock_scratch.add_entry(9999, ["12345"], 123)

    with mock.patch("socket.socket") as mock_sock_class:
        mock_sock = mock_sock_class.return_value
        # Succeeds -> removes
        # pylint: disable=protected-access
        mock_scratch._sanitize()
        assert len(mock_scratch.get_all_entries()) == 0

        mock_scratch.add_entry(8888, ["54321"], 456)
        # Fails -> keeps
        mock_sock.bind.side_effect = socket.error("Port in use")
        mock_scratch._sanitize()
        assert len(mock_scratch.get_all_entries()) == 1


def test_scratch_generate_entry_from_port(mock_scratch):
    # Patch ServoClient in servo.utils.scratch (if it's imported there)
    # or just patch where it is defined if it's imported by name.
    # Scratch imports 'from servo.core.client import ServoClient'
    with mock.patch(
        "servo.common.utils.keyboard_handlers.GrpcClient.create_grpc_channel"
    ), mock.patch("servo.core.client.ServoClient") as mock_client_class:
        mock_client = mock_client_class.return_value
        # pylint: disable=protected-access
        mock_client._server.echo.return_value = "ECH0ING: nonsense"
        mock_client._server.get_servo_serials.return_value = {"0": "12345"}
        mock_client.get.return_value = 123

        entry_status = mock_scratch.generate_entry_from_port(9999)
        assert entry_status is True

        entry = mock_scratch.find_by_id(9999)
        assert entry["port"] == 9999
        assert entry["serials"] == ["12345"]
