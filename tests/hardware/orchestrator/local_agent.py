#!/usr/bin/env python3
# pylint: disable=no-name-in-module
# pylint: disable=import-error
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# pylint: disable=import-error,line-too-long,import-outside-toplevel
import argparse
import glob
import json
import logging
import os
import shutil
import subprocess
import tempfile
import threading
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


def check_dependencies():
    """Verify that required binaries are available."""
    required_binaries = ["docker"]
    missing = []

    for binary in required_binaries:
        if shutil.which(binary) is None:
            missing.append(binary)

    # Check for start-servod/stop-servod either in PATH or in ./scripts
    if shutil.which("start-servod") is None and not os.path.exists(
        "./scripts/start-servod"
    ):
        missing.append(
            "start-servod (not in PATH and ./scripts/start-servod not found)"
        )
    if shutil.which("stop-servod") is None and not os.path.exists(
        "./scripts/stop-servod"
    ):
        missing.append("stop-servod (not in PATH and ./scripts/stop-servod not found)")

    if missing:
        raise LocalAgentError(f"Missing required dependencies: {', '.join(missing)}")


def get_gsc_type(container_name):
    """Detects if the GSC is cr50 or ti50."""
    try:
        res = subprocess.run(
            ["docker", "exec", container_name, "dut-control", "devices"],
            capture_output=True,
            text=True,
            check=True,
        )
        # Output is like: devices:[{...}, {...}]
        # Need to strip 'devices:' prefix
        raw_json = res.stdout.strip().replace("devices:", "", 1)
        devices = json.loads(raw_json)
        for dev in devices:
            if "ccd_cr50" in dev.get("prefix", []):
                return "ccd_cr50"
            if "ccd_ti50" in dev.get("prefix", []):
                return "ccd_ti50"
    except Exception as e:
        logger.warning("Failed to auto-detect GSC type: %s", e)
    return None


def execute_test(job, dry_run=False):
    import io

    log_stream = io.StringIO()
    capture_handler = logging.StreamHandler(log_stream)
    capture_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logging.getLogger().addHandler(capture_handler)

    try:
        res = _execute_test_internal(job, dry_run)
        res["log"] = log_stream.getvalue() + "\n" + res.get("log", "")
        return res
    finally:
        logging.getLogger().removeHandler(capture_handler)


def _execute_test_internal(job, dry_run=False):
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
            (
                "./scripts/start-servod"
                if os.path.exists("./scripts/start-servod")
                else "start-servod"
            ),
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

            stop_cmd = (
                "./scripts/stop-servod"
                if os.path.exists("./scripts/stop-servod")
                else "stop-servod"
            )
            run_command([stop_cmd, "--container_name", base_name])
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

        # Detect GSC type for watchdog mapping
        gsc_type = get_gsc_type(container_name)
        if gsc_type:
            logger.info("Detected GSC type: %s", gsc_type)

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
            original_command = command

            # Dynamic mapping for ccd_gsc / ccd_cr50 / ccd_ti50 aliases
            if gsc_type:
                new_command = command
                # If command targets a watchdog and has _nt, explicitly strip the _nt when resolving to physical GSC.
                for base in ["ccd_gsc", "ccd_cr50", "ccd_ti50"]:
                    if base in new_command and any(
                        x in new_command
                        for x in ["watchdog_add", "watchdog_remove", "gsc_uart_cmd"]
                    ):
                        # First handle the _nt specific case
                        if base + "_nt" in new_command and any(
                            w in new_command
                            for w in ["watchdog_add", "watchdog_remove"]
                        ):
                            new_command = new_command.replace(base + "_nt", gsc_type)
                        else:
                            new_command = new_command.replace(base, gsc_type)

                # CRITICAL BUG FIX: If we replaced ccd_gsc with ccd_cr50 previously,
                # but DIDNT strip the _nt because it wasn't matched properly, it became ccd_cr50_nt!
                # Let's catch that explicitly.
                if (
                    any(x in new_command for x in ["watchdog_add", "watchdog_remove"])
                    and "_nt" in new_command
                ):
                    new_command = new_command.replace("_nt", "")

                if new_command != command:
                    logger.info("  Mapped ccd_gsc -> %s: %s", gsc_type, new_command)
                command = new_command

            logger.info("  Executing: dut-control %s", command)

            try:
                test_cmd = [
                    "docker",
                    "exec",
                    container_name,
                    "dut-control",
                    command,
                ]
                test_result = run_command(test_cmd)
                results["test_outputs"][original_command] = {
                    "stdout": test_result.stdout,
                    "stderr": test_result.stderr,
                    "exit_code": test_result.returncode,
                }
                time.sleep(0.5)  # 0.5 second gap between commands
            except subprocess.CalledProcessError as e:
                # If it failed and we didn't already try mapping, try mapping now as a fallback
                if not gsc_type and any(
                    b in command for b in ["ccd_gsc", "ccd_cr50", "ccd_ti50"]
                ):
                    # Try to detect now
                    detected = get_gsc_type(container_name)
                    if detected:
                        gsc_type = detected
                        new_command = command
                        for base in ["ccd_gsc", "ccd_cr50", "ccd_ti50"]:
                            if base in new_command and any(
                                x in new_command
                                for x in [
                                    "watchdog_add",
                                    "watchdog_remove",
                                    "gsc_uart_cmd",
                                ]
                            ):
                                if base + "_nt" in new_command and any(
                                    w in new_command
                                    for w in ["watchdog_add", "watchdog_remove"]
                                ):
                                    new_command = new_command.replace(
                                        base + "_nt", gsc_type
                                    )
                                else:
                                    new_command = new_command.replace(base, gsc_type)

                        if (
                            any(
                                x in new_command
                                for x in ["watchdog_add", "watchdog_remove"]
                            )
                            and "_nt" in new_command
                        ):
                            new_command = new_command.replace("_nt", "")

                        if new_command != command:
                            command = new_command
                            logger.info("  Retrying with detected GSC: %s", command)

                            retry_test_cmd = [
                                "docker",
                                "exec",
                                container_name,
                                "dut-control",
                                command,
                            ]
                            test_result = run_command(retry_test_cmd)
                            results["test_outputs"][original_command] = {
                                "stdout": test_result.stdout,
                                "stderr": test_result.stderr,
                                "exit_code": test_result.returncode,
                            }
                            time.sleep(0.5)  # 0.5 second gap between commands
                            continue

                # If we get here, it's a real failure
                results["test_outputs"][original_command] = {
                    "stdout": e.stdout,
                    "stderr": e.stderr,
                    "exit_code": e.returncode,
                }
                raise

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
            stop_cmd = (
                "./scripts/stop-servod"
                if os.path.exists("./scripts/stop-servod")
                else "stop-servod"
            )
            run_command([stop_cmd, "--container_name", base_name], check=False)
            time.sleep(2)  # Give logs time to flush

            logger.info("Collecting logs...")
            container_log_dir = log_dir_for_job  # Corrected path
            if os.path.exists(container_log_dir):
                debug_files = glob.glob(os.path.join(container_log_dir, "*.DEBUG"))
                if debug_files:
                    combined_logs = []
                    for debug_file in sorted(debug_files):
                        filename = os.path.basename(debug_file)
                        logger.info("Log file found: %s", filename)
                        combined_logs.append(f"--- {filename} ---")
                        try:
                            with open(
                                debug_file, "r", encoding="utf-8", errors="replace"
                            ) as f:
                                f.seek(0, os.SEEK_END)
                                file_size = f.tell()
                                # Read last 1MB of each log to keep context manageable
                                seek_to = max(0, file_size - 1024 * 1024)
                                f.seek(seek_to)
                                combined_logs.append(f.read())
                        except Exception as log_e:
                            logger.error(
                                "Error reading log file %s: %s", filename, log_e
                            )
                            combined_logs.append(f"Error reading log: {log_e}")

                    results["log"] = "\n\n".join(combined_logs)
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
    if "CLOUDSDK_CONTEXT_AWARE_CERTIFICATE_CONFIG_FILE_PATH" in os.environ:
        del os.environ["CLOUDSDK_CONTEXT_AWARE_CERTIFICATE_CONFIG_FILE_PATH"]

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

    try:
        check_dependencies()
    except LocalAgentError as e:
        logger.critical("Dependency check failed: %s", e)
        return

    def worker():
        while True:
            try:
                job = poll_for_job(args.orchestrator_url)
                if job:
                    job_id = job["job_id"]
                    logger.info("[Worker] Found job: %s", job_id)
                    test_results = execute_test(job, dry_run=args.dry_run)
                    submit_data = {
                        "job_id": job_id,
                        "exit_code": test_results.get("exit_code"),
                        "error": test_results.get("error"),
                        "log": test_results.get("log"),
                        "executed_start_cmd": test_results.get("executed_start_cmd"),
                        "test_outputs": test_results.get("test_outputs"),
                    }
                    logger.info("[Worker] Submitting results for job %s", job_id)
                    submit_results(args.orchestrator_url, job_id, submit_data)
                else:
                    time.sleep(POLL_INTERVAL)
            except Exception as e:
                logger.error("[Worker] Unexpected error: %s", e)
                time.sleep(POLL_INTERVAL)

    # Start a worker per DUT. Since we have 3 DUTs, 3 workers is perfect.
    num_workers = 3
    logger.info("Starting %s worker threads...", num_workers)
    for _unused in range(num_workers):
        t = threading.Thread(target=worker, daemon=True)
        t.start()

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
