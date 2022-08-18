# Copyright 2022 The ChromiumOS Authors.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import time
from enum import Enum
from itertools import count


class DeviceType(Enum):
    SERVOV4P1 = 1
    CR50 = 2


device_details = {}
device_details[DeviceType.SERVOV4P1] = {"idVendor": 0x18D1, "idProduct": 0x520D}
device_details[DeviceType.CR50] = {"idVendor": 0x18D1, "idProduct": 0x5014}

DEFAULT_SERIALS = {
    DeviceType.SERVOV4P1: "SERVOV4P1-S-%s%d",
    DeviceType.CR50: "1002303D-%s%d",
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


def get_board_model_pairs(exclude_list=None):
    """Get a list of board, model tuples that can have tests scheduled.

    If a test can not run for a specific board

    Args:
        exclude_list (list, optional): List of boards to exclude from the returned list. Defaults to None.

    Returns:
        list if string tuples: board model pairs.
    """
    # TODO(haddowk) generate this list dynamically from the files in /data/*
    return [
        ("asuka", "default"),
        ("asurada", "default"),
        ("atlas", "default"),
        ("bloonchipper", "default"),
        ("bob", "default"),
        ("brask", "default"),
        ("brya", "banshee"),
        ("brya", "default"),
        ("brya", "volmar"),
        ("chell", "default"),
        ("cherry", "default"),
        ("cheza", "default"),
        ("chocodile", "default"),
        ("coral", "default"),
        ("d2db", "default"),
        ("dartmonkey", "default"),
        ("dedede", "bugzzy"),
        ("dedede", "magolor"),
        ("dedede", "metaknight"),
        ("dedede", "default"),
        ("dedede", "sasuke"),
        ("draco", "default"),
        ("dragonclaw", "default"),
        ("dragontalon", "default"),
        ("drallion", "default"),
        ("electro", "default"),
        ("endeavour", "default"),
        ("eve", "default"),
        ("excelsior", "default"),
        ("fizz", "labstation"),
        ("fizz", "default"),
        ("flapjack", "default"),
        ("ghost", "default"),
        ("goroh", "default"),
        ("grunt", "default"),
        ("guybrush", "default"),
        ("hammer", "default"),
        ("hatch", "default"),
        ("hayato", "default"),
        ("herobrine", "default"),
        ("icetower", "default"),
        ("jacuzzi", "default"),
        ("kahlee", "default"),
        ("kalista", "default"),
        ("keeby", "habokay"),
        ("keeby", "haboki"),
        ("keeby", "lalala"),
        ("keeby", "default"),
        ("kingler", "default"),
        ("krabby", "default"),
        ("krane", "default"),
        ("kukui", "common"),
        ("kukui", "icarus"),
        ("kukui", "jacuzzi"),
        ("kukui", "default"),
        ("mancomb", "default"),
        ("mistral", "default"),
        ("nami", "default"),
        ("nasher", "default"),
        ("nautilus", "default"),
        ("nightfury", "default"),
        ("nissa", "craask"),
        ("nissa", "ite"),
        ("nissa", "nereid"),
        ("nissa", "nivviks"),
        ("nissa", "npcx"),
        ("nocturne", "default"),
        ("octopus", "ampton"),
        ("octopus", "apel"),
        ("octopus", "casta"),
        ("octopus", "ite"),
        ("octopus", "npcx"),
        ("octopus", "default"),
        ("poppy", "default"),
        ("puff", "default"),
        ("rammus", "default"),
        ("sand", "default"),
        ("sarien", "default"),
        ("scarlet", "default"),
        ("skyrim", "default"),
        ("snappy", "default"),
        ("soraka", "default"),
        ("spherion", "default"),
        ("trogdor", "default"),
        ("volteer", "default"),
        ("volteer", "usbdb"),
        ("waddledee", "default"),
        ("waddledoo", "default"),
        ("zerblebarn", "default"),
        ("zoombini", "default"),
        ("zork", "default"),
    ]


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
