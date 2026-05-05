#!/usr/bin/env python3
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
from datetime import datetime
from datetime import timezone
import logging
import os
import re
import shlex
import signal
import sys
import tempfile
import threading

import docker
import run_command


DEFAULT_IMAGE = "servod:dev"
ARTIFACT_URL_TEMPLATE = "us-docker.pkg.dev/chromeos-hw-tools/servod/servod:%s"
UPDATE_CHECKER_FILE = os.path.join(tempfile.gettempdir(), "start-servod-timestamp")


FW_WARNING_STRING_FMT = (
    "Servo device(s) connected to your setup uses "
    "older/newer FW than stable version for this servod "
    "channel.\nIf it is not expected please update your "
    "device(s) immediately."
    "\nYou can use following command after stopping servod:"
    "\n\nservo_updater --updater_channel %s -- "
    "-b %s\n"
)

signal.signal(signal.SIGINT, signal.default_int_handler)

HELP_MESSAGE = """
start-servod

    [-c {local,latest,fission-latest,beta,release}]
       local, image built on this machine.
       latest, a close to ToT build, may have bugs
       beta, used for short period of time to test next release
       release, latest release version, typically 2-4 weeks behind,
                used by Satlab and most partners has significantly more testing.

    [--docker-label label]
        Like -c, but allows specifying any valid docker label.

    [-b BOARD | --noboard]
       DUT board the servo is connected to. If not provided, must use --noboard flag.

    [-m MODEL | --nomodel]
       DUT model the servo is connected to. If not provided, must use --nomodel flag.

    [-s SERIAL]
       Servo serial number you want to connect to.

    [-n CONTAINER_NAME]
       Name to give your container, not required but useful if you are running
       multiple containers.

    [-t | --run_tests | --no-run_tests]
       Run the e2e tests rather than run servod.

    [-d | --sleep | --no-sleep]
       Run/setup the container but execute sleep infinity, useful in advanced use
       cases like running commands inside docker container without servod
       running in it.

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

    [-v | --verbose]
        Verbose output. Instead of printing pluses, all output of docker library is
        printed. Allows to verify the reason of long start times.

    [--debug]
        Enable debug logging for servod and the gRPC data service.

    [--allow_offline]
        Every time you run start-servod the code will check for a newer version of the
        servod docker image.   If you are not connected to the internet this check will
        fail with an error.

        This option suppresses that error and allows the servod to start with whatever
        version of the image is cached to the disk.  If there is no cached version the
        script will still fail with an access error.

    [--force_update]
        Force checking if there is an update to docker image. By default, the check
        is done only once a day for release channel, and every time for other ones.

    [--token_db token_db_path]
        Path to tokens database on the host machine. Path specified will be mounted
        to the docker container and used by servod.

    [--logs logs_dir]
        ABSOLUTE path to the directory where servod logs should be stored on the host
        machine. Use this to get easy access to the logs instead of searching for
        docker volume.
        You can use "`pwd`/servod_logs" to mount directory in current path. Servod will
        create subdirectory with the container name to make sure to never overwrite
        existing log files.
        Note: files and directories created by docker will be owned by root user.
"""


class StartServodException(Exception):
    pass


def setup():
    error_message = """

        start-servod is not able to communicate with your docker service.

        Often a reboot of the machine can fix this but you may also need
        to change the file permissions on the docker socket.
        Also check your user is in the docker group.
        If a reboot does not fix the problem try uninstall/ re-install of
        docker.
    """
    try:
        return docker.from_env()
    except docker.errors.DockerException as e:
        raise StartServodException(error_message) from e


def needs_update_check():
    if os.path.exists(UPDATE_CHECKER_FILE) is False:
        return True

    with open(UPDATE_CHECKER_FILE, "r", encoding="utf-8") as file:
        date = file.read().strip()
        current_date = datetime.now().strftime("%Y-%m-%d")
        if date == current_date:
            return False
        return True


def update_check_timestamp():
    with open(UPDATE_CHECKER_FILE, "w", encoding="utf-8") as file:
        current_date = datetime.now().strftime("%Y-%m-%d")
        file.write(current_date)


def pull_newest_image(client, image, allow_offline, verbose):
    try:
        resp = client.api.pull(image, stream=True, decode=True)
        for unused_update in resp:
            if verbose:
                print("+ {}".format(unused_update))
            else:
                print("+", end="", flush=True)
        print("", flush=True)
        return True
    except (docker.errors.APIError, docker.errors.DockerException) as e:
        if client.images.list(filters={"reference": image}):
            print("\nWarning: Failed to pull newest image, using local version.\n")
            return False

        if isinstance(e, docker.errors.APIError) and (
            e.is_server_error()
            and e.response is not None
            and str(e.response.content).find("unauthorized") > 0
        ):
            print(
                "!!!\nUnexpected authentication failure. Please try running: \n"
                "\ngcloud auth login\n\n"
                "Refresh the credentials and try again.\n"
                "More reading: https://chromium.googlesource.com/chromiumos/"
                "third_party/hdctools/+/main/docs/servod_outside_chroot.md#start_servod"
                "-sent-me-here-after-authenticating-with-the-registry-failed"
            )
            sys.exit(1)
        if not allow_offline:
            raise
        print("Failed to check for new version, offline mode specified.")


def get_image(client, channel, allow_offline, force_update, verbose):
    if channel == "local":
        if client.images.list(filters={"reference": DEFAULT_IMAGE}):
            return DEFAULT_IMAGE
        print(
            "\nWARNING:  local image requested but not available, "
            "using release image.\n"
        )
        channel = "release"
    image = ARTIFACT_URL_TEMPLATE % channel
    if (
        channel != "release"
        or force_update is True
        or needs_update_check()
        or len(client.images.list(filters={"reference": image})) == 0
    ):
        logging.info(
            "Checking docker image is up to date and downloading updates as necessary."
        )
        is_updated = pull_newest_image(client, image, allow_offline, verbose)
        logging.info("Image check complete.")

        if is_updated and channel == "release":
            update_check_timestamp()
    else:
        logging.info("Docker image version verified earlier today, no updates needed.")
    return image


def output_logs(log_lines):
    for line in log_lines:
        print(line.decode("utf-8"), end="")


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
    token_db,
    logs_dir,
    noboard,
    nomodel,
    dump_xml,
    debug,
):
    try:
        # Just in case someone manages to press ctrl-c before the container object
        # is created.
        cont = None

        servod_params = "--port 9999 "

        if board:
            servod_params += "--board %s " % board
        if model:
            servod_params += "--model %s " % model
        if serial_no:
            servod_params += "--serialname %s " % serial_no
        if noboard:
            servod_params += "--noboard "
        if nomodel:
            servod_params += "--nomodel "
        if debug:
            servod_params += "--debug "

        volumes = ["/dev:/dev", "/sys:/sys"]

        if dump_xml:
            abs_dump_xml = os.path.abspath(dump_xml)
            if os.path.isdir(abs_dump_xml) or dump_xml.endswith(os.sep):
                dir_path = abs_dump_xml
                new_file_path = "/tmp/dump_xml/"
            else:
                dir_path = os.path.dirname(abs_dump_xml)
                new_file_path = f"/tmp/dump_xml/{os.path.basename(abs_dump_xml)}"

            volumes.append(f"{dir_path}:/tmp/dump_xml/")
            servod_params += f"--dump-xml {new_file_path} "

        if passthrough_args:
            # argparse often leaves '--' in the remainder list if the user used it.
            # `servod` itself does not take '--' as an argument.
            filtered_args = [a for a in passthrough_args if a != "--"]
            servod_params += str.join(" ", filtered_args) + " "
        if not container_name:
            now = datetime.now()
            container_name = now.strftime("%s")

        env = {}
        if noboard:
            env["NOBOARD"] = "1"
        if dump_xml:
            env["DUMP_XML"] = new_file_path

        name = "%s-docker_servod" % container_name
        if os.path.exists("/proc/modules"):
            volumes.append("/proc/modules:/host_proc_modules:ro")

        if logs_dir is None:
            logs_volume = "%s_log" % container_name
        else:
            if logs_dir.startswith("/") is False:
                # We can't use CWD here, because this script is ran by bootstrap that
                # has its own CWD in the container, not on the host.
                print("Please provide --logs argument as absolute path")
                sys.exit(1)
            timestamp = container_name.split("_")[-1]
            log_dir_name = "servod_%s_%s" % (port if port else "9999", timestamp)
            logs_volume = os.path.join(logs_dir, log_dir_name)

        # Mount the host log directory to the container's log directory.
        # Inside the container, port is always 9999 as mapped by Docker.
        volumes += ["%s:/var/log/servod_9999/" % logs_volume]

        if token_db:
            dir_path = os.path.dirname(token_db)
            new_file_path = f"/tmp/token_db/{os.path.basename(token_db)}"
            volumes.append(f"{dir_path}:/tmp/token_db/")
            servod_params += f"--token-db {new_file_path}"

        command = ["bash", "/start_servod_dev.sh", servod_params]
        if sleep:
            command = ["sleep", "infinity"]
        elif test:
            command = ["pytest", "-n", "auto", "--forked", "/hdctools/"]
            if passthrough_args:
                command += passthrough_args

        # This variable is set by bootstrap script. If bootstrap is no more,
        # revert commit done for b:400921593
        _servodrc = os.environ["SERVODRC"] if "SERVODRC" in os.environ else ""
        if len(_servodrc) > 0:
            volumes.append(f"{_servodrc}:/root/.servodrc:ro")

        if mounts:
            for mount in mounts:
                volumes.append("".join(mount))
        ports = {}
        if port:
            ports = {"9999": port}

        logging.info("Container run")
        nofile_limit = docker.types.Ulimit(name="nofile", soft=65535, hard=65535)
        logging.debug("Running command %s", shlex.join(command))
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
            environment=env,
            ulimits=[nofile_limit],
        )
        started = False
        log_lines = cont.logs(stream=True, follow=True)
        output_thread = None
        if not test and not sleep:
            if not (sleep or test) and follow:
                output_thread = threading.Thread(target=output_logs, args=(log_lines,))
                output_thread.start()
            else:
                print("Starting ", end="", flush=True)
            while not started:
                try:
                    (error_code, output) = cont.exec_run(
                        "servodtool instance wait-for-active --timeout 1 -p 9999"
                    )
                    del output  # All information necessary is in the error code.
                    print(".", end="", flush=True)
                except docker.errors.APIError:
                    for line in log_lines:
                        print(line.decode("utf-8"), end="")
                    sys.exit(2)
                if error_code == 0:
                    started = True
                    log_lines = None
                    if output_thread is not None:
                        pass
                    elif follow:
                        log_lines = cont.logs()
                        print(log_lines.decode("utf-8"))
                    else:
                        log_lines = b"\n"
                        i = 0
                        # To reduce the clutter on screens print 3 lines at the start of
                        # the servod logs ( to get a timestamp ), then three lines at
                        # the end which is typically the most relevant information.
                        for line in cont.logs(stream=True):
                            i += 1
                            if i > 3:
                                break
                            log_lines += line
                        log_lines += b"\n...............\n\n"
                        log_lines += cont.logs(tail=3)
                        print(log_lines.decode("utf-8"))
                    if port:
                        print(
                            "container port 9999 is mapped to port %s on your machine"
                            % port
                        )
                    else:
                        print(
                            "Port is NOT mapped to host machine - remote access will "
                            "not work - including commands within chroot"
                        )
                    print(
                        "\nTo stop this container: $ stop-servod --container_name %s"
                        % container_name,
                        end="",
                    )
                    if follow:
                        print(" or press CTRL+C", end="")
                    print("\n")
                    (error_code, output) = cont.exec_run(
                        "dut-control ec_uart_pty cpu_uart_pty gsc_uart_pty"
                    )
                    print("Main console locations:\n{}".format(output.decode("utf-8")))
                    # Verify connected servos FW version, print warning if update needed
                    for servo_type in (
                        "servo_v4",
                        "servo_v4p1",
                        "c2d2",
                        "servo_micro",
                    ):
                        (exit_code, output) = cont.exec_run(
                            f"dut-control {servo_type}_firmware_uptodate"
                        )
                        del exit_code  # No need to check exit code.
                        regex_fw_uptodate = re.match(
                            rf"{servo_type}_firmware_uptodate:(yes|no)",
                            output.decode("utf-8"),
                        )
                        if not regex_fw_uptodate:
                            continue
                        if regex_fw_uptodate.group(1) == "no":
                            regex_servod_channel = re.match(
                                r".*:(dev|beta|release|latest|fission-latest)", image
                            )
                            if regex_servod_channel:
                                channel = regex_servod_channel.group(1)
                                if channel == "dev":
                                    channel = "local"
                                print("================Warning================")
                                print(FW_WARNING_STRING_FMT % (channel, servo_type))
                                if not follow:
                                    print(
                                        "You can find more details in servod log"
                                        "(e.g use start-servod with -f flag)"
                                    )
                                print("================Warning================")
                                # It is enough to print this warning only once in
                                # all cases
                                break

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
            output_thread.join()
    except KeyboardInterrupt:
        while cont:
            try:
                cont.reload()
                if cont.status in ["created", "running"]:
                    cont.kill()
                cont = None
            except KeyboardInterrupt:
                pass  # Sometimes multiple ctrl-c are received.
            except docker.errors.APIError:
                pass  # Sometimes we try to kill a container that is shutting down.
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
        choices=["local", "latest", "beta", "release", "fission-latest"],
        default="local",
    )
    parser.add_argument(
        "--docker-label",
        type=str,
        dest="channel",
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
        "-v",
        "--verbose",
        action=argparse.BooleanOptionalAction,
    )
    parser.add_argument(
        "--mount",
        type=str,
        action="append",
        nargs="*",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        help="Host port number to map the servod service to",
    )
    parser.add_argument(
        "passthrough", nargs=argparse.REMAINDER, help="Arguments for subcommand"
    )
    parser.add_argument(
        "--debug",
        action=argparse.BooleanOptionalAction,
    )
    parser.add_argument(
        "--allow_offline",
        action=argparse.BooleanOptionalAction,
    )
    parser.add_argument(
        "--force_update",
        action=argparse.BooleanOptionalAction,
    )
    parser.add_argument(
        "--token_db",
        type=str,
        dest="token_db",
    )
    parser.add_argument(
        "--logs",
        type=str,
        default="/tmp/servod_logs",
        dest="logs_dir",
    )
    parser.add_argument(
        "--dump-xml",
        type=str,
        dest="dump_xml",
    )
    parser.add_argument(
        "--noboard",
        action=argparse.BooleanOptionalAction,
    )
    parser.add_argument(
        "--nomodel",
        action=argparse.BooleanOptionalAction,
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


class UTCFormatter(logging.Formatter):
    """A formatter that always prints dates in UTC in ISO-8601 format."""

    def formatTime(self, record, datefmt=None):
        return datetime.fromtimestamp(record.created, timezone.utc).isoformat(
            timespec="milliseconds"
        )


def main():
    default_handler = logging.StreamHandler(sys.stdout)
    default_handler.formatter = UTCFormatter(fmt="%(asctime)s %(message)s")
    logging.basicConfig(
        level=logging.INFO,
        handlers=[default_handler],
    )
    logging.info("Setup.")
    client = setup()
    args = parse_args()

    # Re-map fission-latest to latest as requested
    if args.channel == "fission-latest":
        args.channel = "latest"

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    image = get_image(
        client, args.channel, args.allow_offline, args.force_update, args.verbose
    )
    logging.info("Starting the server.")
    start_servod(
        client=client,
        container_name=args.container_name,
        board=args.board,
        model=args.model,
        serial_no=args.serial,
        image=image,
        mounts=args.mount,
        port=args.port,
        passthrough_args=args.passthrough,
        sleep=args.sleep,
        test=args.run_tests,
        follow=args.follow,
        token_db=args.token_db,
        logs_dir=args.logs_dir,
        noboard=args.noboard,
        nomodel=args.nomodel,
        dump_xml=args.dump_xml,
        debug=args.debug,
    )


if __name__ == "__main__":
    main()
