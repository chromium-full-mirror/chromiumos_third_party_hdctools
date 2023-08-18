#!/usr/bin/env python3
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import docker
import logging
import argparse
from datetime import datetime

DEFAULT_IMAGE = "servod:dev"
ARTIFACT_URL_TEMPLATE = "us-docker.pkg.dev/chromeos-hw-tools/servod/servod:%s"


def setup():
    client = docker.from_env()
    return client


def get_image(channel):
    if channel != "local":
        image = ARTIFACT_URL_TEMPLATE % channel
        client.images.pull(image)
        return image
    else:
        return DEFAULT_IMAGE


def start_servod(
    client,
    container_name,
    board,
    model,
    serial_no,
    image,
    other_servod_args,
    sleep=False,
    test=False,
):

    servod_params = "--port 9999 "

    if board:
        servod_params += "--board %s " % board
    if model:
        servod_params += "--model %s " % model
    if serial_no:
        servod_params.append += "--serialname %s " % model
    if other_servod_args:
        servod_params += other_servod_args
    if not container_name:
        now = datetime.now()
        container_name = now.strftime("%s")

    name = "%s-docker_servod" % container_name
    logs_volume = "%s_log" % container_name

    command = ["bash", "/start_servod_dev.sh", servod_params]
    if sleep:
        command = ["sleep", "infinity"]
    elif test:
        command = ["pytest", "-n", "auto", "/hdctools/servo/tests/"]

    cont = client.containers.run(
        image,
        remove=True,
        privileged=True,
        name=name,
        hostname=name,
        cap_add=["NET_ADMIN"],
        detach=True,
        volumes=["/dev:/dev", "%s:/var/log/servod_9999/" % logs_volume],
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
        "--container_name",
        type=str,
        help="The IP or hostname of the DUT connected to servo.",
    )
    parser.add_argument("-b", "--board", type=str, help="The board of the DUT.")
    parser.add_argument("-m", "--model", type=str, help="The model of the DUT.")
    parser.add_argument(
        "-s",
        "--serial",
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
    )
    parser.add_argument(
        "-c",
        "--channel",
        type=str,
        choices=["local", "latest", "beta", "release"],
        default="local",
        help="Run the continer but do not start servod - best for debug.",
    )
    parser.add_argument(
        "--other_servod_args",
        type=str,
        help="Any extra args to be passed to servod",
    )
    args = parser.parse_args()
    client = setup()
    image = get_image(args.channel)
    start_servod(
        client,
        args.container_name,
        args.board,
        args.model,
        args.serial,
        image,
        args.run_tests,
        args.sleep,
        args.other_servod_args,
    )
