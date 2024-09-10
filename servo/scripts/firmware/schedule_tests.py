#!/usr/bin/python3
# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import csv
import subprocess
import sys


def run_crosfleet(board, dut_name, testname):
    command = [
        "crosfleet",
        "run",
        "test",
        "-exit-early",
        "-board",
        board,
        "-harness",
        "tauto",
        "-pool",
        "servo_verification",
        "-priority",
        "50",
        "-dim",
        "dut_name:" + dut_name,
        testname,
    ]
    subprocess.run(command)


def main(unused_argv):
    parser = argparse.ArgumentParser(
        description="Run crosfleet tests with DUTs from a CSV file."
    )
    parser.add_argument(
        "--csv-file", help="Path to the CSV file containing DUT information."
    )
    args = parser.parse_args()

    with open(args.csv_file, "r") as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            dut_name = row[0]
            board = row[1]
            run_crosfleet(board, dut_name, "servo_USBMuxVerification")
            run_crosfleet(board, dut_name, "platform_ServoPowerStateController.usb")
            run_crosfleet(board, dut_name, "firmware_FAFTSetup")
            run_crosfleet(board, dut_name, "servo_LogGrab")


if __name__ == "__main__":
    main(sys.argv)
    sys.exit(0)
