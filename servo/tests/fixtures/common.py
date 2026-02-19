# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import glob
import os
import time

import servo.common.servo_dev_templates as tmpl


class TestFixtureError(Exception):
    """Raised when there is an issue with test fixture code."""


device_types = [
    "servo_v4p1",
    "ccd_cr50",
    "ccd_gsc",
    "ccd_gsc_nt",
    "servo_micro",
    "c2d2",
]
device_details = {}
for _device_type in device_types:
    device_details[_device_type] = {
        "idVendor": tmpl.get_vid(_device_type),
        "idProduct": tmpl.get_pid(_device_type),
    }
del _device_type

DEFAULT_SERIALS = {
    "servo_v4p1": "SERVOV4P1-S-%s%d",
    "ccd_cr50": "1002303D-%s%d",
    "ccd_gsc": "2002303D-%s%d",
    "ccd_gsc_nt": "3002303D-%s%d",
    "servo_micro": "MICRO-S-%s%d",
    "c2d2": "100860-%s%d",
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
    # parallel.
    return DEFAULT_SERIALS[device_type] % (
        os.environ.get("PYTEST_XDIST_WORKER", "Not_running_threaded"),
        round(time.time() * 1000),
    )


def board_supports_servo_type(board, servo_type):
    """Check if the servo type is relevant for the given board.

    Args:
        board: board name
        servo_type: servo type string

    Returns:
        True if the servo type is valid for the given board.
    """
    c2d2_boards = [
        "brya",
        "cherry",
        "dedede",
        "guybrush",
        "nissa",
        "skyrim",
    ]
    # C2D2 servos are only usable on C2D2 boards. All other boards use the
    # 50 pin servo header (servo micro).
    return ("c2d2" in servo_type) == (board in c2d2_boards)


def get_board_model_pairs(board_exclude_list=None):
    """Get a list of board, model tuples that can have tests scheduled.

    If a test can not run for a specific board

    Args:
        board_exclude_list (list, optional): List of boards to exclude from the
                                             returned list. Defaults to None.

    Returns:
        list if string tuples: board model pairs.
    """
    if board_exclude_list is None:
        board_exclude_list = []
    exclude_list = [
        "servo_nissa_nirwen_ufs_overlay.xml",  # File not in correct format
        "servo_fpmcu_dev_board_common_overlay.xml",  # File not in correct format
        "servo_fpmcu_dev_board_uart_common_overlay.xml",  # File not in correct format
        # Not working as it includes servo_fpmcu_dev_board xmls
        "servo_bloonchipper_overlay.xml",
        # Not working as it includes servo_fpmcu_dev_board xmls
        "servo_dartmonkey_overlay.xml",
        # Not working as it includes servo_fpmcu_dev_board xmls
        "servo_dragonclaw_overlay.xml",
        # Not working as it includes servo_fpmcu_dev_board xmls
        "servo_dragontalon_overlay.xml",
        # Not working as it includes servo_fpmcu_dev_board xmls
        "servo_helipilot_overlay.xml",
        # Not working as it includes servo_fpmcu_dev_board xmls
        "servo_icetower_overlay.xml",
        # Not working as it includes servo_fpmcu_dev_board xmls
        "servo_quincy_overlay.xml",
        # Not working as it includes servo_fpmcu_dev_board xmls
        "servo_zerblebarn_overlay.xml",
        "servo_chocodile_overlay.xml",  # Not working as it includes servo_micro.xml
        "servo_hana_overlay.xml",  # Not working
        "servo_elm_overlay.xml",  # Not working
        "servo_oak_overlay.xml",  # Not working
    ]
    filenames = glob.glob("/usr/local/lib/*/*-packages/servo/data/servo_*_overlay.xml")
    board_model_list = []
    for filename in filenames:
        basename = os.path.basename(filename)

        if basename in exclude_list:
            continue

        parts = basename[:-4].split("_")

        if parts[1] in board_exclude_list:
            continue

        if len(parts) == 3:
            board_model_list.append((parts[1], "default"))
        elif len(parts) == 4:
            board_model_list.append((parts[1], parts[2]))
        else:
            raise TestFixtureError(
                "Data file %s not in correct format - untested"
                % os.path.basename(filename)
            )

    if not board_model_list:
        raise TestFixtureError("Failed to find ANY boards, likely there is a test bug.")

    if os.getenv("SERVOD_LIMIT_TEST_DUT"):
        board_model_list = board_model_list[: int(os.getenv("SERVOD_LIMIT_TEST_DUT"))]

    return board_model_list


def compare_results(expected, results):
    """Compare two dicts of endpoint data to see if they are equivalent.

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
                result_command = None
                if len(results[serial][interface]) > index:
                    result_command = results[serial][interface][index]

                if expected_command != result_command:
                    print(
                        "Error Serial: %s EP: %d Command: %s Expected %s"
                        % (serial, interface, result_command, expected_command),
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
