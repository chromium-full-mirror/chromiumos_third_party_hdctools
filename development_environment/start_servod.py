#!/usr/bin/env python3
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import docker
import logging
import argparse

# hostname and port docker server is running on the lattice machine
DOCKER_HOST_SERVER = "127.0.1.1:2375"

IMAGE = "127.0.1.1:5000/servod:dev"


def setup():
    client = docker.from_env()
    try:
        client.images.pull(IMAGE)
    except docker.errors.APIError:
        logging.exception("Failed to pull image")
    return client


def start_servod(client, dut_hostname, board, model, serial_no, test=False, sleep=False):
    environment = [
        "BOARD=%s" % board,
        "MODEL=%s" % model,
        "SERIAL=%s" % serial_no,
        "PORT=%s" % "9999",
    ]

    name = "%s-docker_servod" % dut_hostname
    logs_volume = "%s_log" % dut_hostname

    command = ["bash", "/start_servod.sh"]
    if sleep:
      command = ["sleep", "infinity"]

    if test:
        command = ["pytest", "-n", "auto", "/hdctools/servo/tests/"]

    cont = client.containers.run(
        IMAGE,
        remove=True,
        privileged=True,
        name=name,
        hostname=name,
        cap_add=["NET_ADMIN"],
        detach=True,
        volumes=["/dev:/dev", "%s:/var/log/servod_9999/" % logs_volume],
        environment=environment,
        command=command,
    )
    log_lines = cont.logs(stream=True, follow=True)
    started = False
    while log_lines and not started:
        cont.reload()
        for line in log_lines:
            print(line.decode("utf-8").strip())
            if b"servod - INFO - Listening on 0.0.0.0 port" in line:
                started = True
                logging.info("Detected servod has started.")
                break
        if cont.status == "removing":
            break


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "-h",
        "--hostname",
        required=True,
        type=str,
        help="The IP or hostname of the DUT connected to servo.",
    )
    parser.add_argument(
        "-b", "--board", required=True, type=str, help="The board of the DUT."
    )
    parser.add_argument(
        "-m", "--model", required=True, type=str, help="The model of the DUT."
    )
    parser.add_argument(
        "-s",
        "--serial",
        required=True,
        type=str,
        help="The serial number of the servo.",
    )
    parser.add_argument(
        "-t",
        "--run_tests",
        action=argparse.BooleanOptionalAction,
        help="Run the servod tests and exist.",
    )
    parser.add_argument(
        "-d",
        "--sleep",
        action=argparse.BooleanOptionalAction,
        help="Run the continer but do not start servod - best for debug.",
    args = parser.parse_args()
    client = setup()
    start_servod(
        client, args.hostname, args.board, args.model, args.serial, args.run_tests
    )
