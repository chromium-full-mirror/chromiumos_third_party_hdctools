#!/usr/bin/env python3
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Robust test runner for submitting multi-DUT jobs to the Orchestrator
and polling until all results are synthesized.
"""

import argparse
import csv
import sys
import time


try:
    import requests
except ImportError:
    print("Error: 'requests' module not found. Run 'pip install requests'")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Run test plan across multiple DUTs")
    parser.add_argument("csv_file", help="CSV file with board,model,serial columns")
    parser.add_argument(
        "--image", required=True, help="Docker image to test (e.g., servod:release)"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:5002",
        help="Orchestrator URL (default: http://localhost:5002)",
    )
    parser.add_argument(
        "--cmds",
        nargs="+",
        default=["servo_fw_version", "ec_board"],
        help="List of dut-control commands to execute",
    )
    parser.add_argument(
        "--script",
        help="Path to python script to execute",
    )
    args = parser.parse_args()

    jobs = []

    print(f"Reading DUT matrix from {args.csv_file}...")
    try:
        with open(args.csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                board = row.get("board", "").strip()
                model = row.get("model", "").strip()
                serial = row.get("serial", "").strip()

                if not board:
                    continue

                start_args = ["-c", "local", "-b", board]
                if model:
                    start_args.extend(["-m", model])

                s_args = []
                if serial:
                    s_args.extend(["-s", serial])

                payload = {
                    "image_name": args.image,
                    "start_servod_args": start_args,
                    "servod_args": s_args,
                    "test_commands": args.cmds,
                }

                if args.script:
                    with open(args.script, "r", encoding="utf-8") as f:
                        payload["script_body"] = f.read()

                print(f"Submitting job for {board} ({model}) [Serial: {serial}]...")
                try:
                    resp = requests.post(
                        f"{args.url}/api/jobs", json=payload, timeout=10
                    )
                    resp.raise_for_status()
                    job_id = resp.json().get("job_id")
                    jobs.append((job_id, board, model, serial))
                    print(f"  -> Job ID: {job_id}")
                except Exception as e:
                    print(f"  -> Failed to submit to {args.url}: {e}")
                    print("  -> Is the Orchestrator running on the Cloudtop?")
                    sys.exit(1)
    except FileNotFoundError:
        print(f"Error: {args.csv_file} not found.")
        sys.exit(1)

    if not jobs:
        print("No valid jobs found in CSV.")
        sys.exit(1)

    print("\nWaiting for all jobs to complete (this may take several minutes)")
    results = {}

    while len(results) < len(jobs):
        for job_id, board, model, serial in jobs:
            if job_id in results:
                continue
            try:
                res = requests.get(f"{args.url}/api/results/{job_id}", timeout=5)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("error") != "Results not yet available":
                        results[job_id] = data
            except requests.exceptions.RequestException:
                pass

        if len(results) < len(jobs):
            time.sleep(5)
            print(".", end="", flush=True)

    print("\n\n" + "=" * 50)
    print("                 TEST RESULTS")
    print("=" * 50)

    for job_id, board, model, serial in jobs:
        data = results.get(job_id, {})
        exit_code = data.get("exit_code")
        status_msg = "PASS" if exit_code == 0 else "FAIL"

        print(f"\nTarget: {board} ({model}) [Serial: {serial}]")
        print(f"Status: {status_msg} (Exit Code: {exit_code})")

        if data.get("error"):
            print(f"Agent Error: {data.get('error')}")

        outputs = data.get("test_outputs", {})

        if args.script and "custom_script" in outputs:
            out = outputs["custom_script"]
            cmd_status = "PASS" if out.get("exit_code") == 0 else "FAIL"
            print(f"  [{cmd_status}] custom_script")
            stdout = out.get("stdout", "").strip()
            stderr = out.get("stderr", "").strip()
            if stdout:
                print(f"      stdout:\n{stdout}")
            if stderr:
                print(f"      stderr:\n{stderr}")

        if args.cmds:
            for cmd in args.cmds:
                if cmd not in outputs:
                    print(f"  [SKIP] {cmd}")
                    continue

                out = outputs[cmd]
                cmd_status = "PASS" if out.get("exit_code") == 0 else "FAIL"
                print(f"  [{cmd_status}] {cmd}")

                stdout = out.get("stdout", "").strip()
                stderr = out.get("stderr", "").strip()

                if stdout:
                    print(f"      stdout:\n{stdout}")
                if stderr:
                    print(f"      stderr:\n{stderr}")

        print("-" * 50)


if __name__ == "__main__":
    main()
