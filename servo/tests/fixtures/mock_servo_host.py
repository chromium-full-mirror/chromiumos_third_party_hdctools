# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

from mock import call
import pytest

from servo import servod as sd
from servo.tests.fixtures import common
from servo.tests.fixtures.mock_pyusb import clear_interfaces
from servo.tests.fixtures.mock_pyusb import dump_interfaces


_logger = logging.getLogger("mock_servod")


@pytest.fixture(scope="function")
def mock_servo_host(
    class_mocker,
    mock_pyusb,
    mock_cr50_usb_device,
    mock_v4p1_usb_device,
    mock_servo_micro_usb_device,
    mock_c2d2_usb_device,
):
    """Mock representation of a servo host - a machine that has servo USB devices.

    Servod runs on a servo host, it searches the USB devices on that host when it starts
    up.  This is a mock represntation of a host so we can feed in data about the mocked
    USB devices we have generated for the test.

    The host has a list of the USB devices attached to it, constructed by the test and
    has some helper functions to clear all the saved data in the mocked devices to enaure
    a clear run to run

    Args:
        class_mocker (_type_): Mocker module injected by pytest.
        mock_pyusb (_type_): Mock PyUSB fixture injected by pytest.
        mock_cr50_usb_device (_type_): Mock CR50 fixture injected by pytest.
        mock_v4p1_usb_device (_type_): Mock Servo 4.1 fixture injected by pytest.
        mock_servo_micro_usb_device (_type_): Mock Servo micro fixture injected by pytest.
        mock_c2d2_usb_device (_type_): Mock C2D2 fixture injected by pytest.
    """

    def generate_servo_host():
        """Mock generator function.   This allows multiple tests to be run in
        parrallel as it generates a new mock for each test vs sharing the same
        mock between tests.

        Returns:
            MockServoHost: Mock servo host, a representation of a servo host
            which is what connects a servo/ccd to servod.
        """

        class MockServoHost:
            def __init__(self):
                self._mock_usb = mock_pyusb
                self.hierarchy = {}
                self.sysfs = {}
                class_mocker.patch(
                    "servo.utils.usb_hierarchy.Hierarchy._RefreshHierarchy",
                    return_value=self.hierarchy,
                )
                class_mocker.patch(
                    "servo.utils.usb_hierarchy.Hierarchy._ReadFromSysfs",
                    side_effect=self.MockReadFromSysfs,
                )

            def MockReadFromSysfs(self, sysfs_path, dev_file, cast=str):
                return self.sysfs[sysfs_path][dev_file]

            def add_device(self, type, bus, address, dd):
                serial = common.get_servo_serial(type)
                sys_path = "/sys/bus/usb/devices/%s-%s" % (bus, dd)
                self.hierarchy[(bus, address)] = sys_path
                self.sysfs[sys_path] = {}
                self.sysfs[sys_path]["idVendor"] = common.device_details[type][
                    "idVendor"
                ]
                self.sysfs[sys_path]["idProduct"] = common.device_details[type][
                    "idProduct"
                ]
                self.sysfs[sys_path]["serial"] = serial

                device = None

                if type == "ccd_cr50":
                    device = mock_cr50_usb_device(serial, bus, address)
                elif type == "servo_v4p1":
                    device = mock_v4p1_usb_device(serial, bus, address)
                elif type == "servo_micro":
                    device = mock_servo_micro_usb_device(serial, bus, address)
                elif type == "c2d2":
                    device = mock_c2d2_usb_device(serial, bus, address)

                if device:
                    self._mock_usb.devices.append(device)
                return device

            def clear_all_interfaces(self):
                for device in self._mock_usb.devices:
                    clear_interfaces(device)

            def dump_all_interfaces(self):
                result = {}
                for device in self._mock_usb.devices:
                    result[device.iSerial] = dump_interfaces(device)
                return result

            def start(self, serial, board, model, device_discovery="min"):
                opts = [
                    "-s",
                    serial,
                    "-b",
                    board,
                    "-m",
                    model,
                    "--device-discovery",
                    device_discovery,
                ]
                self.starter = sd.ServodStarter(opts)

            def stop(self):
                if self.starter:
                    self.starter._server.server_close()
                    self.starter._servod.close()

        msd = MockServoHost()
        return msd

    return generate_servo_host


@pytest.fixture()
def mock_host_with_4p1_servo_and_ccd(mock_servo_host):
    """A host device with a single servo v4.1 connected to a DUT with CCD.

    Args:
        mock_servo_host (Mock): Mock host device
    """

    def generate_host(board, model):
        """Generate a mock DUT for the given board/model

        Args:
            board (string): board name of the DUT
            model (string): model name of the DUT

        Yields:
            Mock: mock host device with a servo 4.1, CCD and servod started on it.
        """
        servo_host = mock_servo_host()
        # Setup
        servo_v4p1_device = servo_host.add_device("servo_v4p1", 1, 56, "2.5")
        ccd_device = servo_host.add_device("ccd_cr50", 1, 57, "2.3")
        servo_host.start(servo_v4p1_device.iSerial, board, model)
        return (servo_host, servo_v4p1_device, ccd_device)

    return generate_host


@pytest.fixture()
def mock_host_with_4p1_servo_and_servo_micro(mock_servo_host):
    """A host device with a single servo v4.1 connected to a DUT through a servo micro.

    Args:
        mock_servo_host (Mock): Mock host device
    """

    def generate_host(board, model):
        """Generate a mock DUT for the given board/model

        Args:
            board (string): board name of the DUT
            model (string): model name of the DUT

        Yields:
            Mock: mock host device with a servo 4.1, servo micro and servod started on it.
        """
        servo_host = mock_servo_host()
        # Setup
        servo_v4p1_device = servo_host.add_device("servo_v4p1", 1, 56, "2.5")
        servo_micro_device = servo_host.add_device("servo_micro", 1, 57, "2.3")
        servo_host.start(servo_v4p1_device.iSerial, board, model)
        return (servo_host, servo_v4p1_device, servo_micro_device)

    return generate_host


@pytest.fixture()
def mock_host_with_4p1_servo_and_servo_micro_and_ccd(mock_servo_host):
    """A host device with a single servo v4.1 connected to a DUT with CCD through a servo micro.

    Args:
        mock_servo_host (Mock): Mock host device
    """

    def generate_host(board, model):
        """Generate a mock DUT for the given board/model

        Args:
            board (string): board name of the DUT
            model (string): model name of the DUT

        Yields:
            Mock: mock host device with a servo 4.1, servo micro and servod started on it.
        """
        servo_host = mock_servo_host()
        # Setup
        servo_v4p1_device = servo_host.add_device("servo_v4p1", 1, 56, "2.5")
        servo_micro_device = servo_host.add_device("servo_micro", 1, 57, "2.3")
        ccd_device = servo_host.add_device("ccd_cr50", 1, 58, "2.2")
        servo_host.start(servo_v4p1_device.iSerial, board, model, "full")
        return (servo_host, servo_v4p1_device, servo_micro_device, ccd_device)

    return generate_host


@pytest.fixture()
def mock_host_with_4p1_servo_and_c2d2(mock_servo_host):
    """A host device with a single servo v4.1 connected to a DUT through a C2D2.

    Args:
        mock_servo_host (Mock): Mock host device
    """

    def generate_host(board, model):
        """Generate a mock DUT for the given board/model

        Args:
            board (string): board name of the DUT
            model (string): model name of the DUT

        Yields:
            Mock: mock host device with a servo 4.1, C2D2 and servod started on it.
        """
        servo_host = mock_servo_host()
        # Setup
        servo_v4p1_device = servo_host.add_device("servo_v4p1", 1, 56, "2.5")
        c2d2_device = servo_host.add_device("c2d2", 1, 57, "2.3")
        servo_host.start(servo_v4p1_device.iSerial, board, model)
        return (servo_host, servo_v4p1_device, c2d2_device)

    return generate_host


@pytest.fixture()
def mock_host_with_4p1_servo_and_c2d2_and_ccd(mock_servo_host):
    """A host device with a single servo v4.1 connected to a DUT with CCD through a C2D2.

    Args:
        mock_servo_host (Mock): Mock host device
    """

    def generate_host(board, model):
        """Generate a mock DUT for the given board/model

        Args:
            board (string): board name of the DUT
            model (string): model name of the DUT

        Yields:
            Mock: mock host device with a servo 4.1, C2D2 and servod started on it.
        """
        servo_host = mock_servo_host()
        # Setup
        servo_v4p1_device = servo_host.add_device("servo_v4p1", 1, 56, "2.5")
        c2d2_device = servo_host.add_device("c2d2", 1, 57, "2.3")
        ccd_device = servo_host.add_device("ccd_cr50", 1, 58, "2.2")
        servo_host.start(servo_v4p1_device.iSerial, board, model, "full")
        return (servo_host, servo_v4p1_device, c2d2_device, ccd_device)

    return generate_host
