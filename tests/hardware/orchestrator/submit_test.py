#!/usr/bin/env python3
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Client CLI wrapper for submitting hardware tests to the Test Orchestrator.
"""

import argparse
import sys
import time


try:
    import requests
except ImportError:
    print(
        "Error: 'requests' module not found.\n"
        "Please install it with: pip install requests"
    )
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Submit a test to the Servod Test Orchestrator"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:5000",
        help="Orchestrator URL (default: http://localhost:5000)",
    )
    parser.add_argument(
        "--image",
        required=True,
        help="Docker image to test (e.g., servod:dev or servod:release)",
    )
    parser.add_argument(
        "--channel",
        default="local",
        help="Servod channel flag for start-servod (default: local)",
    )
    parser.add_argument("--board", required=True, help="DUT Board (e.g., brya)")
    parser.add_argument("--model", default="", help="DUT Model (e.g., banshee)")
    parser.add_argument("--serial", default="", help="Servo Serial Number")
    parser.add_argument(
        "--cmds",
        nargs="+",
        required=True,
        help="List of dut-control commands to execute",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Print the full servod log output"
    )

    args = parser.parse_args()

    # Construct start-servod args exactly how the shell would expect them
    start_servod_args = ["-c", args.channel, "-b", args.board]
    if args.model:
        start_servod_args.extend(["-m", args.model])

    servod_args = []
    if args.serial:
        servod_args.extend(["-s", args.serial])

    payload = {
        "image_name": args.image,
        "start_servod_args": start_servod_args,
        "servod_args": servod_args,
        "test_commands": args.cmds,
    }

    print(f"Submitting job to {args.url}...")
    try:
        resp = requests.post(f"{args.url}/api/jobs", json=payload, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"Failed to submit job: {e}")
        sys.exit(1)

    job_id = resp.json().get("job_id")
    print(f"Job ID: {job_id}")

    print("Waiting for results (this may take a minute)", end="", flush=True)
    while True:
        time.sleep(5)
        print(".", end="", flush=True)
        try:
            res = requests.get(f"{args.url}/api/results/{job_id}", timeout=10)
            if res.status_code == 200:
                data = res.json()
                if "error" in data and data["error"] == "Results not yet available":
                    continue

                print(" Done!\n")

                # Parse results
                print("=== TEST RESULTS ===")
                print(f"Target Image:     {args.image}")
                print(f"Command Executed: {data.get('executed_start_cmd')}")
                print(f"Exit Code:        {data.get('exit_code')}")

                if data.get("error"):
                    print(f"Agent Error:      {data.get('error')}")

                print("-" * 20)
                outputs = data.get("test_outputs", {})
                for cmd in args.cmds:
                    if cmd not in outputs:
                        print(f"[SKIP] {cmd}: Did not run")
                        continue

                    out = outputs[cmd]
                    exit_c = out.get("exit_code")
                    stdout = out.get("stdout", "").strip()
                    stderr = out.get("stderr", "").strip()

                    status = "[PASS]" if exit_c == 0 else "[FAIL]"
                    print(f"{status} {cmd}: {stdout}")
                    if stderr:
                        print(f"       stderr: {stderr}")

                if args.verbose and data.get("log"):
                    print("\n=== SERVOD LOG ===")
                    print(data["log"])
                break
        except Exception as e:
            print(f"\nError polling results: {e}")
            break


if __name__ == "__main__":
    main()
