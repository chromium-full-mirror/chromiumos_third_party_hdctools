#!/usr/bin/env python3
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# Servod Test Plan: Firmware Read Stress

import os
import subprocess
import sys
import time


ITERATIONS = 3000
SLEEP_SEC = 5
PORT = 9999


def get_candidate_cmds():
    """Extract read commands from the simple read plan."""
    md_path = "/hdctools/servo/test_plans/firmware_simple_read_plan.md"
    cmds = []
    if not os.path.exists(md_path):
        print(f"WARN: Cannot find {md_path} to extract commands.")
        print("Falling back to basic reads.")
        return ["ec_board", "ec_chip", "servo_type", "servo_class"]

    with open(md_path, "r", encoding="utf-8") as f:
        in_block = False
        for line in f:
            line = line.strip()
            if line.startswith("```bash"):
                in_block = True
                continue
            if line.startswith("```"):
                in_block = False
                continue
            if in_block and line and not line.startswith("dut-control"):
                cmd = line.replace("\\", "").strip()
                if cmd:
                    cmds.append(cmd)
    return cmds


def discover_valid_cmds(candidates):
    """Run a fast pass to identify valid read commands for this hardware."""
    valid = []
    for cmd in candidates:
        res = subprocess.run(
            ["dut-control", "-p", str(PORT), cmd],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0:
            valid.append(cmd)
    return valid


def main():
    print(f"--- Starting Firmware Read Stress Test ({ITERATIONS} iterations) ---")
    candidates = get_candidate_cmds()
    print(f"Found {len(candidates)} candidate commands in simple read plan.")

    valid_cmds = discover_valid_cmds(candidates)
    print(f"Discovered {len(valid_cmds)} completely valid read commands.")
    print(f"Commands: {valid_cmds}")

    if not valid_cmds:
        print("FATAL: No valid commands found to stress test!")
        sys.exit(1)

    for i in range(ITERATIONS):
        print(f"--- Iteration {i+1}/{ITERATIONS} ---")

        cmd = ["dut-control", "-p", str(PORT)] + valid_cmds
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)

        # We only fail the stress test if something fundamentally crashes
        # (e.g. gRPC or servod death). Random non-zero exit codes might happen
        # if a control becomes temporarily unavailable.
        if res.returncode != 0:
            if "Fault 1" in res.stderr or "Exception calling" in res.stderr:
                print(f"CRITICAL CRASH at iteration {i+1}!")
                print(f"Exit code: {res.returncode}")
                print(f"Stderr:\n{res.stderr}")
                sys.exit(1)
            else:
                err = res.stderr.strip()
                print(f"Warning: Non-zero exit code at iteration {i+1}.")
                print(f"Stderr: {err}")

        if i < ITERATIONS - 1:
            time.sleep(SLEEP_SEC)

    print(f"Successfully completed all {ITERATIONS} iterations without crashing!")
    sys.exit(0)


if __name__ == "__main__":
    main()
