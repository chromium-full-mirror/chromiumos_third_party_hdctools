# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import glob
import logging
import os
import time
import pytest

from enum import Enum
from itertools import count

import servo.servo_dev_templates as tmpl


device_details = {}
device_details[tmpl.ServoV4p1.TYPE] = {"idVendor": tmpl.ServoV4p1.VID, "idProduct": tmpl.ServoV4p1.PID}
device_details[tmpl.CcdCr50.TYPE] = {"idVendor": tmpl.CcdCr50.VID, "idProduct": tmpl.CcdCr50.PID}
device_details[tmpl.ServoMicro.TYPE] = {"idVendor": tmpl.ServoMicro.VID, "idProduct": tmpl.ServoMicro.PID}

DEFAULT_SERIALS = {
    tmpl.ServoV4p1.TYPE: "SERVOV4P1-S-%s%d",
    tmpl.CcdCr50.TYPE: "1002303D-%s%d",
    tmpl.ServoMicro.TYPE: "MICRO-S-%s%d",
}

PTY_END_LINE = b""


def get_servo_serial(device_type):
    """Generate a unique serial number for a device.

    Try to keep the serial number similar to what the genuine serial
    number are but may be longer.

    TODO(haddowk) - think of better ways to get the serial to be
    in the exact format of the genuine device, but also unique.

    Args:
        device_type (enum): The type of device to generate a serial number for.

    Returns:
        _type_: _description_
    """
    # PYTEST_XDIST_WORKER is a thread id when we are running the tests in
    # parrallel. https://pypi.org/project/pytest-xdist/#identifying-the-worker-process-during-a-test
    return DEFAULT_SERIALS[device_type] % (
        os.environ.get("PYTEST_XDIST_WORKER", "Not_running_threaded"),
        round(time.time() * 1000),
    )


def get_board_model_pairs(board_exclude_list=[]):
    """Get a list of board, model tuples that can have tests scheduled.

    If a test can not run for a specific board

    Args:
        board_exclude_list (list, optional): List of boards to exclude from the returned list. Defaults to None.

    Returns:
        list if string tuples: board model pairs.
    """
    exclude_list = [
        "servo_nissa_nirwen_ufs_overlay.xml",   # File not in correct format
        "servo_fpmcu_dev_board_common_overlay.xml", # File not in correct format
        "servo_fpmcu_dev_board_uart_common_overlay.xml", # File not in correct format
        "servo_hana_overlay.xml",   # Not working
        "servo_elm_overlay.xml",   # Not working
        "servo_oak_overlay.xml",   # Not working
    ]
    filenames = glob.glob("/usr/local/lib/*/site-packages/servo/data/servo_*_overlay.xml")
    board_model_list = []
    for filename in filenames:
        basename = os.path.basename(filename)

        if basename in exclude_list:
            continue

        parts = basename[:-4].split('_')

        if parts[1] in board_exclude_list:
            continue

        if len(parts) == 3:
            board_model_list.append((parts[1], "default"))
        elif len(parts) == 4:
            board_model_list.append((parts[1], parts[2]))
        else:
            raise Exception("Data file %s not in correct format - untested" % os.path.basename(filename))

    return board_model_list


def compare_results(expected, results):
    """Compare two dicts of endpoint data to see if they are equivelent.

    Args:
        expected (dict): The endpoint commands the test was expected to generate.
        results (dict): The actual endpoint command the test generated.

    Returns:
        bool : True if the dicts are equal - False otherwise.
    """
    result = True
    # TODO(haddowk) check that the number of device are the same in both dicts.
    for serial in expected.keys():
        # TODO(haddowk) check that each device has same number of interfaces.
        for interface in expected[serial].keys():
            for index in range(0, len(expected[serial][interface])):
                expected_command = expected[serial][interface][index]
                result_commmand = None
                if len(results[serial][interface]) > index:
                    result_commmand = results[serial][interface][index]

                if expected_command != result_commmand:
                    print(
                        "Error Serial: %s EP: %d Command: %s Expected %s"
                        % (serial, interface, result_commmand, expected_command),
                        flush=True,
                    )
                    result = False
                else:
                    print(
                        "Correct result Serial: %s EP: %d Command: %s"
                        % (serial, interface, expected_command),
                        flush=True,
                    )
        if results[serial]["missing"] != []:
            print(
                "Error Serial: %s - commands without mock data"
                % results[serial]["missing"]
            )
            result = False

    return result
