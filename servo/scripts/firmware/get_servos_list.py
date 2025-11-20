#!/usr/bin/python3
# Copyright 2024 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import csv
import random
import subprocess
import sys


SERVO_TYPES = ["servo_v4", "servo_v4p1", "servo_micro", "c2d2"]
POOLS = [
    "DUT_POOL_QUOTA",
    "servo_verification",
    "faft-test",
    "wificell",
    "chameleon_audio",
]
SERVO_STATES = ["WORKING"]
STATES = ["ready"]
SERVO_FW_CHANNELS = ["STABLE", "ALPHA", "DEV"]
ALL = ["%"]


def join_helper(to_join: list) -> str:
    """
    Helper function to format a list for inclusion in a SQL query.
    It adds quotes around each element and joins them with commas.

    Args:
        to_join (list): A list of strings to format.

    Returns:
        str: A string representation of the formatted list.
    """
    for i in range(len(to_join)):
        to_join[i] = '"' + to_join[i] + '"'
    return ",".join(to_join)


def define_query(
    servo_type_raws: list = None,
    pools: list = None,
    states: list = None,
    servo_states: list = None,
    servo_fw_channels: list = None,
) -> str:
    """
    Constructs a SQL query to fetch DUT information from the UFS based on provided
    filter criteria.

    Args:
        servo_type_raws (list): List of servo types to filter by (default is all '%').
        pools (list): List of pools to filter by (default is all '%').
        states (list): List of DUT states to filter by (default is all '%').
        servo_states (list): List of servo states to filter by (default is all '%').
        servo_fw_channels (list): List of servo firmware channels to filter by (default
                                  is all '%').

    Returns:
        str: The constructed SQL query string.

    Raises:
        ValueError: If any of the provided filter values are invalid or unsupported.
    """

    if servo_type_raws is None:
        servo_type_raws = ["%"]
    if pools is None:
        pools = ["%"]
    if states is None:
        states = ["%"]
    if servo_states is None:
        servo_states = ["%"]
    if servo_fw_channels is None:
        servo_fw_channels = ["%"]

    # Validate and preprocess servo_type_raws
    tmp_servo_type_raws = servo_type_raws.copy()
    for i in range(len(servo_type_raws)):
        if servo_type_raws[i] not in SERVO_TYPES + ALL:
            raise ValueError(f"{servo_type_raws[i]} is not a supported servo type.")
        if servo_type_raws[i] == "servo_v4p1":
            tmp_servo_type_raws[i] = r"servo\\_v4p1\\_%"
        elif servo_type_raws[i] == "servo_v4":
            tmp_servo_type_raws[i] = r"servo\\_v4\\_%"
        elif servo_type_raws[i] == "servo_micro":
            tmp_servo_type_raws[i] = r"%servo\\_micro%"
        elif servo_type_raws[i] == "c2d2":
            tmp_servo_type_raws[i] = r"%c2d2%"

    # Validate other filter criteria
    for pool in pools:
        if pool not in POOLS + ALL:
            raise ValueError(f"{pool} is not a supported pool.")

    for state in states:
        if state not in STATES + ALL:
            raise ValueError(f"{state} is not a supported DUT state.")

    for servo_state in servo_states:
        if servo_state not in SERVO_STATES + ALL:
            raise ValueError(f"{servo_state} is not a supported servo state.")

    for servo_fw_channel in servo_fw_channels:
        if servo_fw_channel not in SERVO_FW_CHANNELS + ALL:
            raise ValueError(
                f"{servo_fw_channel} is not a supported servo fw channels."
            )

    # Construct the SQL query with sql_filter conditions
    sql_filter = (
        """EXISTS (SELECT 1 FROM UNNEST([%s]) AS pattern WHERE %s LIKE pattern)"""
    )
    query = f"""
        SELECT DISTINCT hostname, board, model, state, servo_state
        FROM chrome_fleet_analytics.cros_fleet.latest_dut_info
        WHERE RIGHT(board, 10) != 'labstation'
        AND {sql_filter % (join_helper(tmp_servo_type_raws), "servo_type_raw")}
        AND {sql_filter % (join_helper(pools), "pool")}
        AND {sql_filter % (join_helper(states), "state")}
        AND {sql_filter % (join_helper(servo_fw_channels), "servo_fw_channel")}
        AND {sql_filter % (join_helper(servo_states), "servo_state")}
        AND pool NOT LIKE "%satlab%"
        AND hostname NOT like "%satlab%"
        AND servo_hostname NOT IN (
            SELECT
                DISTINCT hostname
            FROM chrome_fleet_analytics.cros_fleet.latest_dut_info
            WHERE hostname LIKE "%labstation%"
            AND model LIKE "%guado%"
        );
    """

    return query


def run_command(command: str or list) -> subprocess.CompletedProcess:
    """
    Executes a shell command and returns the output.

    Args:
        command (string or list): The command to run

    Returns:
        subprocess.CompletedProcess: All the information about the command execution.
    """

    return subprocess.run(command, stdout=subprocess.PIPE, check=True)


def get_hostnames(query: str) -> list[list[str]]:
    """
    Queries the UFS using the provided SQL query and extracts hostnames from the result.

    Args:
        query (str): The SQL query to execute.

    Returns:
        list[list[str]]: A list of lists, where each inner list contains hostname,
                                board, model, state, and servo_state of a DUT.
    """

    ps = subprocess.Popen(["echo", query], stdout=subprocess.PIPE)
    hostnames = (
        subprocess.check_output(
            ("f1-sql", "--csv_output"), stdin=ps.stdout, stderr=subprocess.DEVNULL
        )
        .strip()
        .split(b"\n")
    )

    # hostname, board, model, state, servo_state
    hostnames_list = []
    # skip 1st row, with column names
    for hostname in hostnames[1:]:
        hostnames_list.append(
            hostname.decode("utf-8").strip().replace('"', "").split(",")
        )

    return hostnames_list


def group_all_hostnames_by_model(
    hostnames_list: list[list[str]],
) -> dict[str, list[list[str]]]:
    """
    Groups DUT hostnames by their model.

    Args:
        hostnames_list (list[list[str]]): A list of lists containing DUT information.

    Returns:
        dict[str, list[list[str]]]: A dictionary where keys are DUT models and values
                            are lists of DUT details for that model.
    """

    model = 2  # Index of the model in the inner list
    hostnames_by_model = {}

    for hostname_details in hostnames_list:
        # check if we already have key and list for specific model
        if hostname_details[model] not in hostnames_by_model:
            hostnames_by_model[hostname_details[model]] = []

        hostnames_by_model[hostname_details[model]].append(hostname_details)

    return hostnames_by_model


# we want to have specifc percent of model duts included
def get_random_list_of_hostnames(
    hostnames_by_model: dict[str, list[list[str]]], percent: int
) -> list[list[str]]:
    """
    Randomly selects a specified percentage of DUTs from each model group.

    Args:
        hostnames_by_model (dict[str, list[list[str]]]): A dictionary of DUTs grouped
                                                         by model.
        percent (int): The percentage of DUTs to select from each model.

    Returns:
        list[list[str]]: A list of randomly selected DUT details.
    """

    random_hostnames = []
    all_len = 0
    for model, hostnames in hostnames_by_model.items():
        number_of_devices_to_update = int(
            len(hostnames_by_model[model]) * percent / 100
        )

        print(
            f"There is {len(hostnames_by_model[model])} of {model} available, "
            f"would randomly select {number_of_devices_to_update} devices for update."
        )

        random_hostnames.extend(random.sample(hostnames, number_of_devices_to_update))
        all_len += len(hostnames)

    print(
        f"Selected {len(random_hostnames)} devices of "
        f"{all_len}, what is {len(random_hostnames) / all_len * 100} percent"
    )

    return random_hostnames


def parse_args() -> argparse.Namespace:
    """Parse the command line args

    Returns:
        argparse.Namespace: Parsed arguments.
    """
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument(
        "--servo-type",
        required=True,
        nargs="+",
        type=str,
        help="[Required] Choose servo type.",
    )
    parser.add_argument(
        "--stage",
        required=True,
        choices=[
            "tests",
            "first",
            "second",
            "all-stable",
            "all-alpha",
            "all-dev",
            "manual",
            "first-ocd",
            "second-ocd",
        ],
        type=str,
        help="[Required] Choose option. Usage described in readme.",
    )
    # TODO add logic for all arguments below, to have tool
    # for getting more advanced servo lists
    parser.add_argument(
        "--fw-channel",
        required=False,
        nargs="+",
        type=str,
        help="Fw channel(s) to list. If no specified take all.",
    )
    parser.add_argument(
        "--pool",
        required=False,
        nargs="+",
        type=str,
        help="Device pool(s) to list. If no specified take all.",
    )
    parser.add_argument(
        "--servo-state",
        required=False,
        nargs="+",
        type=str,
        help="Servo state filter. If no specified take all.",
    )
    parser.add_argument(
        "--dut-state",
        required=False,
        nargs="+",
        type=str,
        help="Dut state filter. If no specified take all.",
    )
    return parser.parse_args()


def define_stage_rollout(args: argparse.Namespace) -> list[list[str]]:
    """
    Defines the DUT selection logic and returns ready to use list based on the specified
    stage.

    Args:
        args (argparse.Namespace): Parsed command-line arguments.

    Returns:
        list[list[str]]: A list of lists containing DUT information (hostname, board,
                         model, state, servo_state) based on the selected stage.
    """
    if args.stage == "tests":
        query = define_query(
            servo_type_raws=args.servo_type,
            pools=["servo_verification"],
        )
        return get_hostnames(query)
    # 1st stage is ~10% of every available model within DUT_POOL_QUOTA,
    # chosen only from working devices
    if args.stage == "first":
        # We are choosing only from working devices, so to get ~10% of all lets use ~13%
        percent = 13
        query = define_query(
            servo_type_raws=args.servo_type,
            pools=["DUT_POOL_QUOTA"],
            servo_fw_channels=["STABLE"],
            servo_states=["WORKING"],
            states=["ready"],
        )
        all_hostnames_by_model = group_all_hostnames_by_model(get_hostnames(query))
        return get_random_list_of_hostnames(all_hostnames_by_model, percent)
    # We need to organize roll-out for OCD servos a little different because e.g most of
    # these setups are in specialized pools, not in DUT_POOL_QUOTA
    if args.stage == "first-ocd":
        # We are choosing only from working devices, so to get ~10% of all lets use ~15%
        # C2D2 population is super small, so no need for 3 stages
        if "c2d2" in args.servo_type:
            percent = 60
        else:
            percent = 15
        query = define_query(
            servo_type_raws=args.servo_type,
            servo_fw_channels=["STABLE"],
            servo_states=["WORKING"],
            states=["ready"],
        )
        all_hostnames_by_model = group_all_hostnames_by_model(get_hostnames(query))
        return get_random_list_of_hostnames(all_hostnames_by_model, percent)
    # 2nd stage, we increasing DUT_POOL_QUOTA to 33% and take all pools NAMED:
    if args.stage == "second":
        # We are choosing only from working devices and assuming ~10% is already in
        # alpha, so to get ~33% lets use 25 here
        percent = 25
        query = define_query(
            servo_type_raws=args.servo_type,
            pools=["DUT_POOL_QUOTA"],
            servo_fw_channels=["STABLE"],
            servo_states=["WORKING"],
            states=["ready"],
        )
        all_hostnames_by_model = group_all_hostnames_by_model(get_hostnames(query))
        random_hostnames = get_random_list_of_hostnames(all_hostnames_by_model, percent)

        query_other_pools = define_query(
            servo_type_raws=args.servo_type,
            pools=["faft-test", "wificell", "chameleon_audio"],
            servo_fw_channels=["STABLE"],
        )

        other_pools_hostnames = get_hostnames(query_other_pools)
        return other_pools_hostnames + random_hostnames
    if args.stage == "second-ocd":
        # We are choosing only from working devices and assuming ~10% is already in
        # alpha, so to get ~33% in total (together with 1st stage) lets use 25 here
        if "c2d2" in args.servo_type:
            percent = 100
        else:
            percent = 25
        query = define_query(
            servo_type_raws=args.servo_type,
            servo_fw_channels=["STABLE"],
            servo_states=["WORKING"],
            states=["ready"],
        )
        all_hostnames_by_model = group_all_hostnames_by_model(get_hostnames(query))
        random_hostnames = get_random_list_of_hostnames(all_hostnames_by_model, percent)
        return random_hostnames
    # Simply get all devices left in STABLE or in ALPHA
    if args.stage == "all-stable":
        query = define_query(
            servo_type_raws=args.servo_type,
            servo_fw_channels=["STABLE"],
        )
        return get_hostnames(query)
    if args.stage == "all-alpha":
        query = define_query(
            servo_type_raws=args.servo_type,
            servo_fw_channels=["ALPHA"],
        )
        return get_hostnames(query)
    if args.stage == "all-dev":
        query = define_query(
            servo_type_raws=args.servo_type,
            servo_fw_channels=["DEV"],
        )
        return get_hostnames(query)


def define_manual_list(args):
    """
    Prepare query and final list based on all arguments manually passed by user

    Args:
        args (argparse.Namespace): Parsed command-line arguments.

    Returns:
        list[list[str]]: A list of lists containing DUT information (hostname, board,
                         model, state, servo_state) based on the selected filter.
    """
    query = define_query(
        servo_type_raws=args.servo_type,
        pools=args.pool,
        states=args.dut_state,
        servo_states=args.servo_state,
        servo_fw_channels=args.fw_channel,
    )
    return get_hostnames(query)


def write_csv(
    hostnames: list[list[str]], csv_file: str, debug_mode: bool = False
) -> None:
    """
    Writes the list of hostnames to a CSV file.

    Args:
        hostnames (list[list[str]]): A list of lists containing DUT information.
        csv_file (str): The name of the CSV file to write to.
        debug_mode (bool, optional): If True, writes all elements of each inner list
                                     as a row (debug mode). Defaults to False.
    """

    with open(csv_file, "w", encoding="utf-8") as f:
        writer = csv.writer(f)

        if debug_mode:
            # Debug mode: Write all elements as a row
            for hostname_details in hostnames:
                writer.writerow(hostname_details)
        else:
            # Ready-to-use mode: Write only the first element (hostname)
            writer.writerow("hostnames")
            for hostname_details in hostnames:
                writer.writerow([hostname_details[0]])


def main(unused_argv):
    args = parse_args()

    hostnames = []

    # We can provide not-required arguments only if "manual" parameter provided
    if args.stage != "manual" and (
        args.fw_channel or args.pool or args.pool or args.servo_state or args.dut_state
    ):
        raise ValueError(
            "You can provide additional filters only in '--stage manual' mode"
        )
    if args.stage != "manual":
        hostnames = define_stage_rollout(args)
    else:
        hostnames = define_manual_list(args)

    print(
        (
            f"Writing {len(hostnames)} DUT hostnames to "
            f"{args.stage}_{args.servo_type[0]}_list.csv and additional "
            "information to "
            f"{args.stage}_{args.servo_type[0]}_list_debug.csv"
        )
    )
    write_csv(hostnames, f"{args.stage}_{args.servo_type[0]}_list.csv")
    write_csv(hostnames, f"{args.stage}_{args.servo_type[0]}_list_debug.csv", True)
    print("Please review these lists before going forward.")
    print("To proceed with release run below command:")
    print(
        (
            f"\t./fleet_rollout.py --channel ALPHA --select from-csv "
            f"--csv-file {args.stage}_{args.servo_type[0]}_list.csv "
            f"--servo_type {args.servo_type[0]}"
        )
    )


if __name__ == "__main__":
    main(sys.argv)
    sys.exit(0)
