#!/usr/bin/env python3
# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import json
import sys

import docker


FORMAT_STR = "{0:<25} {1:<10} {2:<15} {3:<15} {4:<26} {5:<5}"


def parse_args(arguments):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-b", "--board", type=str, default="Unspecified")
    parser.add_argument("-m", "--model", type=str, default="Unspecified")
    return parser.parse_known_args(arguments)[0]


def print_header():
    print()
    print(FORMAT_STR.format("Name", "Image", "Board", "Model", "Servo Serial", "Port"))


def determine_host_port(container):
    host_port = "None"
    if container.ports:
        for key in container.ports.keys():
            host_port = container.ports[key][0]["HostPort"]
    return host_port


def determine_root_serial(container):
    root_serial = "Unknown"
    exit_code, output = container.exec_run("dut-control serialnames")
    if exit_code == 0:
        output = output.replace(b"serialnames", b'"serialnames"')
        serial_data = json.loads("{%s}" % output.decode("utf-8"))
        root_serial = serial_data["serialnames"]["root"]
    return root_serial


def print_line(container):
    container_args = container.attrs["Args"]
    if len(container_args) > 1:
        container_args = container_args[1].split(" ")
    servod_cmd_args = parse_args(container_args)
    root_serial = determine_root_serial(container)
    host_port = determine_host_port(container)
    image = "Unknown"
    try:
        container.image.tags[0].split(":")[1],
    except IndexError:
        pass
    print(
        FORMAT_STR.format(
            container.name,
            image,
            servod_cmd_args.board,
            servod_cmd_args.model,
            root_serial,
            host_port,
        )
    )


def main():
    client = docker.from_env()

    name_search = "docker_servod"
    containers = client.containers.list(filters={"name": name_search})
    if not containers:
        print("No containers running")
        sys.exit(1)

    print_header()

    for container in containers:
        print_line(container)


if __name__ == "__main__":
    main()
