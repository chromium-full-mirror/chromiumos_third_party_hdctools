#!/usr/bin/env python3
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Unified Servod Hardware-in-the-Loop (HIL) Tester.
Provides a single interface to execute test plans against either
a bare-metal Labstation or a containerized Test Orchestrator.
"""

import argparse
import csv
import json
import logging
import sys
import uuid

import requests


logger = logging.getLogger(__name__)


def parse_csv(csv_path):
    """Parses the DUT matrix CSV file."""
    duts = []
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 3:
                    # Expecting: board, model, serial
                    duts.append(
                        {
                            "board": row[0].strip(),
                            "model": row[1].strip(),
                            "serial": row[2].strip(),
                        }
                    )
        return duts
    except Exception as e:
        logger.error("Failed to read CSV %s: %s", csv_path, e)
        sys.exit(1)


def load_plan(plan_path):
    """Loads the test plan JSON or YAML."""
    try:
        with open(plan_path, "r", encoding="utf-8") as f:
            # Simplified: just treating it as JSON for now
            return json.load(f)
    except Exception as e:
        logger.error("Failed to read Test Plan %s: %s", plan_path, e)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Unified Servod HIL Tester")
    parser.add_argument("plan", help="Path to the JSON test plan file")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    subparsers = parser.add_subparsers(
        dest="backend", required=True, help="Execution backend"
    )

    # Labstation Backend
    ssh_parser = subparsers.add_parser(
        "ssh", help="Execute on a bare-metal Labstation via SSH"
    )
    ssh_parser.add_argument(
        "--host", required=True, help="Labstation hostname (e.g., labstation)"
    )
    ssh_parser.add_argument("--csv", required=True, help="Path to DUT CSV matrix")

    # Orchestrator Backend
    orch_parser = subparsers.add_parser(
        "orchestrator", help="Execute via the Test Orchestrator"
    )
    orch_parser.add_argument(
        "--url", default="http://localhost:5000", help="Orchestrator URL"
    )
    orch_parser.add_argument("--image", required=True, help="Docker image to deploy")
    orch_parser.add_argument("--csv", required=True, help="Path to DUT CSV matrix")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    logger.info("Initializing Unified HIL Tester...")
    logger.info("Loading Test Plan: %s", args.plan)

    test_plan = load_plan(args.plan)
    logger.debug("Plan loaded: %s", test_plan)

    if args.backend == "ssh":
        logger.info("Selected Backend: SSH")
        logger.info("Target Host:      %s", args.host)
        duts = parse_csv(args.csv)
        logger.info("Found %d DUTs in matrix.", len(duts))
        logger.error("SSH Backend execution is not fully implemented yet.")
        sys.exit(1)

    elif args.backend == "orchestrator":
        logger.info("Selected Backend: ORCHESTRATOR")
        logger.info("Orchestrator URL: %s", args.url)
        logger.info("Docker Image:     %s", args.image)

        duts = parse_csv(args.csv)
        logger.info("Found %d DUTs in matrix.", len(duts))

        for dut in duts:
            job_id = f"{uuid.uuid4().hex[:8]}-{dut['serial']}"
            job_payload = {
                "job_id": job_id,
                "image_name": args.image,
                "servod_args": [
                    f"BOARD={dut['board']}",
                    f"MODEL={dut['model']}",
                    f"SERIAL={dut['serial']}",
                ],
                "start_servod_args": ["-c", "local"],
                "test_commands": test_plan.get("commands", []),
                "lifecycle_test": test_plan.get("lifecycle_test", False),
                "fault_injection": test_plan.get("fault_injection", []),
            }
            logger.info("Submitting job %s for DUT %s...", job_id, dut["serial"])
            try:
                response = requests.post(
                    f"{args.url}/api/jobs", json=job_payload, timeout=10
                )
                response.raise_for_status()
                logger.info("Job successfully queued: %s", job_id)
            except requests.exceptions.RequestException as e:
                logger.error("Failed to queue job for DUT %s: %s", dut["serial"], e)

        logger.info("All orchestrator jobs submitted. Use Orchestrator UI to monitor.")


if __name__ == "__main__":
    main()
