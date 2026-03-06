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
import threading
from unittest import mock


sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import local_agent
import pytest


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


@mock.patch("local_agent.glob.glob")
@mock.patch("local_agent.os.rename")
@mock.patch("local_agent.os.makedirs")
def test_init_storage_recovery(mock_makedirs, mock_rename, mock_glob):
    mock_glob.return_value = ["/path/to/job1.json.lock"]
    local_agent.init_storage()
    mock_makedirs.assert_called()
    mock_rename.assert_called_once_with("/path/to/job1.json.lock", "/path/to/job1.json")


@mock.patch("local_agent.requests.post")
@mock.patch("local_agent.glob.glob")
@mock.patch("local_agent.os.path.exists")
@mock.patch("local_agent.os.remove")
@mock.patch(
    "builtins.open", new_callable=mock.mock_open, read_data='{"job_id": "test_job"}'
)
def test_sync_with_orchestrator(
    mock_open, mock_remove, mock_exists, mock_glob, mock_post
):
    # Mock job download
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"jobs": [{"job_id": "new_job"}]}
    mock_exists.side_effect = (
        lambda p: "new_job" not in p
    )  # Simulate job doesn't exist locally

    # Mock result upload
    mock_glob.return_value = ["/path/to/results/test_job.json"]
    mock_post.return_value.status_code = 200

    local_agent.sync_with_orchestrator("http://mock")

    # Verify download
    mock_post.assert_any_call(
        "http://mock/api/jobs/sync", json={"existing_job_ids": ["test_job"]}, timeout=30
    )
    # open() was called for both writing the new job and reading the result.
    # The first call is 'w' for the new job.
    mock_open.assert_any_call(
        os.path.join(local_agent.JOBS_DIR, "new_job.json"), "w", encoding="utf-8"
    )

    # Verify upload
    assert "/api/results/test_job" in mock_post.call_args[0][0]

    # Verify cleanup
    mock_remove.assert_any_call("/path/to/results/test_job.json")


@mock.patch("local_agent.glob.glob")
@mock.patch("local_agent.execute_test")
@mock.patch("local_agent.os.rename")
@mock.patch("local_agent.os.remove")
@mock.patch("local_agent.os.path.exists")
@mock.patch(
    "builtins.open",
    new_callable=mock.mock_open,
    read_data='{"job_id": "job1", "servod_args": ["-s", "serial1"]}',
)
@mock.patch("local_agent.sync_with_orchestrator")
def test_worker_logic_claim_and_lock(
    unused_mock_sync,
    unused_mock_open,
    mock_exists,
    unused_mock_remove,
    mock_rename,
    mock_execute,
    mock_glob,
):
    # Setup state
    local_active_duts = set()
    dut_lock = threading.Lock()

    # Mock glob to return one job then stop
    mock_glob.side_effect = [["job1.json"], []]
    mock_exists.return_value = True
    mock_execute.return_value = {"exit_code": 0}

    # Run worker once
    stop_event = threading.Event()
    local_agent.worker(
        "http://mock", False, local_active_duts, dut_lock, stop_event=stop_event
    )

    # Verify job was claimed
    mock_rename.assert_called_once_with("job1.json", "job1.json.lock")
    # Verify execute_test was called
    mock_execute.assert_called_once()
    # Verify serial1 was added to local_active_duts during execution
    # (Worker is synchronous in this test, so it is removed by the time we check)
    assert "serial1" not in local_active_duts


@mock.patch("local_agent.glob.glob")
@mock.patch("local_agent.execute_test")
@mock.patch("local_agent.os.rename")
@mock.patch("local_agent.os.path.exists")
@mock.patch("builtins.open")
@mock.patch("local_agent.sync_with_orchestrator")
def test_dut_locking_prevention(
    unused_mock_sync,
    mock_open,
    mock_exists,
    mock_rename,
    mock_execute,
    mock_glob,
):
    # Setup state: serial1 is already busy
    local_active_duts = {"serial1"}
    dut_lock = threading.Lock()

    # Mock glob to return a job for serial1
    mock_glob.return_value = ["job_serial1.json"]
    mock_open.return_value.__enter__.return_value.read.return_value = (
        '{"job_id": "job2", "servod_args": ["-s", "serial1"]}'
    )
    mock_exists.return_value = True

    # Run worker once
    stop_event = threading.Event()
    local_agent.worker(
        "http://mock", False, local_active_duts, dut_lock, stop_event=stop_event
    )

    # Verify rename (claim) was NOT called because DUT is busy
    mock_rename.assert_not_called()
    # Verify execute_test was NOT called
    mock_execute.assert_not_called()
