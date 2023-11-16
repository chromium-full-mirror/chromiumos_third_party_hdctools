#!/usr/bin/env python3
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
from datetime import datetime
import os
import signal
import sys

import docker
import run_command


DEFAULT_IMAGE = "servod:dev"
ARTIFACT_URL_TEMPLATE = "us-docker.pkg.dev/chromeos-hw-tools/servod/servod:%s"

signal.signal(signal.SIGINT, signal.default_int_handler)

HELP_MESSAGE = """
start-servod

    [-c {local,latest,beta,release}]
       local, image built on this machine.
       latest, a close to ToT build, may have bugs
       beta, used for short period of time to test next release
       release, latest release version, typically 2-4 weeks behind,
                used by Satlab and most partners has significantly more testing.

    [-b BOARD]
       DUT board the servo is connected to.  Not required but strongly suggested.

    [-m MODEL]
       DUT model the servo is connected to.  Not required.

    [-s SERIAL]
       Servo serial number you want to connect to.

    [-n CONTAINER_NAME]
       Name to give your container, not required but useful if you are running
       multiple containers.

    [-t | --run_tests | --no-run_tests]
       Run the e2e tests rather than run servod.

    [-d | --sleep | --no-sleep]
       Run/setup the container but execute sleep infinity, useful in advanced use
       cases like running servo_updater where the servod can not be running but
       the container needs to be setup.

    [--mount [MOUNT ...]]
       Mount a directory from the host to the container in the format:
             <host_directory>:<container_mount_point>

       Note multiple mount arguments are supported.

    [-p PORT]
       Map the internal XML RPC port to this port number on the host, allows for
       direct API access without having to run commands inside of the docker
       container

    [-f ]
       After the servod has started continue to follow the logs as they get generated
       rather than dropping back to the shell.  CTRL+C will exit the servod on the
       command line.

       By default -f will show the debug logs but you can specify -f=WARNING or -f=INFO
       if you wish another level of logging.
"""


def setup():
    return docker.from_env()


def get_image(client, channel):
    if channel != "local":
        image = ARTIFACT_URL_TEMPLATE % channel
        resp = client.api.pull(image, stream=True, decode=True)
        for unused_update in resp:
            print("+", end="", flush=True)
        print("", flush=True)
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
    follow,
):
    servod_params = "--port 9999 "

    if board:
        servod_params += "--board %s " % board
    if model:
        servod_params += "--model %s " % model
    if serial_no:
        servod_params += "--serialname %s " % serial_no
    if passthrough_args:
        servod_params += str.join(" ", passthrough_args)
    if not container_name:
        now = datetime.now()
        container_name = now.strftime("%s")

    name = "%s-docker_servod" % container_name
    logs_volume = "%s_log" % container_name

    command = ["bash", "/start_servod_dev.sh", servod_params]
    if sleep:
        command = ["sleep", "infinity"]
    elif test:
        command = ["pytest", "-n", "auto", "/hdctools/"]

    volumes = ["/dev:/dev", "%s:/var/log/servod_9999/" % logs_volume]

    _servodrc = os.path.join(os.path.expanduser("~"), ".servodrc")
    if os.path.isfile(_servodrc):
        volumes.append(f"{_servodrc}:/root/.servodrc:ro")

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
                sys.exit(2)
            if ec == 0:
                started = True
                log_lines = None
                if follow:
                    log_lines = cont.logs()
                else:
                    log_lines = cont.logs(tail=3)
                print(log_lines.decode("utf-8"))
                if port:
                    print(
                        "container port 9999 is mapped to port %s on your machine"
                        % port
                    )
                print(
                    "\nTo stop this container: $ stop-servod --container_name %s"
                    % container_name,
                    end="",
                )
                if follow:
                    print(" or press CTRL+C", end="")
                print("\n")
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
    elif sleep:
        print(
            "Enter the container by running the command $ docker exec -it %s bash"
            % name
        )
    if not (sleep or test) and follow:
        try:
            unused_rc, stream = cont.exec_run(
                ["tail", "-F", "-n", "0", "/var/log/servod_9999/latest.%s" % (follow,)],
                stream=True,
            )
            for data in stream:
                print(data.decode(), end="")
        except KeyboardInterrupt:
            cont.kill()
            sys.exit(1)


def parse_args():
    parser = run_command.CustomArgHelpParser(message=HELP_MESSAGE)
    parser.add_argument(
        "-n",
        "--container_name",
        type=str,
        help="The IP or hostname of the DUT connected to servo.",
    )
    parser.add_argument("-b", "--board", type=str)
    parser.add_argument("-m", "--model", type=str)
    parser.add_argument(
        "-s",
        "--serial",
        type=str,
    )
    parser.add_argument(
        "-t",
        "--run_tests",
        action=argparse.BooleanOptionalAction,
    )
    parser.add_argument(
        "-d",
        "--sleep",
        action=argparse.BooleanOptionalAction,
    )
    parser.add_argument(
        "-c",
        "--channel",
        type=str,
        choices=["local", "latest", "beta", "release"],
        default="local",
    )
    parser.add_argument(
        "-f",
        "--follow",
        type=str,
        choices=["INFO", "WARNING", "DEBUG"],
        nargs="?",
        const="DEBUG",
    )
    parser.add_argument(
        "--mount",
        type=str,
        action="append",
        nargs="*",
    )
    parser.add_argument(
        "-p", "--port", type=int, help="Host port number to map the servod service to"
    )
    parser.add_argument(
        "passthrough", nargs=argparse.REMAINDER, help="Arguments for subcommand"
    )
    args = parser.parse_args()
    if args.help:
        parser.print_usage()
        sys.exit(4)
    if args.passthrough and args.passthrough[0] != "--":
        print(
            (
                "Error - unknown arguments '%s' - if you want to pass through"
                " arguments use the -- separator"
            )
            % " ".join(args.passthrough)
        )
        sys.exit(3)
    return args


def main():
    client = setup()
    args = parse_args()
    print("Checking docker image is up to date and downloading updates as necessary.")
    image = get_image(client, args.channel)
    print("\nStarting the server.\n")
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
        follow=args.follow,
    )


if __name__ == "__main__":
    main()
