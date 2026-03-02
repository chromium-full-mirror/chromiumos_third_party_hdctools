#!/usr/bin/env python3
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# pylint: disable=import-error,line-too-long
import argparse
import glob
import json
import logging
import os
import shutil
import subprocess
import tempfile
import time

import requests


logger = logging.getLogger(__name__)


class LocalAgentError(Exception):
    """Custom exception for local agent testing failures."""


DEFAULT_ORCHESTRATOR_URL = "http://localhost:5002"  # Requires SSH -L tunnel
POLL_INTERVAL = 10  # Seconds


def run_command(command, shell=False, check=True):
    if isinstance(command, str):
        cmd_str = command
    else:
        cmd_str = " ".join(command)

    logger.info("Running: %s", cmd_str)
    try:
        result = subprocess.run(
            command, shell=shell, check=check, capture_output=True, text=True
        )
        logger.debug("Output:\n%s", result.stdout)
        if result.stderr:
            logger.debug("Stderr:\n%s", result.stderr)
        return result
    except subprocess.CalledProcessError as e:
        logger.error("Command failed with exit code %d: %s", e.returncode, cmd_str)
        logger.error("Stdout:\n%s", e.stdout)
        logger.error("Stderr:\n%s", e.stderr)
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
        logger.warning("Error polling orchestrator: %s", e)
        return None


def submit_results(orchestrator_url, job_id, result_data):
    try:
        response = requests.post(
            f"{orchestrator_url}/api/results/{job_id}", json=result_data, timeout=60
        )
        response.raise_for_status()
        logger.info("Successfully submitted results for job %s", job_id)
    except requests.exceptions.RequestException as e:
        logger.error("Error submitting results for job %s: %s", job_id, e)


def find_servo_usb_path():
    """Finds a Google USB device (18d1) in sysfs."""
    paths = glob.glob("/sys/bus/usb/devices/*")
    for path in paths:
        id_vendor_path = os.path.join(path, "idVendor")
        if os.path.exists(id_vendor_path):
            with open(id_vendor_path, "r", encoding="utf-8") as f:
                if f.read().strip() == "18d1":
                    return path
    return None


def execute_test(job, dry_run=False):
    job_id = job["job_id"]
    image_name = job["image_name"]
    test_commands = job.get("test_commands", [])
    if not isinstance(test_commands, list):
        test_commands = [test_commands]  # Ensure it's a list

    fault_injection = job.get("fault_injection", [])
    lifecycle_test = job.get("lifecycle_test", False)

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
        logger.info("--- Starting Job: %s ---", job_id)
        logger.debug("DEBUG Job Payload: %s", json.dumps(job, indent=2))

        start_args = job.get("start_servod_args", ["-c", "local"])
        s_args = job.get("servod_args", [])
        start_cmd = [
            "start-servod",
            *start_args,
            "-n",
            base_name,
            "--logs",
            temp_log_base,
            "--",
            *s_args,
        ]
        string_start_cmd = " ".join(start_cmd)
        results["executed_start_cmd"] = string_start_cmd

        if dry_run:
            logger.info("DRY RUN: Would pull image %s", image_name)
            logger.info("DRY RUN: Would execute start cmd: %s", string_start_cmd)
            results["exit_code"] = 0
            return results

        logger.info("Pulling image: %s", image_name)
        try:
            run_command(["docker", "pull", image_name])
        except subprocess.CalledProcessError as e:
            raise LocalAgentError(
                f"Failed to pull Docker image: {image_name}. Network issue or image not found."
            ) from e

        logger.info("Re-tagging %s as servod:dev for start-servod", image_name)
        run_command(["docker", "tag", image_name, "servod:dev"])

        logger.info("Starting servod container, base name: %s", base_name)
        logger.info("Host log base: %s", temp_log_base)

        logger.debug("received start_servod_args=%s", start_args)
        logger.debug("received servod_args=%s", s_args)

        # LIFECYCLE TEST
        if lifecycle_test:
            logger.info("Running Lifecycle Verification Test")
            run_command(string_start_cmd, shell=True)
            time.sleep(5)

            run_command(["stop-servod", "--container_name", base_name])
            time.sleep(2)

            # Assert container is gone
            ps_res = run_command(["docker", "ps", "-q", "-f", f"name={container_name}"])
            if ps_res.stdout.strip():
                raise LocalAgentError("Container is still running after stop-servod!")

            # Assert logs exist
            if not os.path.exists(log_dir_for_job):
                raise LocalAgentError(
                    f"Log directory {log_dir_for_job} was not created!"
                )

            results["exit_code"] = 0
            return results

        # NORMAL / FAULT / STRESS START

        run_command(string_start_cmd, shell=True)

        # Wait for servod to be ready
        logger.info("Waiting for servod to become active in %s...", container_name)
        run_command(
            [
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
        )
        logger.info("servod is active.")

        # FAULT INJECTION
        if "usb_disconnect" in fault_injection:
            logger.info("Simulating USB Disconnect...")
            servo_path = find_servo_usb_path()
            if not servo_path:
                raise LocalAgentError(
                    "Could not find a Google USB device (18d1) to unbind."
                )

            unbind_file = "/sys/bus/usb/drivers/usb/unbind"
            bind_file = "/sys/bus/usb/drivers/usb/bind"
            device_name = os.path.basename(servo_path)

            try:
                # Unbind (simulate unplug)
                run_command(f"echo -n '{device_name}' > {unbind_file}", shell=True)
                time.sleep(5)  # Give watchdog time to notice

                # Check if container cleanly exited
                ps_res = run_command(
                    ["docker", "ps", "-q", "-f", f"name={container_name}"]
                )
                if ps_res.stdout.strip():
                    raise LocalAgentError(
                        "Container did NOT exit cleanly after USB unbind!"
                    )

                results["exit_code"] = 0
                return results
            finally:
                # Rebind (simulate plug in)
                run_command(f"echo -n '{device_name}' > {bind_file}", shell=True)

        logger.info("Running test commands...")
        for command in test_commands:
            logger.info("  Executing: dut-control %s", command)
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
        logger.info("--- Job %s Completed ---", job_id)

    except subprocess.CalledProcessError as e:
        results["error"] = (
            f"Command failed: {e}\nArgs: {e.cmd}\n"
            f"Stdout: {e.stdout}\nStderr: {e.stderr}"
        )
        logger.error("Error during job %s: %s", job_id, e)
    except Exception as e:
        results["error"] = f"An unexpected error occurred: {e}"
        logger.error("Unexpected error during job %s: %s", job_id, e)
    finally:
        if not dry_run:
            logger.info("Stopping servod...")
            # stop-servod uses the base name
            run_command(["stop-servod", "--container_name", base_name], check=False)
            time.sleep(2)  # Give logs time to flush

            logger.info("Collecting logs...")
            container_log_dir = log_dir_for_job  # Corrected path
            if os.path.exists(container_log_dir):
                debug_files = glob.glob(os.path.join(container_log_dir, "*.DEBUG"))
                if debug_files:
                    latest_log = max(debug_files, key=os.path.getctime)
                    logger.info("Log file found: %s", latest_log)
                    try:
                        with open(
                            latest_log, "r", encoding="utf-8", errors="replace"
                        ) as f:
                            f.seek(0, os.SEEK_END)
                            file_size = f.tell()
                            seek_to = max(0, file_size - 1024 * 1024)  # Read last 1MB
                            f.seek(seek_to)
                            log_content = f.read()
                            results["log"] = (
                                f"--- servod log ({os.path.basename(latest_log)}) ---\n"
                                f"{log_content}"
                            )
                    except Exception as log_e:
                        logger.error("Error reading log file: %s", log_e)
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

            logger.info("Cleaning up local log directory.")
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
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not execute Docker commands, just simulate.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose DEBUG logging.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info(
        "Local agent started. Polling %s every %d seconds.",
        args.orchestrator_url,
        POLL_INTERVAL,
    )
    if args.dry_run:
        logger.info("Running in DRY RUN mode.")

    while True:
        job = poll_for_job(args.orchestrator_url)
        if job:
            job_id = job["job_id"]
            logger.info("Found job: %s", job_id)
            test_results = execute_test(job, dry_run=args.dry_run)
            submit_data = {
                "job_id": job_id,
                "exit_code": test_results.get("exit_code"),
                "error": test_results.get("error"),
                "log": test_results.get("log"),
                "executed_start_cmd": test_results.get("executed_start_cmd"),
                "test_outputs": test_results.get("test_outputs"),
            }
            logger.info("Submitting results for job %s", job_id)
            submit_results(args.orchestrator_url, job_id, submit_data)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
