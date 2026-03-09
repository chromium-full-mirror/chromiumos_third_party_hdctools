# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# PyUSB is the python module servod uses to communicate with USB endpoint.
# This file provides a mock version of each of the main entities that the
# PyUSB interface provides.  Device, Configuration, Interface, Endpoint

# pylint: disable=redefined-outer-name
# pylint: disable=unused-argument

from functools import partial
import logging
import queue
import tempfile
import time

import pytest


_logger = logging.getLogger("mock_pyusb")


@pytest.fixture(scope="function")
def mock_endpoint(mocker):
    """A mock USB endpoint to emulate hardware for for servo testing."""

    def generate_mock_endpoint(b_endpoint_address, parent, description):
        """Create a Mock object that represents a PyUSB endpoint

        Args:
            b_endpoint_address (int): Endpoint id
            parent (Mock interface): The mock interface that contains this
                                     endpoints.
            description (str): Name of the endpoint, example "CR50 Uart" used
                               for logging.

        Returns:
            Mock: A mock object that setup to emulate a USB endpoint.
        """
        mock_endpoint = mocker.Mock(name="Endpoint %s" % description)

        def mock_read(ep, description, size_or_buffer, _):
            """Function to emulate the read function of PyUSB endpoints.

            Look in the queue of commands - for all the commands in
            the queue ( typically just one ) find the mocked data and
            return that.

            Args:
                ep (Mock): Mock endpoint object used to access / store data.
                description (str): Name of the endpoint, example "CR50 Uart" used
                               for logging.
                size_or_buffer:  Either the number of bytes to read or an array
                                 object where the data will be put in
            Returns:
                string: mocked data for the last command issued.
            """
            result = None
            command = None
            while ep.parent.command_queue.qsize() > 0:
                try:
                    command = ep.parent.command_queue.queue[0]
                    if command not in ep.parent.mocked_data:
                        # Store any command we do not have mocked data so the
                        # test data can report this.
                        ep.parent.no_data_command_queue.put(
                            "%s: %s" % (description, command)
                        )
                        _logger.debug(
                            "%s Missing mock data for command %s", description, command
                        )
                        ep.parent.command_queue.get()
                    else:
                        if not result:
                            result = ep.parent.mocked_data[command]
                            if isinstance(result, list):
                                if len(result) > 1:
                                    result = result.pop(0)
                                else:
                                    result = result[0]
                            ep.parent.command_queue.get()
                            ep.parent.executed_command_queue.put(command)

                        else:
                            new_result = ep.parent.mocked_data[command]
                            if len(result) + len(new_result) + 1 > size_or_buffer:
                                # Total results exceeds the size so stop generating
                                # a result.
                                break

                            if new_result:
                                result += b"\r\n" + new_result
                            ep.parent.command_queue.get()
                            ep.parent.executed_command_queue.put(command)
                except Exception:
                    _logger.exception("Something bad happened in endpoint read")
                    raise
            if not result:
                # Required or some of the threads will read so fast they will starve
                # other threads of resources.
                time.sleep(0.01)
            return result

        def _mock_write_list_ep(ep, data):
            """Function to emulate the write function of PyUSB endpoints.

            I2C endpoints write data as a list like [0, 38, 2, 1, 3, 156] convert
            that list into a string and push it into a command queue for the
            endpoint

            Args:
                ep (Mock): Mock endpoint object used to access / store data.
                data (list): list of I2C data like [0, 38, 2, 1, 3, 156]

            Returns:
                int: number of items in the list of data.
            """
            ep.parent.command_queue.put(str(data).encode("utf-8"))
            return len(data)

        def _mock_write_str_ep(ep, data):
            """Function to emulate the write function of PyUSB endpoints.

            UART consoles send strings to the endpoints and then read back the
            data echoed out to the console.  Store the command in a queue to
            be read later when the read command is called.

            At times multiple commands can be sent - each command is delineated
            by a line break.

            At times partial strings are sent, store these partial strings until
            the next line break is received.

            Args:
                ep (Mock): Mock endpoint object used to access / store data.
                data (string): string that is being sent to the UART.
            Returns:
                int: number of characters in the string in data
            """
            try:
                data_to_parse = ep.parent.received_data + data
                line_break = data_to_parse.find(b"\n")
                while line_break != -1:
                    command = data_to_parse[0:line_break]
                    command = command.strip()
                    ep.parent.command_queue.put(command)
                    data_to_parse = data_to_parse[line_break + 1 :]
                    line_break = data_to_parse.find(b"\n")
                if data_to_parse.endswith(b"\n"):
                    command = data_to_parse
                    command = command.strip()
                    ep.parent.command_queue.put(command)
                    data_to_parse = b""
                ep.parent.received_data = data_to_parse
            except Exception:
                _logger.exception("Something bad happened in endpoint write")
                raise
            return len(data)

        def mock_write(ep, data, _):
            """Generic write function that routes to correct write function depending
               on data type.

            Args:
                ep (Mock): Mock endpoint object used to access / store data.
                data (list/string): Data being sent to the endpoint

            Returns:
                int: the length of the data written.
            """
            if isinstance(data, list):
                return _mock_write_list_ep(ep, data)

            return _mock_write_str_ep(ep, data)

        mock_endpoint.bEndpointAddress = b_endpoint_address
        mock_endpoint.read.side_effect = partial(mock_read, mock_endpoint, description)
        mock_endpoint.write.side_effect = partial(mock_write, mock_endpoint)
        mock_endpoint.parent = parent
        return mock_endpoint

    return generate_mock_endpoint


@pytest.fixture(scope="function")
def mock_interface(mocker, mock_endpoint):
    def find_endpoint(mock_interface, _unused, _, args):
        """Mock replacement function for finding USB endpoint in PyUSB.

        Args:
            mock_interface (Mock): Mock interface object used to access / store data.
            args (dict): dictionary of arguments, we expect there to be an argument
                         called b_endpoint_address that

        Returns:
            Mock: Mock endpoint for the given address.
        """
        return mock_interface.endpoints[args["bEndpointAddress"]]

    def generate_mock_interface(
        b_interface_number,
        endpoints_nos,
        description,
        parent,
        mocked_data,
        default_reply,
    ):
        mock_interface = mocker.Mock(name="Interface")
        mock_interface.bInterfaceNumber = b_interface_number
        mock_interface.endpoints = {}
        for endpoint_no in endpoints_nos:
            mock_interface.endpoints[endpoint_no] = mock_endpoint(
                endpoint_no, mock_interface, description
            )
        mock_interface.parent = parent
        mock_interface.find_descriptor.side_effect = partial(
            find_endpoint, mock_interface
        )
        mock_interface.command_queue = queue.Queue()
        mock_interface.executed_command_queue = queue.Queue()
        mock_interface.no_data_command_queue = queue.Queue()
        mock_interface.received_data = b""
        mock_interface.lock = tempfile.TemporaryFile()
        mock_interface.mocked_data = mocked_data
        mock_interface.default_reply = default_reply
        return mock_interface

    return generate_mock_interface


@pytest.fixture(scope="function")
def mock_pyusb(mocker):
    mock_pyusb = mocker.Mock(name="PyUSB")
    mock_pyusb.devices = []

    def mock_find(
        mock_pyusb, find_all, idVendor, idProduct, serial_number=None
    ):  # pylint: disable=invalid-name

        found_devices = []
        for device in mock_pyusb.devices:
            if (
                device.idVendor == idVendor and device.idProduct == idProduct
            ):  # pylint: disable=invalid-name

                found_devices.append(device)
        return found_devices

    def mock_get_string(dev, _index, langid=None):
        """Replacement PyUSB implementation of get_string.

        As our code always only asks for the serial number we can simplify and
        not use the index and just return the serial of the device.  We also
        ignore all information in the langid param.

        Args:
            dev (Mock): Mock USB device.

        Returns:
            string: serial number of the device passed in.
        """
        # Simulate bad USB device
        if isinstance(dev.iSerial, Exception):
            raise dev.iSerial
        return dev.iSerial

    def mock_find_descriptor(desc, find_all=False, custom_match=None, **args):
        """_summary_

        Args:
            desc (_type_): _description_
            find_all (bool, optional): _description_. Defaults to False.
            custom_match (_type_, optional): _description_. Defaults to None.

        Returns:
            _type_: _description_
        """
        return desc.find_descriptor(find_all, custom_match, args)

    mocker.patch("usb.core.find", side_effect=partial(mock_find, mock_pyusb))
    mocker.patch("usb.util.get_string", side_effect=mock_get_string)

    mocker.patch("usb.util.claim_interface")
    mocker.patch("usb.util.find_descriptor", side_effect=mock_find_descriptor)
    return mock_pyusb


def clear_interfaces(device):
    for _unused, interface in device.configuration.interfaces.items():
        while not interface.executed_command_queue.empty():
            interface.executed_command_queue.get()


def dump_interfaces(device):
    result = {}
    for no, interface in device.configuration.interfaces.items():
        result[no] = list(interface.executed_command_queue.queue)
        result["missing"] = list(interface.no_data_command_queue.queue)
    return result
