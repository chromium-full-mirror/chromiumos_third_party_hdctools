#!/usr/bin/python3
# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import csv
import subprocess
import sys


FAFT_TESTS = ["servo_USBMuxVerification", "servo_LogGrab"]
TAST_TESTS = [
    "labqual.BootupTimesUSB.usb_recovery",
    "labqual.ECControlRead",
    "labqual.ServoGBBFlagsFutility",
    "labqual.ServoDeviceBatteryCheck",
]


def run_crosfleet(board, dut_name, testname, harness):
    command = [
        "crosfleet",
        "run",
        "test",
        "-exit-early",
        "-board",
        board,
        "-harness",
        harness,
        "-pool",
        "servo_verification",
        "-priority",
        "50",
        "-dim",
        "dut_name:" + dut_name,
        testname,
    ]
    subprocess.run(command, check=True)


def main(unused_argv):
    parser = argparse.ArgumentParser(
        description="Run crosfleet tests with DUTs from a CSV file."
    )
    parser.add_argument(
        "--csv-file", help="Path to the CSV file containing DUT information."
    )
    args = parser.parse_args()

    with open(args.csv_file, "r", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            dut_name, board = row[0], row[1]

            for test in FAFT_TESTS:
                run_crosfleet(board, dut_name, test, "tauto")

            for test in TAST_TESTS:
                run_crosfleet(board, dut_name, test, "tast")


if __name__ == "__main__":
    main(sys.argv)
    sys.exit(0)
