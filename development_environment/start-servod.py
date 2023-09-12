#!/usr/bin/env python3
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
from datetime import datetime
import sys

import docker


DEFAULT_IMAGE = "servod:dev"
ARTIFACT_URL_TEMPLATE = "us-docker.pkg.dev/chromeos-hw-tools/servod/servod:%s"


def setup():
    return docker.from_env()


def get_image(client, channel):
    if channel != "local":
        image = ARTIFACT_URL_TEMPLATE % channel
        client.images.pull(image)
        return image
    return DEFAULT_IMAGE


def start_servod(
    client,
    container_name,
    board,
    model,
    serial_no,
    image,
    mounts,
    port,
    passthrough_args,
    sleep,
    test,
):
    servod_params = "--port 9999 "

    if board:
        servod_params += "--board %s " % board
    if model:
        servod_params += "--model %s " % model
    if serial_no:
        servod_params += "--serialname %s " % serial_no
    if passthrough_args:
        servod_params += passthrough_args
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
    # elif servo_upgrade:
    #    command = ["servo_updator", "-c", fw_channel, "-b", servo_board]

    volumes = ["/dev:/dev", "%s:/var/log/servod_9999/" % logs_volume]
    if mounts:
        for mount in mounts:
            volumes.append("".join(mount))
    ports = {}
    if port:
        ports = {"9999": port}

    cont = client.containers.run(
        image,
        remove=True,
        privileged=True,
        name=name,
        hostname=name,
        cap_add=["NET_ADMIN"],
        detach=True,
        volumes=volumes,
        ports=ports,
        command=command,
    )
    started = False
    log_lines = cont.logs(stream=True, follow=True)
    if not test and not sleep:
        while not started:
            try:
                (ec, _unused) = cont.exec_run(
                    "servodtool instance wait-for-active --timeout 1 -p 9999"
                )
            except docker.errors.APIError:
                for line in log_lines:
                    print(line.decode("utf-8"), end="")
                sys.exit(1)
            if ec == 0:
                started = True
                log_lines = cont.logs(tail=3)
                print(log_lines.decode("utf-8"))
    elif test:
        cont.reload()
        while cont.status == "running":
            try:
                cont.reload()
            except docker.errors.APIError:
                sys.exit(0)
            else:
                for line in log_lines:
                    print(line.decode("utf-8"), end="")


def parse_args():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "-n",
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
        "--mount",
        type=str,
        action="append",
        nargs="*",
        help="Mount a host directory into the servod container in the format <hostdir>:<containerdir>.",
    )
    parser.add_argument(
        "-p", "--port", type=int, help="Host port number to map the servod service to"
    )
    parser.add_argument(
        "passthrough", nargs=argparse.REMAINDER, help="Arguments for subcommand"
    )
    return parser.parse_args()


def main():
    client = setup()
    args = parse_args()
    image = get_image(client, args.channel)
    start_servod(
        client=client,
        container_name=args.container_name,
        board=args.board,
        model=args.model,
        serial_no=args.serial,
        image=image,
        mounts=args.mount,
        port=args.port,
        passthrough_args=args.passthrough[1:],
        sleep=args.sleep,
        test=args.run_tests,
    )


if __name__ == "__main__":
    main()
