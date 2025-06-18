# Copyright 2025 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
from concurrent.futures import as_completed
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime
import io
import logging
import os
import shlex
import subprocess
import threading
import time


# --- Configuration ---
SSH_PORT = 22
CONNECT_TIMEOUT = 30  # Seconds for SSH connection attempt
COMMAND_TIMEOUT = 30  # Seconds for individual SSH command execution
SSH_USERNAME = "root"  # Hardcoded SSH username
NUM_WORKERS = 10  # Number of parallel workers for device processing

_BASE_LOG_FILE_NAME_FOR_UNIQUENESS = "keyboard_rollout.log"
_timestamp_for_log = datetime.now().strftime("%Y%m%d_%H%M%S")
_base_name_part_for_log, _extension_part_for_log = os.path.splitext(
    _BASE_LOG_FILE_NAME_FOR_UNIQUENESS
)
LOG_FILE_NAME = (
    f"{_base_name_part_for_log}_{_timestamp_for_log}{_extension_part_for_log}"
)

COMMON_SSH_OPTIONS = [
    "-o",
    f"ConnectTimeout={CONNECT_TIMEOUT}",
    "-o",
    "StrictHostKeyChecking=no",
    "-o",
    "UserKnownHostsFile=/dev/null",
    "-o",
    "LogLevel=ERROR",
]

file_log_lock = threading.Lock()


def setup_console_logging():
    """Configures the CONSOLE logging for the script."""
    logger = logging.getLogger("RolloutScriptConsole")
    logger.setLevel(logging.INFO)

    if logger.hasHandlers():
        logger.handlers.clear()

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s - %(threadName)s - %(levelname)s - %(message)s"
    )
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    logger.propagate = False
    return logger


console_logger = setup_console_logging()


def execute_ssh_command(
    hostname, command_str, logger, ssh_port=SSH_PORT, cmd_timeout=COMMAND_TIMEOUT
):
    """
    Executes a command on a remote server via system SSH using key-based authentication.
    Uses the provided logger instance.
    """
    ssh_command_list = [
        "ssh",
        *COMMON_SSH_OPTIONS,
        "-p",
        str(ssh_port),
        f"{SSH_USERNAME}@{hostname}",
        command_str,
    ]

    logger.info(
        f"    [*] Executing via SSH: {' '.join(shlex.quote(arg) for arg in ssh_command_list)}"
    )

    try:
        process = subprocess.run(
            ssh_command_list,
            capture_output=True,
            text=True,
            timeout=cmd_timeout + CONNECT_TIMEOUT,
            check=False,
        )
        stdout_str = process.stdout.strip()
        stderr_str = process.stderr.strip()
        exit_status = process.returncode

        logger.info(f"    [+] SSH command executed. Exit status: {exit_status}")
        if stdout_str:
            logger.info(
                f"    [+] Stdout: {stdout_str[:200]}{'...' if len(stdout_str) > 200 else ''}"
            )
        if stderr_str:
            logger.warning(f"    [-] Stderr: {stderr_str}")

        return stdout_str, stderr_str, exit_status
    except subprocess.TimeoutExpired:
        logger.error(
            f"    [-] SSH command timed out for {SSH_USERNAME}@{hostname} after {cmd_timeout + CONNECT_TIMEOUT}s."
        )
        return None, "Command timed out", -1
    except Exception as e:
        logger.error(f"    [-] Error executing SSH command on {hostname}: {e}")
        return None, str(e), -1


def transfer_file_scp(hostname, local_path, remote_path, logger, ssh_port=SSH_PORT):
    """
    Transfers a file to a remote server using system SCP with key-based auth.
    Uses the provided logger instance.
    """
    scp_command_list = [
        "scp",
        *COMMON_SSH_OPTIONS,
        "-P",
        str(ssh_port),
        local_path,
        f"{SSH_USERNAME}@{hostname}:{remote_path}",
    ]

    logger.info(
        f"    [*] Attempting to transfer via SCP: {' '.join(shlex.quote(arg) for arg in scp_command_list)}"
    )

    try:
        process = subprocess.run(
            scp_command_list,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT + CONNECT_TIMEOUT,
            check=False,
        )

        if process.returncode == 0:
            logger.info(
                f"    [+] File '{local_path}' transferred successfully to '{remote_path}'."
            )
            return True
        else:
            logger.error(
                f"    [-] SCP failed for {SSH_USERNAME}@{hostname}. Exit status: {process.returncode}"
            )
            if process.stdout.strip():
                logger.error(f"    [-] SCP Stdout: {process.stdout.strip()}")
            if process.stderr.strip():
                logger.error(f"    [-] SCP Stderr: {process.stderr.strip()}")
            return False
    except subprocess.TimeoutExpired:
        logger.error(f"    [-] SCP command timed out for {SSH_USERNAME}@{hostname}.")
        return False
    except Exception as e:
        logger.error(f"    [-] Error transferring file to {hostname} via SCP: {e}")
        return False


def check_servod_status(labstation_hostname, servod_port, target_servo_serial, logger):
    """
    Checks servod status and returns True if OK, False otherwise.
    Uses the provided logger instance.
    """
    logger.info(
        f"    [*] Checking servod status for serial '{target_servo_serial}' on port {servod_port}..."
    )
    cmd = f"dut-control -p {servod_port} serialname"
    stdout, stderr, retcode = execute_ssh_command(labstation_hostname, cmd, logger)

    if retcode == 0 and stdout and target_servo_serial in stdout.strip():
        logger.info(
            f"    [+] Servod OK: Port {servod_port} is associated with serial '{target_servo_serial}'."
        )
        return True
    elif retcode == 0 and stdout:
        logger.warning(
            f"    [-] Servod Warning: Port {servod_port} returned serial '{stdout.strip()}', expected '{target_servo_serial}'."
        )
        return False
    else:
        logger.warning(
            f"    [-] Failed to get serialname from port {servod_port}. Retcode: {retcode}, Stderr: {stderr}"
        )
        return False


def start_servod(labstation_hostname, servod_port, logger):
    """
    Attempts to start servod.
    Uses the provided logger instance.
    """
    logger.info(f"    [*] Attempting to start servod on port {servod_port}...")
    cmd = f"start servod PORT={servod_port}"
    stdout, stderr, retcode = execute_ssh_command(labstation_hostname, cmd, logger)
    if retcode == 0:
        logger.info(
            f"    [+] 'start servod PORT={servod_port}' command executed. Exit status: {retcode}."
        )
        return True
    else:
        logger.error(
            f"    [-] Failed to execute 'start servod PORT={servod_port}'. Retcode: {retcode}, Stderr: {stderr}"
        )
        return False


def process_device(row_data, keyboard_hex_path):
    """
    Processes a single device entry from the CSV.
    Returns a dictionary with failure details if processing fails, else None.
    Logs for this DUT are buffered and written to file at the end.
    """
    dut_hostname = row_data.get("dut")
    target_servo_serial = row_data.get("servo_serial")
    labstation_hostname = row_data.get("labstation")
    servod_port_str = row_data.get("servo_port")

    dut_logger_name = f"DUT.{dut_hostname or 'UnknownDUT'}_{target_servo_serial or 'UnknownSerial'}_{threading.get_ident()}"
    dut_logger = logging.getLogger(dut_logger_name)
    dut_logger.setLevel(logging.INFO)

    if dut_logger.hasHandlers():
        dut_logger.handlers.clear()

    log_capture_buffer = io.StringIO()
    buffer_handler = logging.StreamHandler(log_capture_buffer)
    formatter = logging.Formatter(
        "%(asctime)s - %(threadName)s - %(levelname)s - %(message)s"
    )
    buffer_handler.setFormatter(formatter)
    dut_logger.addHandler(buffer_handler)
    dut_logger.propagate = False

    try:
        dut_logger.info(
            f"--- Processing DUT: {dut_hostname} (Lab: {labstation_hostname}, Servo Serial: {target_servo_serial}, Servod Port: {servod_port_str}) ---"
        )

        if not all(
            [dut_hostname, target_servo_serial, labstation_hostname, servod_port_str]
        ):
            missing_fields = [
                field
                for field, value in {
                    "dut": dut_hostname,
                    "servo_serial": target_servo_serial,
                    "labstation": labstation_hostname,
                    "servo_port": servod_port_str,
                }.items()
                if not value
            ]
            reason = f"Missing critical CSV data: {', '.join(missing_fields)}."
            dut_logger.error(f"    [!] Skipping row due to {reason} Row: {row_data}")
            return {
                "dut": dut_hostname or "N/A",
                "labstation": labstation_hostname or "N/A",
                "servo_serial": target_servo_serial or "N/A",
                "stage": "CSV Parsing",
                "reason": reason,
            }

        if servod_port_str and servod_port_str.isdigit():
            servod_port = int(servod_port_str)
        else:
            reason = (
                f"Invalid 'servod_port' value '{servod_port_str}' for {dut_hostname}."
            )
            dut_logger.warning(f"    [!] {reason}")
            return {
                "dut": dut_hostname or "N/A",
                "labstation": labstation_hostname or "N/A",
                "servo_serial": target_servo_serial or "N/A",
                "stage": "CSV Parsing",
                "reason": reason,
            }

        dut_logger.info(f"[LABSTATION {labstation_hostname}] Initial servod check...")
        servod_ok = check_servod_status(
            labstation_hostname, servod_port, target_servo_serial, dut_logger
        )

        if not servod_ok:
            dut_logger.info(
                f"[LABSTATION {labstation_hostname}] Attempting to start servod as it was not found or incorrect."
            )
            if start_servod(labstation_hostname, servod_port, dut_logger):
                dut_logger.info(
                    f"[LABSTATION {labstation_hostname}] Waiting 8s then re-checking servod status..."
                )
                time.sleep(8)
                servod_ok = check_servod_status(
                    labstation_hostname, servod_port, target_servo_serial, dut_logger
                )
            else:
                servod_ok = False

        if not servod_ok:
            reason = f"Failed to verify/start servod for serial '{target_servo_serial}' on port {servod_port}."
            dut_logger.error(
                f"    [-] {reason} Skipping further processing for this device."
            )
            return {
                "dut": dut_hostname,
                "labstation": labstation_hostname,
                "servo_serial": target_servo_serial,
                "stage": "Servod Setup",
                "reason": reason,
            }

        dut_logger.info(
            f"[LABSTATION {labstation_hostname}] Running pre-DUT-flash dut-control commands..."
        )
        dut_control_command_pre = (
            f"dut-control -p {servod_port} at_hwb:on atmega_rst:on atmega_rst:off"
        )
        _, _, retcode = execute_ssh_command(
            labstation_hostname, dut_control_command_pre, dut_logger
        )
        if retcode != 0:
            reason = f"Command '{dut_control_command_pre}' failed on labstation. Retcode: {retcode}."
            dut_logger.error(f"    [-] {reason} Skipping further processing.")
            return {
                "dut": dut_hostname,
                "labstation": labstation_hostname,
                "servo_serial": target_servo_serial,
                "stage": "Labstation Pre-Flash Commands",
                "reason": reason,
            }
        dut_logger.info(f"    [+] Labstation pre-DUT-flash commands successful.")

        dut_logger.info(f"[DUT {dut_hostname}] Transferring '{keyboard_hex_path}'...")
        remote_hex_path = f"/tmp/{os.path.basename(keyboard_hex_path)}"
        if not transfer_file_scp(
            dut_hostname, keyboard_hex_path, remote_hex_path, dut_logger
        ):
            reason = f"Failed to SCP '{keyboard_hex_path}' to DUT {dut_hostname}:{remote_hex_path}."
            dut_logger.error(f"    [-] {reason} Skipping further DUT operations.")
            return {
                "dut": dut_hostname,
                "labstation": labstation_hostname,
                "servo_serial": target_servo_serial,
                "stage": "DUT SCP",
                "reason": reason,
            }

        dut_logger.info(f"[DUT {dut_hostname}] Verifying '{remote_hex_path}' on DUT...")
        stdout_ls, _, retcode_ls = execute_ssh_command(
            dut_hostname, f"ls {shlex.quote(remote_hex_path)}", dut_logger
        )
        if retcode_ls != 0 or not remote_hex_path in stdout_ls.splitlines():
            reason = f"File '{remote_hex_path}' not found on DUT after SCP. Retcode: {retcode_ls}."
            dut_logger.error(f"    [-] {reason} Skipping further DUT operations.")
            return {
                "dut": dut_hostname,
                "labstation": labstation_hostname,
                "servo_serial": target_servo_serial,
                "stage": "DUT SCP Verification",
                "reason": reason,
            }
        dut_logger.info(f"    [+] File '{remote_hex_path}' confirmed on DUT.")

        dut_logger.info(
            f"[DUT {dut_hostname}] Checking for DFU bootloader (03eb:2ff4)..."
        )
        dfu_bootloader_id = "03eb:2ff4"
        stdout_lsusb_dfu, _, retcode_lsusb_dfu = execute_ssh_command(
            dut_hostname, "lsusb -v", dut_logger
        )
        if retcode_lsusb_dfu != 0 or dfu_bootloader_id not in stdout_lsusb_dfu:
            reason = f"DFU bootloader '{dfu_bootloader_id}' not found on DUT {dut_hostname}. Retcode: {retcode_lsusb_dfu}."
            dut_logger.error(
                f"    [-] {reason} lsusb output (first 500 chars): {stdout_lsusb_dfu[:500] if stdout_lsusb_dfu else 'N/A'}"
            )
            return {
                "dut": dut_hostname,
                "labstation": labstation_hostname,
                "servo_serial": target_servo_serial,
                "stage": "DUT DFU Check",
                "reason": reason,
            }
        dut_logger.info(f"    [+] DFU bootloader '{dfu_bootloader_id}' found on DUT.")

        dut_logger.info(f"[DUT {dut_hostname}] Running dfu-programmer erase...")
        _, _, retcode_erase = execute_ssh_command(
            dut_hostname, "dfu-programmer atmega32u4 erase", dut_logger
        )
        if retcode_erase != 0:
            reason = f"'dfu-programmer atmega32u4 erase' failed on DUT {dut_hostname}. Retcode: {retcode_erase}."
            dut_logger.error(f"    [-] {reason} Skipping further DUT operations.")
            return {
                "dut": dut_hostname,
                "labstation": labstation_hostname,
                "servo_serial": target_servo_serial,
                "stage": "DUT DFU Erase",
                "reason": reason,
            }
        dut_logger.info(f"    [+] DFU erase successful.")

        dut_logger.info(
            f"[DUT {dut_hostname}] Running dfu-programmer flash '{remote_hex_path}'..."
        )
        cmd_flash_dfu = (
            f"dfu-programmer atmega32u4 flash {shlex.quote(remote_hex_path)}"
        )
        _, _, retcode_flash = execute_ssh_command(
            dut_hostname, cmd_flash_dfu, dut_logger
        )
        if retcode_flash != 0:
            reason = f"'{cmd_flash_dfu}' failed on DUT {dut_hostname}. Retcode: {retcode_flash}."
            dut_logger.error(f"    [-] {reason} Skipping further DUT operations.")
            return {
                "dut": dut_hostname,
                "labstation": labstation_hostname,
                "servo_serial": target_servo_serial,
                "stage": "DUT DFU Flash",
                "reason": reason,
            }
        dut_logger.info(f"    [+] DFU flash successful.")

        dut_logger.info(
            f"[LABSTATION {labstation_hostname}] Running post-DUT-flash dut-control commands..."
        )
        dut_control_command_post = (
            f"dut-control -p {servod_port} at_hwb:off atmega_rst:on atmega_rst:off"
        )
        _, _, retcode_post = execute_ssh_command(
            labstation_hostname, dut_control_command_post, dut_logger
        )
        if retcode_post != 0:
            reason = f"Command '{dut_control_command_post}' failed on labstation. Retcode: {retcode_post}."
            dut_logger.error(
                f"    [-] {reason} Marking as failed due to post command fail"
            )
            return {
                "dut": dut_hostname,
                "labstation": labstation_hostname,
                "servo_serial": target_servo_serial,
                "stage": "Labstation Post-Flash Commands",
                "reason": reason,
            }
        dut_logger.info(f"    [+] Labstation post-DUT-flash commands executed.")

        dut_logger.info(
            f"[DUT {dut_hostname}] Waiting 3s and Checking for LUFA Keyboard Demo Application (03eb:2042)..."
        )
        time.sleep(3)
        lufa_keyboard_id = "03eb:2042"
        stdout_lsusb_lufa, _, retcode_lsusb_lufa = execute_ssh_command(
            dut_hostname, "lsusb -v", dut_logger
        )
        if retcode_lsusb_lufa != 0 or lufa_keyboard_id not in stdout_lsusb_lufa:
            reason = f"LUFA Keyboard Demo App '{lufa_keyboard_id}' not found on DUT {dut_hostname} after flashing. Retcode: {retcode_lsusb_lufa}."
            dut_logger.error(f"    [-] {reason}")
            return {
                "dut": dut_hostname,
                "labstation": labstation_hostname,
                "servo_serial": target_servo_serial,
                "stage": "DUT LUFA Check",
                "reason": reason,
            }

        dut_logger.info(
            f"    [SUCCESS] DUT {dut_hostname} successfully processed and LUFA Keyboard Demo App found!"
        )
        return None
    finally:
        dut_log_content = log_capture_buffer.getvalue()
        log_capture_buffer.close()
        dut_logger.removeHandler(buffer_handler)
        with file_log_lock:
            with open(LOG_FILE_NAME, "a", encoding="utf-8") as f:
                f.write(
                    f"--- BEGIN LOG FOR DUT: {dut_hostname or 'UnknownDUT'} | Servo: {target_servo_serial or 'UnknownSerial'} ---\n"
                )
                f.write(dut_log_content)
                f.write(
                    f"--- END LOG FOR DUT: {dut_hostname or 'UnknownDUT'} | Servo: {target_servo_serial or 'UnknownSerial'} ---\n\n"
                )


def main():
    parser = argparse.ArgumentParser(
        description="Automate Labstation and DUT interactions via SSH using system ssh/scp.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=f"""
Example CSV format:
  dut,servo_serial,labstation,servod_port
  dut_hostname1,serial123,labstation_host1,9999
  dut_hostname2,serial456,labstation_host2,9998

Notes:
- This script uses system 'ssh' and 'scp'. Ensure they are configured for passwordless
  access (e.g., using SSH keys and ssh-agent) for the user '{SSH_USERNAME}'.
- SSH connection options {COMMON_SSH_OPTIONS} are used.
  These suppress host key prompts, which is convenient for automation but has security
  implications. Use with caution and in controlled environments.
- Number of worker threads: {NUM_WORKERS}
- Logs are primarily on console for real-time. Detailed per-DUT logs are in: {LOG_FILE_NAME}
  (each DUT's log is written contiguously upon completion).
- CSV reports for successful and failed DUTs will also be generated.
""",
    )
    parser.add_argument(
        "csv_file", help="Path to the CSV file containing device information."
    )
    parser.add_argument(
        "keyboard_hex", help="Path to the Keyboard.hex file to be flashed."
    )

    args = parser.parse_args()

    initial_log_messages = []
    initial_log_messages.append(
        f"Script started at {time.asctime(time.localtime(time.time()))}"
    )
    initial_log_messages.append(f"Actual log file will be: {LOG_FILE_NAME}")

    if not os.path.exists(args.csv_file):
        msg = f"Error: CSV file '{args.csv_file}' not found."
        console_logger.error(msg)
        initial_log_messages.append(msg)
        with file_log_lock:
            with open(LOG_FILE_NAME, "a", encoding="utf-8") as f:
                for log_msg in initial_log_messages:
                    f.write(log_msg + "\n")
                f.write("\n")
        return

    if not os.path.exists(args.keyboard_hex):
        msg1 = f"Error: Keyboard.hex file '{args.keyboard_hex}' not found."
        msg2 = "Please ensure this file exists and is the correct firmware."
        console_logger.error(msg1)
        console_logger.error(msg2)
        initial_log_messages.append(msg1)
        initial_log_messages.append(msg2)
        with file_log_lock:
            with open(LOG_FILE_NAME, "a", encoding="utf-8") as f:
                for log_msg in initial_log_messages:
                    f.write(log_msg + "\n")
                f.write("\n")
        return

    initial_log_messages.append("--- SSH Configuration ---")
    initial_log_messages.append(
        f"[*] Using SSH username: '{SSH_USERNAME}' for all connections via system ssh/scp."
    )
    initial_log_messages.append(
        f"[*] Assuming passwordless SSH (key-based authentication) is configured for the system."
    )
    initial_log_messages.append(
        f"[*] Common SSH options: {' '.join(COMMON_SSH_OPTIONS)}"
    )
    initial_log_messages.append(f"[*] Number of worker threads: {NUM_WORKERS}")
    initial_log_messages.append("-------------------------\n")

    for msg in initial_log_messages:
        console_logger.info(msg.replace("[*]", "(INFO)").replace("---", "###"))

    with file_log_lock:
        with open(LOG_FILE_NAME, "a", encoding="utf-8") as f:
            for log_msg in initial_log_messages:
                f.write(log_msg + "\n")
            f.write("\n")

    failed_devices_reports = []
    processed_device_count = 0
    device_rows = []
    csv_fieldnames = []  # To store headers from input CSV
    successful_dut_original_rows = []  # To store original row data for successful DUTs
    failed_dut_original_rows = []  # To store original row data for failed DUTs

    try:
        with open(args.csv_file, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            if not reader.fieldnames:
                msg = f"Error: CSV file '{args.csv_file}' is empty or has no header."
                console_logger.error(msg)
                with file_log_lock:
                    with open(LOG_FILE_NAME, "a", encoding="utf-8") as f:
                        f.write(msg + "\n\n")
                return

            csv_fieldnames = list(reader.fieldnames)  # Store headers
            console_logger.info(f"Detected CSV columns: {csv_fieldnames}")

            required_cols = ["dut", "servo_serial", "labstation", "servo_port"]
            missing_cols = [col for col in required_cols if col not in csv_fieldnames]
            if missing_cols:
                msg = f"Error: CSV file '{args.csv_file}' is missing required columns: {', '.join(missing_cols)}"
                console_logger.error(msg)
                with file_log_lock:
                    with open(LOG_FILE_NAME, "a", encoding="utf-8") as f:
                        f.write(msg + "\n\n")
                return

            device_rows = list(reader)

        if not device_rows:
            msg = "No devices found in CSV file to process."
            console_logger.info(msg)
            with file_log_lock:
                with open(LOG_FILE_NAME, "a", encoding="utf-8") as f:
                    f.write(msg + "\n\n")
            return

        msg = f"Starting processing for {len(device_rows)} devices with {NUM_WORKERS} workers..."
        console_logger.info(msg)
        with file_log_lock:
            with open(LOG_FILE_NAME, "a", encoding="utf-8") as f:
                f.write(msg + "\n\n")

        with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
            futures = {
                executor.submit(process_device, row, args.keyboard_hex): row
                for row in device_rows
            }

            for future in as_completed(futures):
                row_data = futures[future]  # Original input row for this DUT
                dut = row_data.get("dut", "Unknown DUT")
                try:
                    result = future.result()
                    if result:
                        failed_devices_reports.append(result)
                        failed_dut_original_rows.append(
                            row_data
                        )  # Add original data to failed list
                    else:
                        successful_dut_original_rows.append(
                            row_data
                        )  # Add original data to success list
                    processed_device_count += 1
                    console_logger.info(
                        f"Completed processing for DUT: {dut}. ({processed_device_count}/{len(device_rows)})"
                    )
                except Exception as e:
                    console_logger.error(
                        f"An unexpected error occurred processing device {dut}: {e}"
                    )
                    failed_devices_reports.append(
                        {
                            "dut": dut,
                            "labstation": row_data.get("labstation", "N/A"),
                            "servo_serial": row_data.get("servo_serial", "N/A"),
                            "stage": "Execution Framework",
                            "reason": f"Unhandled exception in thread: {e}",
                        }
                    )
                    failed_dut_original_rows.append(
                        row_data
                    )  # Also count as failed for CSV report
                    processed_device_count += 1
                    console_logger.info(
                        f"Completed processing (with unhandled error in thread) for DUT: {dut}. ({processed_device_count}/{len(device_rows)})"
                    )

    except FileNotFoundError:
        msg = f"Error: CSV file '{args.csv_file}' not found during processing."
        console_logger.error(msg)
        with file_log_lock:
            with open(LOG_FILE_NAME, "a", encoding="utf-8") as f:
                f.write(msg + "\n\n")
    except Exception as e:
        console_logger.exception(
            "An unexpected error occurred during CSV processing setup:"
        )
        with file_log_lock:
            with open(LOG_FILE_NAME, "a", encoding="utf-8") as f:
                f.write("An unexpected error occurred during CSV processing setup:\n")
                f.write(str(e) + "\n\n")

    # --- Generate CSV reports ---
    csv_report_log_messages = []
    if csv_fieldnames:  # Proceed only if we have headers from the input CSV
        # Successful DUTs CSV
        successful_csv_filename = f"successful_duts_{_timestamp_for_log}.csv"
        msg_success_csv = (
            f"Generating CSV report for successful DUTs: {successful_csv_filename}"
        )
        console_logger.info(msg_success_csv)
        csv_report_log_messages.append(msg_success_csv)
        try:
            with open(
                successful_csv_filename, "w", newline="", encoding="utf-8"
            ) as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=csv_fieldnames)
                writer.writeheader()
                writer.writerows(successful_dut_original_rows)
            if not successful_dut_original_rows:
                csv_report_log_messages.append(
                    f"No successful DUTs to report in {successful_csv_filename}."
                )
        except IOError as e:
            err_msg = (
                f"Error writing successful DUTs CSV {successful_csv_filename}: {e}"
            )
            console_logger.error(err_msg)
            csv_report_log_messages.append(err_msg)

        # Failed DUTs CSV
        failed_csv_filename = f"failed_duts_{_timestamp_for_log}.csv"
        msg_failed_csv = f"Generating CSV report for failed DUTs: {failed_csv_filename}"
        console_logger.info(msg_failed_csv)
        csv_report_log_messages.append(msg_failed_csv)
        try:
            with open(
                failed_csv_filename, "w", newline="", encoding="utf-8"
            ) as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=csv_fieldnames)
                writer.writeheader()
                writer.writerows(failed_dut_original_rows)
            if not failed_dut_original_rows:
                csv_report_log_messages.append(
                    f"No failed DUTs to report in {failed_csv_filename} (or all succeeded)."
                )
        except IOError as e:
            err_msg = f"Error writing failed DUTs CSV {failed_csv_filename}: {e}"
            console_logger.error(err_msg)
            csv_report_log_messages.append(err_msg)

    else:
        no_header_msg = "Skipping CSV report generation as no CSV headers were found (e.g., empty or invalid input CSV)."
        console_logger.info(no_header_msg)
        csv_report_log_messages.append(no_header_msg)

    if csv_report_log_messages:  # Add CSV report messages to the main log file
        with file_log_lock:
            with open(LOG_FILE_NAME, "a", encoding="utf-8") as f:
                f.write("\n--- CSV Report Generation Log ---\n")
                for msg in csv_report_log_messages:
                    f.write(msg + "\n")
                f.write("---------------------------------\n")

    # --- Summary of Operations (existing part) ---
    summary_lines = []
    if failed_devices_reports:
        summary_lines.append(
            "\n\n--- Summary of Failed Devices/Operations (Detailed Reasons) ---"
        )
        for item in failed_devices_reports:
            summary_lines.append(
                f"  DUT: {item['dut']}, Labstation: {item['labstation']}, Servo Serial: {item.get('servo_serial', 'N/A')}"
            )
            summary_lines.append(f"    Stage: {item['stage']}")
            summary_lines.append(f"    Reason: {item['reason']}")
            summary_lines.append("-" * 20)
    else:
        if processed_device_count > 0 and device_rows:
            summary_lines.append(
                "\n\n--- All specified devices processed. See individual DUT logs and CSV reports. ---"
            )
        elif not device_rows:  # Already handled, but for completeness of summary logic
            pass
        else:  # Processed 0, but there were rows. Likely indicates prior setup error.
            summary_lines.append(
                "\n\n--- No devices were processed. Check logs for errors. ---"
            )

    summary_lines.append(
        f"\nScript finished at {time.asctime(time.localtime(time.time()))}\n"
    )

    for line in summary_lines:
        console_logger.info(line)

    with file_log_lock:
        with open(LOG_FILE_NAME, "a", encoding="utf-8") as f:
            for line in summary_lines:
                f.write(line + "\n")


if __name__ == "__main__":
    main()
