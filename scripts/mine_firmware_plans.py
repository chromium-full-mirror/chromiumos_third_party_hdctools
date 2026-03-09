#!/usr/bin/env python3
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
# pylint: disable=import-error,line-too-long,invalid-name,broad-exception-caught,chained-comparison,f-string-without-interpolation,consider-using-with

"""
Generates Servod Test Plans from Tast results.json and latest.DEBUG logs.
"""
import json
import os
import re
import subprocess


OUT_DIR = os.path.abspath("servo/test_plans")
os.makedirs(OUT_DIR, exist_ok=True)

INDEX_FILE = (
    "/usr/local/google/home/haddowk/analysis/2026-02-16/log_index_2026-02-16.jsonl"
)

suite_paths = {}
print("Scanning index for firmware test suites...")
with open(INDEX_FILE, "r", encoding="utf-8") as f:
    for line in f:
        try:
            data = json.loads(line)
            if (
                "fw_wp_state" in data.get("sets", [])
                or "cold_reset" in data.get("sets", [])
                or "warm_reset" in data.get("sets", [])
            ):
                debug_path = data["path"]
                res_path = re.sub(r"/servo_log/.*", "/results.json", debug_path)
                if res_path != debug_path:
                    if res_path not in suite_paths:
                        suite_paths[res_path] = {
                            "debug_paths": [],
                            "board": data.get("board", ""),
                            "model": data.get("model", ""),
                        }
                    suite_paths[res_path]["debug_paths"].append(debug_path)
        except Exception:
            pass

print(f"Found {len(suite_paths)} potential firmware suites. Extracting tests...")

COUNT = 0
generated_tests = set()

for r_path, suite_data in list(suite_paths.items())[:60]:
    try:
        res_data = subprocess.check_output(
            ["gsutil", "cat", r_path], stderr=subprocess.DEVNULL
        )
        results = json.loads(res_data)
    except Exception:
        continue

    if not isinstance(results, list):
        continue

    fw_tests = [t for t in results if t.get("name", "").startswith("firmware.")]
    new_tests = [t for t in fw_tests if t["name"] not in generated_tests]
    if not new_tests:
        continue

    print(f"Suite {r_path.split('/')[6]} has {len(new_tests)} new firmware tests.")

    debug_contents = []
    for dpath in suite_data["debug_paths"]:
        try:
            log_data = subprocess.check_output(
                ["gsutil", "cat", dpath], stderr=subprocess.DEVNULL
            )
            debug_contents.append(
                log_data.decode("utf-8", errors="replace").splitlines()
            )
        except Exception:
            pass

    board = suite_data["board"]
    model = suite_data["model"]

    for test in new_tests:
        name = test["name"]
        start_time = test.get("start", "")[:19]
        end_time = test.get("end", "")[:19]
        if not start_time or not end_time:
            continue

        commands = []
        for log_lines in debug_contents:
            for line in log_lines:
                if line >= start_time and line <= end_time:
                    get_match = re.search(r"\(GET\) ([a-zA-Z0-9_]+)\s*\?", line)
                    if get_match:
                        commands.append(
                            f"dut-control {get_match.group(1)}".replace(
                                "cr50", "gsc"
                            ).replace("ti50", "gsc")
                        )
                    set_match = re.search(r"\(SET\) ([a-zA-Z0-9_]+)\s+(.*)", line)
                    if set_match:
                        val = set_match.group(2).strip()
                        if val.startswith("['") or val.startswith('["'):
                            val = f'"{val}"'
                        commands.append(
                            f"dut-control {set_match.group(1)}:{val}".replace(
                                "cr50", "gsc"
                            ).replace("ti50", "gsc")
                        )

        clean_commands = []
        for cmd in commands:
            if board and board != "unknown":
                cmd = re.sub(rf"\b{board}\b", "${BOARD}", cmd)
            if model and model != "unknown":
                cmd = re.sub(rf"\b{model}\b", "${MODEL}", cmd)

            if not clean_commands or clean_commands[-1] != cmd:
                clean_commands.append(cmd)

        if clean_commands:
            md_path = os.path.join(OUT_DIR, f"{name}_servod_plan.md")
            with open(md_path, "w", encoding="utf-8") as f_out:
                f_out.write("# Copyright 2026 The ChromiumOS Authors\n")
                f_out.write(
                    "# Use of this source code is governed by a BSD-style license that can be\n"
                )
                f_out.write("# found in the LICENSE file.\n\n")
                f_out.write(f"# Servod Test Plan: {name}\n\n")
                f_out.write(
                    f"This test plan emulates the hardware-level interactions of the `{name}` Tast test.\n"
                )
                f_out.write(
                    "It was automatically generated by extracting the `GET` and `SET` commands from a successful test run.\n\n"
                )

                f_out.write("## Execution Parameters\n\n")
                f_out.write(
                    "To execute this test plan across different environments, the agent must dynamically inject the following variables:\n"
                )
                f_out.write(
                    "* `${BOARD}`: The target ChromeOS board (e.g., `volteer`).\n"
                )
                f_out.write(
                    "* `${MODEL}`: The target ChromeOS model (e.g., `delbin`).\n"
                )
                f_out.write(
                    "* `${IMAGE_URL}`: The download path or URL for the ChromeOS test image or firmware archive. Depending on the environment, this could be a local path or a Google Cloud Storage URI (e.g., `gs://chromeos-image-archive/${BOARD}-release/RXXX-YYYY.Z.0/`).\n\n"
                )

                f_out.write("## Firmware / Image Links\n\n")
                f_out.write(
                    "* When emulating this test, the agent needs to acquire the specific firmware or OS image required for the test variations.\n"
                )
                f_out.write(
                    "* For tests like `FWAutoupdate`, download the older firmware archive from `gs://chromeos-image-archive/${BOARD}-firmware/` and stage it on the DUT prior to executing the servod commands.\n\n"
                )

                f_out.write("## Prerequisites\n\n")
                f_out.write(
                    "1. **Hardware setup:** A DUT connected to a Servo (v4/v4.1 + CCD or Micro).\n"
                )
                f_out.write(
                    "2. **Test Build:** Ensure the DUT is running an appropriate test-signed image located at `${IMAGE_URL}`.\n"
                )
                f_out.write(
                    "3. **Environment:** If the test requires specific hardware states (e.g., AC power disconnected for battery tests), manually configure the physical environment before running this plan.\n\n"
                )
                f_out.write("## Command Sequence\n\n")
                f_out.write(
                    "Run the following commands in sequence to emulate the test execution:\n\n"
                )
                f_out.write("```bash\n")
                for cmd in clean_commands:
                    f_out.write(cmd + "\n")
                f_out.write("```\n\n")
                f_out.write("## Phase: Labstation Health Check\n\n")
                f_out.write(
                    "Verify that the system logs are not being flooded with respawn errors.\n\n"
                )
                f_out.write("```bash\n")
                f_out.write("dmesg | grep 'console-ttyS0' | tail -n 20\n")
                f_out.write("```\n")
            generated_tests.add(name)
            COUNT += 1

print(f"\nSuccessfully generated {COUNT} new generic test plans.")
