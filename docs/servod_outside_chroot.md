# Servod Outside of Chroot

Current status: **Dogfood**

- [Servod Outside of Chroot](#servod-outside-of-chroot)
  - [Overview](#overview)
  - [Assumptions](#assumptions)
  - [How to give feedback / report issues](#how-to-give-feedback--report-issues)
  - [Install docker](#install-docker)
  - [Add your user to the tty group](#add-your-user-to-the-tty-group)
  - [Installing docker API](#installing-docker-api)
  - [Setting up your PATH](#setting-up-your-path)
  - [Quick start](#quick-start)
  - [Advanced Usage](#advanced-usage)
  - [Making changes to servod](#making-changes-to-servod)
    - [Building Servod](#building-servod)
  - [Running Tests](#running-tests)
    - [To run the same tests as the CQ does](#to-run-the-same-tests-as-the-cq-does)
  - [Forget the wrappers just let me into the container](#forget-the-wrappers-just-let-me-into-the-container)
  - [FAQ](#faq)
    - [When I run dut-control -- XXX I get a message like “More than one container matches …“](#when-i-run-dut-control----xxx-i-get-a-message-like-more-than-one-container-matches-)
    - [I want to flash firmware - how do I do that ?](#i-want-to-flash-firmware---how-do-i-do-that-)
    - [I want to run TAST/FAFT tests locally - how do I do that ?](#i-want-to-run-tastfaft-tests-locally---how-do-i-do-that-)
    - [Some tests fail with OSError - No space on device or similar - how to fix](#some-tests-fail-with-oserror---no-space-on-device-or-similar---how-to-fix)
    - [I am getting docker.errors.DockerException: Error while fetching server API version: ('Connection aborted.', PermissionError(13, 'Permission denied'))](#i-am-getting-dockererrorsdockerexception-error-while-fetching-server-api-version-connection-aborted-permissionerror13-permission-denied)
    - [Can I use podman instead of docker ?](#can-i-use-podman-instead-of-docker-)
    - [When do I know a new release has occurred ?](#when-do-i-know-a-new-release-has-occurred-)
    - [Is this available for ARM based hosts ?](#is-this-available-for-arm-based-hosts-)

## Overview

This document is designed to explain to existing users of servod inside of the
ChromeOS SDK chroot how to use servod whilst operating outside of the chroot.
For most users it should also provide a way to use servod without building any
code. Unless you are changing code in servod you should be able to just run from
a pre-built docker image.

## Assumptions

This document assumes you:

- Have followed the ChromiumOS developer guide
[link](https://chromium.googlesource.com/chromiumos/docs/+/HEAD/developer_guide.md)
at least up to the “Getting the source code section”

- Are running a linux x86 distribution that supports docker engine.

## How to give feedback / report issues

- Googlers please file feedback at <http://go/file-hwtools-bug>
- Non-Googlers please email your feedback to <cros-servod-outside-chroot-external@google.com>
this feedback will only been seen by Google and we will reach out to you directly if we
need any further information or to update you with progress.

## Install docker

**Googlers:**

Follow the instructions for **Installation**, **Sudoless Docker** And **GCR
credential helper** at [link](http://go/docker)

**Non-Googlers:**

Follow the instructions for your distribution to install docker engine at
[link](https://docs.docker.com/engine/install/)

Also complete the post installation step to have "Manage Docker as a non-root user"
setup [link](https://docs.docker.com/engine/install/linux-postinstall/)

## Add your user to the tty group

The serial devices created by the docker container are owned by root - outside of the
container the host will get a permission denied error if they try to access these
devices

```text
picocom /dev/pts/36
FATAL: cannot open /dev/pts/36: Permission denied
```

To solve this issue add your user into the tty group

```text
sudo usermod -aG tty $USER
```

You may need to reboot your host for this change to take effect.

## Installing docker API

```text
sudo apt install python3-docker
```

Some users have reported that apt install did not correctly install the docker
API module. To check if you run the command:

```text
echo "import docker" | python3
```

And you see an error like:

```text
Traceback (most recent call last): File "<stdin>",
line 1, in <module> ModuleNotFoundError: No module named 'docker'
```

You may have to install via pip:

```text
pip install --user docker --break-system-packages docker
```

## Setting up your PATH

```text
export PATH=~/chromiumos/src/third_party/hdctools/scripts:$PATH
```

To set it for every session you can also add this line at the end of yours shell
configuration, like .bashrc (NOTE: make sure you use proper path to chromiumos in your
setup):

```text
echo "export PATH=~/chromiumos/src/third_party/hdctools/scripts:\$PATH" >> ~/.bashrc
```

## Quick start

If you just need servod running for some simple dut-control commands there is no
need to build anything. Assuming you just have one servo attached to your machine
you can run:

```text
start-servod --channel=release --board=<board name>
```

This will run the current released version of servod - typically from a branch cut
2-4 weeks ago. This is the version Satlab and most ChromeOS development and testing
partners, are running.

There is also --**channel=latest**, which is a docker image that is rebuilt when
a new CL lands in the main branch of hdctools. Typically there is about a 20 min
lag from the submit to the image being ready to use. It is going to be pretty
close to ToT but is not guaranteed to be as builds may finish out of order.

It is not necessary - but **strongly** recommended that you provide a board and
model parameter to your start-servod. **Some servod functionality may not
work without the board and model being passed in.**

With a running servod can then just run dut-control commands like

```text
dut-control -- servo_type
servo_type:ccd_cr50
```

servodtool commands are also available:

```text
servodtool -- instance wait-for-active -p 9999
Instance associated with id 9999 ready.
```

When you are finished running commands you can stop servod with:

 ```text
 stop-servod
 ```

## Advanced Usage

```text
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
```

```text
dut-control

    [-n CONTAINER_NAME]
        If you are running multiple servod containers use this to address a
        specific instance.

    --
        Everything after the -- is passed to the dut-control command in
        the container.

Example:   dut-control -- servo_type
servo_type:ccd_cr50

Note the exit code for the wrapper script is set to be the exit code of the dut-control command.
```

```text
servodtool

    [-n CONTAINER_NAME]
        If you are running multiple servod containers use this to address a
        specific instance.

    --
        Everything after the -- is passed to the servodtool command in
        the container.

Example:   servodtool -- instance
servo_type:ccd_cr50

Note the exit code for the wrapper script is set to be the exit code of the dut-control command.
```

```text
servod-ps

   Shows a list of the servod containers currently running

Example:   servod-ps

Name                      Image      Board   Model     Servo Serial               Port
1700772381-docker_servod  dev        brya    banshee   SERVOV4P1-C-2306151088     9997
```

## Making changes to servod

### Building Servod

Any changes you have locally can be built by running the command

```text
build-servod
```

## Running Tests

### To run the same tests as the CQ does

Note the tests run in the build docker image - so if you make changes to the
code you need to run build-servod then run-servod-tests

```text
run-servod-tests
```

## Forget the wrappers just let me into the container

You can see a list of the running containers by running the command:

```text
servod-ps

Name                      Image      Board   Model     Servo Serial               Port
1700772381-docker_servod  dev        brya    banshee   SERVOV4P1-C-2306151088     9997

```

Containers are always named - if you do not supply a name then a timestamp is
used - so in this case the containers are named 1692829089 and 1692827271.

The built in wrapper scripts append the -docker_servod on any docker command
to namespace the servo containers distinctly from any other container you may be
running.

Entering a container so you can run commands can be done with the command:

```text
docker exec -it <name> bash

Example: docker exec -it 1700772381-docker_servod bash
```

In particular if you use the:

```text
start-servod --sleep
```

option, which just starts the container and executes sleep infinity, you can enter
the container and start servod or run servo\_updater with whatever arguments you wish.

## FAQ

### When I run dut-control -- XXX I get a message like “More than one container matches …“

Likely you have started two or more servod containers without giving them names,
by default a timestamp is used for the container name if it is not provided.

You can see a list of the running containers by running the command:

```text
servod-ps

Name                      Image      Board   Model     Servo Serial               Port
1700772381-docker_servod  dev        brya    banshee   SERVOV4P1-C-2306151088     9997
1700778745-docker_servod  release    puff    wyvern    SERVOV4P1-C-2306153023     None
```

Then you can stop one a container by running

```text
stop-servod  -n 1700778745
```

Until you have only one servod container running. If you wish to have multiple
containers it is best to explicitly name them with the -n parameter.

### I want to flash firmware - how do I do that ?

Start your servod container with the directory with the firmware to flash
mounted so something like:

```text
start-servod --channel=release --mount=$HOME/firmware_build_output:/tmp/firmware_to_flash -n flashing_servod
```

You then have to enter the docker container ( since you named it we do not need
to do a docker ps )

```text
docker exec -it flashing_servod-docker_servod bash
```

You should then see your firmware directory in /tmp/firmware\_to\_flash and
should be able to use flash\_ec or any any other normal firmware

flashing commands.

### I want to run TAST/FAFT tests locally - how do I do that ?

Start your servod container with -p [PORT] parameter, which would map internal XML RPC
port to specific port number on the host. Then you should be able to run TAST or FAFT
tests as usual.

```text
tast run -var=servo=localhost:<PORT> <DUT_IP> example.ServoEcho
```

or

```text
test_that --autotest_dir <TESTS_PATH> --board=<BOARD> <DUT_IP> --args "servo_host=localhost servo_port=<PORT>" f:.*firmware_ConsecutiveBoot/control
```

### Some tests fail with OSError - No space on device or similar - how to fix

You need to change the device limit on number of pty’s

```text
sudo bash -c 'echo "kernel.pty.max = 8096" >> /etc/sysctl.conf'
sudo sysctl -p
```

You should be able to check the setting has been applied by running

```text
cat /proc/sys/kernel/pty/max 5120
```

### I am getting docker.errors.DockerException: Error while fetching server API version: ('Connection aborted.', PermissionError(13, 'Permission denied'))

Most likely your sudoless configuration of docker has not worked. Please review
this section of the docker installation. The documentation says that a login/logout is
sufficient for the changes to take effect, however experience has shown that reboot is
often required.

To validate your docker is setup correctly you should be able to run the command:

```text
docker run -it hello-world
```

With no errors and see an output similar to this:

```text
Hello from Docker!
This message shows that your installation appears to be working correctly.

To generate this message, Docker took the following steps:
 1. The Docker client contacted the Docker daemon.
 2. The Docker daemon pulled the "hello-world" image from the Docker Hub.
    (amd64)
 3. The Docker daemon created a new container from that image which runs the
    executable that produces the output you are currently reading.
 4. The Docker daemon streamed that output to the Docker client, which sent it
    to your terminal.

To try something more ambitious, you can run an Ubuntu container with:
 $ docker run -it ubuntu bash

Share images, automate workflows, and more with a free Docker ID:
 https://hub.docker.com/

For more examples and ideas, visit:
 https://docs.docker.com/get-started/

```

If you see error messages please go through the instructions for sudoless docker again.

### Can I use podman instead of docker ?

At this time no.  The scripts rely on the docker api and Satlab/partners are using
docker.  If there is enough demand for podman we can suggest porting over but I do not
think we can support/test multiple container engines simultaneously.

Rootless docker also does not work at this time. Quick experiments have shown that you
quickly run into permission issues with devices.

### When do I know a new release has occurred ?

There is a google group [link](https://groups.google.com/a/google.com/g/chromeos-servo-announce-external) for release notes and announcements are made there.

For non Googlers you will will need to email a request to <chromeos-servo-announce-external+subscribe@google.com> to join the group.

Google groups will reply to your request and you will have to reply back to
confirm your subscription.  The web UI does not work for external users.

A release branch is cut once per month at the start of the month.  A post to the group
with release notes and a new image tagged as beta - users have about a 2 week time frame
to ensure the new release is functioning for their fleet/CI.

If no bugs are filed in that two week period then the image will be marked as release
and an announcement to that effect sent to the group.

### Is this available for ARM based hosts ?

At this time we have some experimental ARM builds but they are not ready for dogfood.

Please file a feature request with your use case for running on ARM as this makes it
more likely that the ARM project will be prioritized.
