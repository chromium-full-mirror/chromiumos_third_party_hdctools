# Standalone Servod

If you just need to run servod but do not need to make any changes to the servod code you can use these instructions to install it via a Debian package.

This actually only installs some wrapper scripts and dependencies that will make it simple for you to download and run the docker image that contains servod and related tooling.

**Googlers this will not work on gLinux as adding repos is disallowed**

- [Standalone Servod](#standalone-servod)
  - [Install Pre-Requisites](#install-pre-requisites)
  - [Setup Google Cloud, Docker and Google HW Tools Repositories](#setup-google-cloud-docker-and-google-hw-tools-repositories)
  - [Install Servod](#install-servod)
  - [Allow use of docker without sudo](#allow-use-of-docker-without-sudo)
  - [Example usage](#example-usage)
  - [Advanced Usage](#advanced-usage)

## Install Pre-Requisites

```text
sudo apt-get install apt-transport-https ca-certificates gnupg curl sudo
```

## Setup Google Cloud, Docker and Google HW Tools Repositories

```text
curl  https://us-apt.pkg.dev/doc/repo-signing-key.gpg |sudo gpg --dearmor -o /etc/apt/keyrings/hwtools.gpg
curl  https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

echo "deb [signed-by=/etc/apt/keyrings/hwtools.gpg] https://us-apt.pkg.dev/projects/chromeos-hw-tools servod-deb main" | sudo tee -a /etc/apt/sources.list.d/artifact-registry.list

echo   "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
$(. /etc/os-release && echo "$VERSION_CODENAME") stable" |   sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

```

## Install Servod

```text
sudo apt update
sudo apt install servod
```

## Allow use of docker without sudo

```text
sudo addgroup docker
sudo usermod -aG docker $USER
```

**You will now need to reboot or log out / log in to apply this group change**

## Example usage

```text
start-servod --channel=release --board=brya
Checking docker image is up to date and downloading updates as necessary.
+++

Starting the server.

2023-11-25 01:15:49,091 - DeviceWatchdog - INFO - Reinit capable device found. Polling rate set to 0.10s.
2023-11-25 01:15:49,091 - DeviceWatchdog - INFO - Watchdog setup for devices: [servo_v4p1 (18d1:520d) SERVOV4P1-C-2306151088, ccd_cr50 (18d1:5014) 1080C03D-9066B219]
2023-11-25 01:15:49,092 - servod - INFO - Listening on 0.0.0.0 port 9999


To stop this container: $ stop-servod --container_name 1700874944
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

   [--allow_offline]
      Every time you run start-servod the code will check for a newer version of the
      servod docker image.   If you are not connected to the internet this check will
      fail with an error.

      This option suppresses that error and allows the servod to start with whatever
      version of the image is cached to the disk.  If there is no cached version the
      script will still fail with an access error.
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
