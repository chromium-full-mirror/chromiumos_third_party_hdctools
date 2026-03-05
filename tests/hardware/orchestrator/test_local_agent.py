# pylint: disable=no-name-in-module
# pylint: disable=import-error
#!/usr/bin/env python3
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os

# pylint: disable=import-error, redefined-outer-name, wrong-import-position
import subprocess
import sys
from unittest import mock


sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import local_agent
import pytest
import requests


@pytest.fixture(autouse=True)
def mock_sleep():
    with mock.patch("time.sleep"):
        yield


@pytest.fixture
def mock_requests():
    with mock.patch("local_agent.requests") as mock_req:
        yield mock_req


@pytest.fixture
def mock_subprocess():
    with mock.patch("local_agent.subprocess.run") as mock_run:
        yield mock_run


@pytest.fixture
def mock_os_makedirs():
    with mock.patch("local_agent.os.makedirs") as mock_makedirs:
        yield mock_makedirs


@pytest.fixture
def mock_os_path_exists():
    with mock.patch("local_agent.os.path.exists") as mock_exists:
        yield mock_exists


@pytest.fixture
def mock_shutil():
    with mock.patch("local_agent.shutil") as mock_shutil:
        yield mock_shutil


def test_run_command_success(mock_subprocess):
    mock_subprocess.return_value = mock.MagicMock(stdout="OK", stderr="", returncode=0)
    result = local_agent.run_command(["echo", "hello"])
    assert result.stdout == "OK"
    mock_subprocess.assert_called_once()


def test_run_command_fail(mock_subprocess):
    cpe = subprocess.CalledProcessError(1, ["false"])
    cpe.stdout = ""
    cpe.stderr = "Error"
    mock_subprocess.side_effect = cpe
    with pytest.raises(subprocess.CalledProcessError):
        local_agent.run_command(["false"])

    mock_subprocess.side_effect = None
    mock_subprocess.return_value = cpe
    result = local_agent.run_command(["false"], check=False)
    assert result.returncode == 1
    assert result.stderr == "Error"


def test_poll_for_job_success(mock_requests):
    mock_response = mock.MagicMock()
    mock_response.json.return_value = {"job": {"job_id": "123", "image_name": "test"}}
    mock_requests.get.return_value = mock_response

    job = local_agent.poll_for_job("http://fake")
    assert job["job_id"] == "123"
    mock_requests.get.assert_called_once_with("http://fake/api/jobs/next", timeout=10)


def test_poll_for_job_none(mock_requests):
    mock_response = mock.MagicMock()
    mock_response.json.return_value = {"job": None}
    mock_requests.get.return_value = mock_response

    job = local_agent.poll_for_job("http://fake")
    assert job is None


def test_poll_for_job_error(mock_requests):
    mock_requests.get.side_effect = requests.exceptions.ConnectionError(
        "Test Connection Error"
    )
    # The try/except in the main code should handle this.
    job = local_agent.poll_for_job("http://fake")
    assert job is None
    mock_requests.get.assert_called_once()


def test_submit_results_success(mock_requests):
    mock_response = mock.MagicMock()
    mock_requests.post.return_value = mock_response
    local_agent.submit_results("http://fake", "123", {"data": "ok"})
    mock_requests.post.assert_called_once_with(
        "http://fake/api/results/123", json={"data": "ok"}, timeout=60
    )


@mock.patch("local_agent.run_command")
@mock.patch(
    "builtins.open",
    new_callable=mock.mock_open,
    read_data="Found XML overlay for board",
)
@mock.patch("local_agent.os.path.getctime")
@mock.patch("local_agent.os.path.exists")
@mock.patch("local_agent.glob.glob")
@mock.patch("local_agent.get_gsc_type")
def test_execute_test_success(
    unused_mock_get_gsc_type,
    mock_glob,
    mock_exists,
    mock_getctime,
    mock_open,
    mock_run_command,
    mock_shutil,
):
    job = {
        "job_id": "abc",
        "image_name": "test:latest",
        "test_commands": ["test"],
        "servod_args": ["-b", "brya"],
    }
    mock_run_command.return_value = mock.MagicMock(
        stdout="firmware v1", stderr="", returncode=0
    )
    mock_exists.return_value = True  # Simulate log file exists
    mock_glob.return_value = ["/tmp/log/latest.DEBUG"]
    mock_getctime.return_value = 123456789
    # mock_open().tell() should return an int
    mock_open.return_value.tell.return_value = 11  # 'log content' is 11 bytes

    results = local_agent.execute_test(job)

    assert results["exit_code"] == 0
    assert results["test_outputs"]["test"]["stdout"] == "firmware v1"
    assert "Found XML overlay for board" in results["log"]
    assert (
        mock_run_command.call_count == 8
    )  # pull, tag, start, wait, exec, stop, rm, rmi
    assert mock_shutil.rmtree.call_count == 2
    assert mock_open.call_count == 1
    mock_glob.assert_called_once()


@mock.patch("local_agent.run_command")
@mock.patch("local_agent.os.path.exists")
@mock.patch("local_agent.get_gsc_type")
def test_execute_test_fail_start(
    unused_mock_get_gsc_type, mock_exists, mock_run_command, mock_shutil
):
    job = {"job_id": "def", "image_name": "test:fail", "servod_args": ["-b", "brya"]}
    cpe = subprocess.CalledProcessError(1, ["start-servod"])
    cpe.stdout = None
    cpe.stderr = "Failed to start"

    # Simulate run_command behavior for each call in execute_test
    def run_command_side_effect(*args, **kwargs):
        del kwargs  # Unused
        cmd = args[0]
        cmd_str = cmd if isinstance(cmd, str) else " ".join(cmd)
        if "docker pull" in cmd_str:
            return mock.MagicMock(stdout="", stderr="", returncode=0)
        if "start-servod" in cmd_str:
            raise cpe
        return mock.MagicMock(stdout="", stderr="", returncode=0)  # stop, rm, rmi

    mock_run_command.side_effect = run_command_side_effect
    mock_exists.return_value = True

    results = local_agent.execute_test(job)

    assert results["exit_code"] == 1
    assert "Failed to start" in results["error"]
    assert mock_shutil.rmtree.call_count == 2
