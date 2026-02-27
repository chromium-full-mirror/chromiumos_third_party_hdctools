#!/usr/bin/env python3
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# pylint: disable=import-error
import argparse
import glob
import json
import os
import shutil
import subprocess
import tempfile
import time

import requests


DEFAULT_ORCHESTRATOR_URL = "http://localhost:5002"  # Requires SSH -L tunnel
POLL_INTERVAL = 10  # Seconds


def run_command(command, shell=False, check=True):
    if isinstance(command, str):
        print(f"Running: {command}")
    else:
        print(f"Running: {' '.join(command)}")
    try:
        result = subprocess.run(
            command, shell=shell, check=check, capture_output=True, text=True
        )
        print(f"Output:\n{result.stdout}")
        if result.stderr:
            print(f"Stderr:\n{result.stderr}")
        return result
    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit code {e.returncode}: {' '.join(command)}")
        print(f"Stdout:\n{e.stdout}")
        print(f"Stderr:\n{e.stderr}")
        if check:
            raise
        return e


def poll_for_job(orchestrator_url):
    try:
        response = requests.get(f"{orchestrator_url}/api/jobs/next", timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("job")
    except Exception as e:  # Broad exception for robustness
        print(f"Error polling orchestrator: {e}")
        return None


def submit_results(orchestrator_url, job_id, result_data):
    try:
        response = requests.post(
            f"{orchestrator_url}/api/results/{job_id}", json=result_data, timeout=60
        )
        response.raise_for_status()
        print(f"Successfully submitted results for job {job_id}")
    except requests.exceptions.RequestException as e:
        print(f"Error submitting results for job {job_id}: {e}")


def execute_test(job):
    job_id = job["job_id"]
    image_name = job["image_name"]
    test_commands = job.get("test_commands", [])
    if not isinstance(test_commands, list):
        test_commands = [test_commands]  # Ensure it's a list

    run_id = job_id.split("-")[0]
    base_name = f"servod_test_{run_id}"
    container_name = f"{base_name}-docker_servod"  # Expected name by start-servod

    # Create a unique temporary base log directory
    temp_log_base = os.path.join(tempfile.gettempdir(), f"servod_testing_{run_id}")
    if os.path.exists(temp_log_base):
        shutil.rmtree(temp_log_base, ignore_errors=True)
    os.makedirs(temp_log_base, exist_ok=True)
    # This is the directory start-servod will create its subfolder in
    log_dir_for_job = os.path.join(temp_log_base, base_name)

    results = {
        "log": "",
        "exit_code": 1,
        "error": "",
        "test_outputs": {},
        "executed_start_cmd": [],
    }

    try:
        print(f"--- Starting Job: {job_id} ---")
        print(f"DEBUG Job Payload: {json.dumps(job, indent=2)}")

        print(f"Pulling image: {image_name}")
        # run_command(["docker", "pull", image_name])

        print(f"Re-tagging {image_name} as servod:dev for start-servod")
        run_command(["docker", "tag", image_name, "servod:dev"])

        print(f"Starting servod container, base name: {base_name}")
        print(f"Host log base: {temp_log_base}")
        start_cmd = [
            "start-servod",
            *job.get("start_servod_args", ["-c", "local"]),
            "-n",
            base_name,
            "--logs",
            temp_log_base,
            "--",
            *job.get("servod_args", []),
        ]
        results["executed_start_cmd"] = start_cmd
        string_start_cmd = " ".join(start_cmd)
        results["executed_start_cmd"] = string_start_cmd
        run_command(string_start_cmd, shell=True)

        # Wait for servod to be ready
        print(f"Waiting for servod to become active in {container_name}...")
        wait_cmd = [
            "docker",
            "exec",
            container_name,
            "servodtool",
            "instance",
            "wait-for-active",
            "-p",
            "9999",
            "--timeout",
            "60",
        ]
        run_command(wait_cmd)
        print("servod is active.")

        print("Running test commands...")
        for command in test_commands:
            print(f"  Executing: dut-control {command}")
            test_cmd = [
                "docker",
                "exec",
                container_name,
                "dut-control",
            ] + command.split()
            test_result = run_command(test_cmd)
            results["test_outputs"][command] = {
                "stdout": test_result.stdout,
                "stderr": test_result.stderr,
                "exit_code": test_result.returncode,
            }
            if test_result.returncode != 0:
                raise subprocess.CalledProcessError(
                    test_result.returncode,
                    test_cmd,
                    test_result.stdout,
                    test_result.stderr,
                )

        results["exit_code"] = 0
        print(f"--- Job {job_id} Completed ---")

    except subprocess.CalledProcessError as e:
        results["error"] = (
            f"Command failed: {e}\nArgs: {e.cmd}\n"
            f"Stdout: {e.stdout}\nStderr: {e.stderr}"
        )
        print(f"Error during job {job_id}: {e}")
    except Exception as e:
        results["error"] = f"An unexpected error occurred: {e}"
        print(f"Unexpected error during job {job_id}: {e}")
    finally:
        print("Stopping servod...")
        # stop-servod uses the base name
        run_command(["stop-servod", "--container_name", base_name], check=False)
        time.sleep(2)  # Give logs time to flush

        print("Collecting logs...")
        container_log_dir = log_dir_for_job  # Corrected path
        if os.path.exists(container_log_dir):
            debug_files = glob.glob(os.path.join(container_log_dir, "*.DEBUG"))
            if debug_files:
                latest_log = max(debug_files, key=os.path.getctime)
                print(f"Log file found: {latest_log}")
                try:
                    with open(latest_log, "rb") as f:
                        f.seek(0, os.SEEK_END)
                        file_size = f.tell()
                        seek_to = max(0, file_size - 1024 * 1024)  # Read last 1MB
                        f.seek(seek_to)
                        log_content = f.read().decode("utf-8", errors="replace")
                        results["log"] = (
                            f"--- servod log ({os.path.basename(latest_log)}) ---\n"
                            f"{log_content}"
                        )
                except Exception as log_e:
                    print(f"Error reading log file: {log_e}")
                    results["log"] = (
                        f"\n\n--- servod log ---\nError reading log: {log_e}"
                    )
            else:
                results["log"] = (
                    f"\n\n--- servod log ---\n"
                    f"No .DEBUG files found in {container_log_dir}"
                )
        else:
            results["log"] = (
                f"\n\n--- servod log ---\n"
                f"Log directory not found at {container_log_dir}"
            )

        print("Cleaning up local log directory.")
        if os.path.exists(temp_log_base):
            shutil.rmtree(temp_log_base, ignore_errors=True)
        # remove the container
        run_command(["docker", "rm", "-f", container_name], check=False)
        # Clean up the temporary tag
        run_command(["docker", "rmi", "servod:dev"], check=False)

    return results


def main():
    parser = argparse.ArgumentParser(description="Local agent for servod testing.")
    parser.add_argument(
        "--orchestrator_url",
        default=DEFAULT_ORCHESTRATOR_URL,
        help="URL of the Cloudtop orchestrator service",
    )
    args = parser.parse_args()

    print(
        f"Local agent started. Polling {args.orchestrator_url} every "
        f"{POLL_INTERVAL} seconds."
    )

    while True:
        job = poll_for_job(args.orchestrator_url)
        if job:
            job_id = job["job_id"]
            print(f"Found job: {job_id}")
            test_results = execute_test(job)
            submit_data = {
                "job_id": job_id,
                "exit_code": test_results.get("exit_code"),
                "error": test_results.get("error"),
                "log": test_results.get("log"),
                "executed_start_cmd": test_results.get("executed_start_cmd"),
                "test_outputs": test_results.get("test_outputs"),
            }
            print(f"Submitting results for job {job_id}")
            submit_results(args.orchestrator_url, job_id, submit_data)
        # else:
        # print("No jobs found.") # Too noisy

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
