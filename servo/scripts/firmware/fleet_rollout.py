#!/usr/bin/python3
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import json
import subprocess
import sys


ALL_QUERY = """
    SELECT DISTINCT hostname
    FROM chrome_fleet_analytics.cros_fleet.dut_info_archive
    WHERE LEFT(servo_type_raw, %d) = '%s'
    AND RIGHT(board, 10) != 'labstation'
    AND TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), timestamp, DAY) < 1
    GROUP BY hostname;
"""


def run_command(command):
    """Run a command in the shell

    Args:
        command (string): The command to run

    Returns:
        CompletedProcess: All the information about the command execution.
    """

    return subprocess.run(command, stdout=subprocess.PIPE, check=True)


def get_hostnames(all_servo_type=False):
    """Query the UFS a list of DUT hostnames.

    By default it returns a list based on the custom plx table
    chromeos_hardware_tools.FW_ROLLOUT_CONNECTED which is populated by the contents of
    a google sheet.  This allows careful control of DUT's affected.

    If all_servo_type is specified all DUT's in the fleet that have been seen in the
    last 1 day is returned.

    Args:
        all_servo_type (bool, optional): Query the full list of DUT's.
                                         Defaults to False.

    Returns:
        list[string]: Fleet DUT hostnames, either in the collated list or the full list
                      of active fleet DUT's
    """
    query = "SELECT * FROM chromeos_hardware_tools.FW_ROLLOUT_CONNECTED;"
    if all_servo_type:
        query = ALL_QUERY % (len(all_servo_type), all_servo_type)
    ps = subprocess.Popen(["echo", query], stdout=subprocess.PIPE)
    hostnames = (
        subprocess.check_output(
            ("f1-sql", "--csv_output"), stdin=ps.stdout, stderr=subprocess.DEVNULL
        )
        .strip()
        .split(b"\n")
    )
    return [hostname.strip(b'\r\n"').decode("utf-8") for hostname in hostnames]


def get_servo_data(data):
    """Get just the servo data from a shivas dut get --json query.

    To get all of the servo information from shivas you need to get all the information
    about a DUT and pick out just the servo data from that shivas json structure.

    Args:
        data (dict): Dictionary of information about a DUT from shivas.

    Returns:
        dict: Dictionary of information about the servo attached to a DUT, or None if
              that information is missing.
    """
    try:
        return data["chromeosMachineLse"]["deviceLse"]["dut"]["peripherals"]["servo"]
    except KeyError:
        return None


def get_hostname(data):
    """Extract the hostname from the shivas return data.

    Args:
        data (dict): Dictionary of information about a DUT from shivas.

    Returns:
        string: the hostname of the DUT
    """
    return data["hostname"]


def get_all_dut_info(hostnames):
    """Query shivas for DUT data and refine down the to the data required.

    Args:
        hostnames (list): A list of dut hostname strings.

    Returns:
        dict: A dictionary of dut_hostname string to a dict of information about the
              attached servo.
    """

    command = ["shivas", "get", "dut", "-json"] + hostnames
    ps = run_command(command)
    data = json.loads(ps.stdout)
    return {get_hostname(data): get_servo_data(data) for data in data}


def get_servo_fw_channel(data):
    """Extract the current firmware channel from the servo data.

    Args:
        data (dict): Dictionary of information about a DUT from shivas.

    Returns:
        string: the current firmware channel of the servo.
    """
    try:
        return data["servoFwChannel"]
    except IndexError:
        return "UNKNOWN"


def get_servo_fw_version(data):
    """Extract the current firmware version from the servo data.

    Args:
        data (dict): Dictionary of information about a DUT from shivas.

    Returns:
        string: the current firmware version of the servo.
    """
    try:
        return data["servoTopology"]["main"]["fwVersion"]
    except TypeError:
        return "UNKNOWN"


def update_channel(hostnames, channel):
    """Execute shivas command to update the firmware channel for hostnames.

    Although it is faster to call shivas with a list of hostnames, it is not possible
    to get/parse the error messages and relate them to a hostname, so do it one by one.

    Args:
        hostnames (list(string)): List of DUT hostnames to update the firmware channel.
        channel (string): The channel to update to.
    """
    print("Updating channels - this might take some time...")
    for hostname in hostnames:
        command = [
            "/usr/local/bin/shivas",
            "update",
            "dut",
            "-name",
            "%s" % hostname,
            "-servo-fw-channel",
            "%s" % channel,
        ]
        print(".", end="", flush=True)
        run_command(command)
    print("Done.")


def request_repair(hostnames):
    """Call the command to request shivas repair a list of DUT's

    We do this as one command as it is much faster to call shivas this way versus
    calling a shivas one time for each hostname.

    Args:
        hostnames (list(string)): List of hostnames to ask shivas to repair.
    """
    command = ["/usr/local/bin/shivas", "repair", "%s"] + hostnames
    print("Requesting the repairs - this might take some time....")
    run_command(command)
    print("Done with repairs")


def is_firmware_channel_update_required(hostname, channel, data):
    """_summary_

    Args:
        hostname (string): hostname of the DUT.
        channel (string): expected servo firmware channel of the DUT.
        data (dict): Dictionary of information about a DUT from shivas.

    Returns:
        bool: False if the channel is correct otherwise True
    """
    if get_servo_fw_channel(data).split("_")[-1:][0] == channel:
        print("Skipping", hostname)
        return False
    return True


def update_servo_firmware(hostnames, channel):
    """_summary_

    Args:
        hostname (string): hostname of the DUT.
        channel (string): servo firmware channel to of the DUT.
    """
    update_channel(hostnames, channel)
    request_repair(hostnames)


def print_servo_firmware_status(hostname, data):
    """_summary_

    Args:
        hostname (string): hostname of the DUT.
        data (dict): Dictionary of information about a DUT from shivas.
    """
    try:
        print(
            "%s,%s,%s"
            % (
                hostname,
                get_servo_fw_channel(data),
                get_servo_fw_version(data),
            )
        )
    except Exception:
        print("Unable to get all data from", hostname)


def parse_args():
    """Parse the command line args

    Returns:
        argparse.Namespace: Parsed arguments.
    """
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument(
        "--channel",
        required=False,
        choices=["ALPHA", "BETA", "DEV", "STABLE"],
        help="What FW channel to update to.",
    )
    parser.add_argument(
        "--repair_if_not_updated",
        required=False,
        type=str,
        help=(
            "Run repair on devices if they firmware does not match"
            " the supplied firmware version"
        ),
    )
    parser.add_argument(
        "--all",
        required=False,
        choices=["servo_v4", "servo_v4p1"],
        help="What servo to update",
    )
    return parser.parse_args()


def is_run_repair_needed(hostname, fw_version, data):
    """Check to see if the firmware version is as expected.

    Args:
        hostname (string): hostname of the DUT.
        fw_version (string): expected firmware version.
        data (dict): Dictionary of information about a DUT from shivas.

    Returns:
        _type_: _description_
    """
    if get_servo_fw_version(data) == fw_version:
        print("Skipping", hostname)
        return False
    print("Repairing", hostname)
    return True


def main(unused_argv):
    """Main control logic for the fw_rollout tool.

    Tools makes it easy to:
        Change the servo fw channel of a select number of servos.
        Change the servo fw channel for all servos of a given type.
        Monitor the current fw version for a select or full list of servos.

    This tool only works for the Google Fleet ( satlab and non satlab )
    """
    args = parse_args()
    # Ensure the user has run gcert so a nice error message can be shown.
    ps = run_command(["/usr/bin/gcertstatus", "--check_remaining=1h"])
    if ps.returncode != 0:
        print("gcert is not valid please run the gcert command and try again.")
        sys.exit(1)

    # Change channel and repair are exclusive options ( change channel will call
    # repair ) validate that is user has not specified both.
    if args.channel and args.repair_if_not_updated:
        print("Can not update channel and repair only")
        sys.exit(1)

    # Retrieve all relevant data from shivas, based on a collated list of devices
    # or all of the devices for a particular servo board.
    hostnames = get_hostnames(args.all)[1:]
    data_dict = get_all_dut_info(hostnames)

    action_hostnames = []
    for hostname in data_dict.keys():
        # First time this is called all of the hostnames will be eligible to update,
        # shivas updates are not 100% reliable so at times you have to run this again
        # to find the devices that failed on the first channel update.
        if args.channel:
            if is_firmware_channel_update_required(
                hostname, args.channel, data_dict[hostname]
            ):
                action_hostnames.append(hostname)
        elif args.repair_if_not_updated:
            # When the channel is changed repair is called, repair is what will actually
            # update the firmware to the new version.  Repair jobs have a short
            # lifespan and if the DUT is busy it can timeout.  So we need to scan
            # firmware version to decide if to schedule a new repair job.
            if is_run_repair_needed(
                hostname, args.repair_if_not_updated, data_dict[hostname]
            ):
                action_hostnames.append(hostname)
        else:
            # If no action has been supplied just print status.
            print_servo_firmware_status(hostname, data_dict[hostname])
    if action_hostnames:
        if args.channel:
            update_servo_firmware(action_hostnames, args.channel)
        elif args.repair_if_not_updated:
            request_repair(action_hostnames)
    elif args.channel or args.repair_if_not_updated:
        print("No devices to perform action on")


if __name__ == "__main__":
    main(sys.argv)
    sys.exit(0)
