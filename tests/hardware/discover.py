#!/usr/bin/env python3
# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Hardware Discovery Module.
Can detect connected servos over SSH or locally.
"""

import argparse
import csv
import logging
import subprocess
import sys


logger = logging.getLogger(__name__)


class HardwareDiscovery:
    """Abstracts the discovery of Servo devices on a target host."""

    def __init__(self, backend, target=None):
        self.backend = backend  # 'local' or 'ssh'
        self.target = target  # e.g., 'labstation.obair.xyz'

    def _run_cmd(self, cmd):
        """Runs a shell command either locally or over SSH."""
        if self.backend == "ssh":
            if not self.target:
                raise ValueError("Target host required for SSH backend.")
            full_cmd = [
                "ssh",
                "-o",
                "StrictHostKeyChecking=no",
                f"root@{self.target}",
            ] + cmd
        else:
            full_cmd = cmd

        logger.debug("Running: %s", " ".join(full_cmd))
        result = subprocess.run(full_cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            logger.error("Command failed: %s", result.stderr)
            return None
        return result.stdout

    def discover_servos(self):
        """
        Parses lsusb to find all connected USB serial numbers.
        Returns a list of serial numbers.
        """
        cmd = ["lsusb", "-v"]

        if self.backend == "local":
            # It's usually fine without sudo, but let's try gracefully.
            pass

        output = self._run_cmd(cmd)
        if not output:
            return []

        serials = set()
        for line in output.splitlines():
            if "iSerial" in line:
                parts = line.split()
                if len(parts) >= 3:
                    serial = parts[-1].strip()
                    # Filter out empty serials, generic hubs
                    if len(serial) > 5 and (
                        "SERVO" in serial.upper()
                        or "C2D2" in serial.upper()
                        or "-" in serial
                    ):
                        serials.add(serial)

        return list(serials)

    def write_csv(self, serials, filename="discovered_duts.csv"):
        """
        Writes the discovered serials to a CSV file.
        Since we don't inherently know the board/model attached to a raw servo serial
        from just lsusb, we leave them as placeholders for the user to fill, OR
        we can default them if requested.
        """
        with open(filename, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            for s in serials:
                # We use empty strings as placeholders. The Orchestrator or the user
                # can update these if specific board/models are needed for the test.
                writer.writerow(["", "", s])
        logger.info("Wrote %d devices to %s", len(serials), filename)


def main():
    parser = argparse.ArgumentParser(description="Auto-discover connected servos.")
    parser.add_argument(
        "--backend",
        choices=["local", "ssh"],
        default="local",
        help="Where to run the discovery (local machine or remote SSH).",
    )
    parser.add_argument(
        "--host",
        type=str,
        help="The target hostname if backend is 'ssh' (e.g., labstation).",
    )
    parser.add_argument(
        "--out", type=str, default="discovered_duts.csv", help="The output CSV file."
    )
    parser.add_argument("--verbose", action="store_true")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if args.backend == "ssh" and not args.host:
        logger.error("--host is required when using the 'ssh' backend.")
        sys.exit(1)

    discoverer = HardwareDiscovery(backend=args.backend, target=args.host)
    print(f"Discovering servos via {args.backend}...")

    serials = discoverer.discover_servos()

    if not serials:
        print("No servos found or command failed.")
        sys.exit(1)

    print(f"Found {len(serials)} servos:")
    for s in serials:
        print(f"  - {s}")

    discoverer.write_csv(serials, args.out)


if __name__ == "__main__":
    main()
