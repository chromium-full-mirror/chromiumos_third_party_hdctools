# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import errno
import socket
import threading
import unittest
import unittest.mock
from xmlrpc.server import SimpleXMLRPCServer

from servo.common.utils import servo_logging
from servo.core import recovery
from servo.core import servo_dev
from servo.core import servo_dev_finder
from servo.core import servo_dev_templates
from servo.core import servo_parsing
from servo.core import servo_server
from servo.core import servod
from servo.core import watchdog
from servo.utils import scratch
from servo.utils import servo_dev_prober


class TestServoStarter(unittest.TestCase):
    """Test ServoStarter."""

    @unittest.mock.patch(
        "servo.utils.scratch.Scratch.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    @unittest.mock.patch(
        "servo.utils.servo_dev_prober.DeviceProber.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    @unittest.mock.patch(
        "servo.servod.ServodStarter._init_parsers_and_option_helpers",
        unittest.mock.MagicMock(),
    )
    @unittest.mock.patch(
        "servo.servod.ServodStarter._start_xml_server", unittest.mock.MagicMock()
    )
    @unittest.mock.patch(
        "servo.servod.ServodStarter._discover_servos",
        unittest.mock.MagicMock(return_value=(None, None)),
    )
    @unittest.mock.patch(
        "servo.servod.ServodStarter._setup_servos", unittest.mock.MagicMock()
    )
    @unittest.mock.patch(
        "servo.servod.ServodStarter._setup_servod_server", unittest.mock.MagicMock()
    )
    @unittest.mock.patch(
        "servo.recovery.set_recovery_active", unittest.mock.MagicMock()
    )
    @unittest.mock.patch("servo.servo_logging.setup", unittest.mock.MagicMock())
    @unittest.mock.patch(
        "servo.servo_server.Servod.__init__", unittest.mock.MagicMock(return_value=None)
    )
    @unittest.mock.patch(
        "servo.servo_server.Servod.validate_dut_controller", unittest.mock.MagicMock()
    )
    @unittest.mock.patch(
        "servo.servod.servo_server.Servod.hwinit", unittest.mock.MagicMock()
    )
    @unittest.mock.patch(
        "servo.watchdog.DeviceWatchdog.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    @unittest.mock.patch(
        "servo.servod.disable_unusable_usb3_hubs", unittest.mock.MagicMock()
    )
    @unittest.mock.patch(
        "servo.common.proto.system_config_grpc", unittest.mock.MagicMock()
    )
    @unittest.mock.patch("grpc.insecure_channel", unittest.mock.MagicMock())
    def test_init(self):
        """Test __init__()."""
        sopts = unittest.mock.MagicMock()
        sopts.host = "localhost"
        sopts.servo_recovery = True
        sopts.usbkm232 = None
        sopts.step_init = False
        sopts.fetch_token_db = False
        with unittest.mock.patch(
            "servo.servod.ServodStarter._parse_args",
            unittest.mock.MagicMock(return_value=(sopts, [])),
        ):
            starter = servod.ServodStarter([])
        servod.ServodStarter._init_parsers_and_option_helpers.assert_called_once()
        servod.ServodStarter._start_xml_server.assert_called_once()
        servod.ServodStarter._discover_servos.assert_called_once_with(sopts, [])
        servod.ServodStarter._setup_servos.assert_called_once_with(
            None, None, unittest.mock.ANY
        )
        servod.ServodStarter._setup_servod_server.assert_called_once()
        recovery.set_recovery_active.assert_called_once()
        servo_logging.setup.assert_called_once()
        servo_server.Servod.hwinit.assert_called_once_with(
            verbose=True,
            step_init=False,
        )
        servo_server.Servod.validate_dut_controller.assert_called_once()
        servod.disable_unusable_usb3_hubs.assert_called_once()
        self.assertTrue(isinstance(starter._server_thread, threading.Thread))
        self.assertTrue(isinstance(starter._watchdog_thread, watchdog.DeviceWatchdog))
        self.assertFalse(starter._turndown_initiated)
        self.assertEqual(starter._exit_status, 0)
        self.assertEqual(starter._host, "localhost")

    @unittest.mock.patch(
        "servo.servod.ServodStarter.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    def test_handle_sig(self):
        """Test handle_sig()."""
        starter = servod.ServodStarter([])
        starter._turndown_initiated = False
        starter._logger = unittest.mock.MagicMock()
        starter._logger.info = unittest.mock.MagicMock()
        starter._server = unittest.mock.MagicMock()
        starter._server.shutdown = unittest.mock.MagicMock()
        starter._server.server_close = unittest.mock.MagicMock()
        starter._servod = unittest.mock.MagicMock()
        starter._servod.close = unittest.mock.MagicMock()

        starter.handle_sig(0)

        self.assertTrue(starter._turndown_initiated)
        starter._server.shutdown.assert_called_once()
        starter._server.server_close.assert_called_once()
        starter._servod.close.assert_called_once()

    @unittest.mock.patch(
        "servo.servod.ServodStarter.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    def test_init_parsers_and_option_helpers(self):
        """Test _init_parsers_and_option_helpers()."""
        starter = servod.ServodStarter([])

        starter._init_parsers_and_option_helpers()

        self.assertTrue(
            isinstance(starter.help_parser, servo_parsing._BaseServodParser)
        )
        self.assertTrue(isinstance(starter.server_pars, servo_parsing.BaseServodParser))
        self.assertTrue(isinstance(starter.dev_pars, servo_parsing.ServodRCParser))
        self.assertTrue(isinstance(starter.devopts_generator(), argparse.Namespace))
        self.assertEqual(
            starter.help_parser.format_usage, starter.server_pars.format_usage
        )
        self.assertEqual(
            starter.help_parser.format_usage, starter.dev_pars.format_usage
        )

    @unittest.mock.patch(
        "servo.servod.ServodStarter.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    def test_parse_args(self):
        """Test _parse_args()."""
        starter = servod.ServodStarter([])
        starter._init_parsers_and_option_helpers()
        server_args = argparse.Namespace()
        server_args.no_log_dir = True
        dev_cmdline = [
            "-b",
            "atlas",
            "---",
            "-s",
            "serial",
            "---",
            "---",
            "--product",
            "3",
            "--vendor",
            "4",
            "---",
        ]
        starter.server_pars.parse_known_args = unittest.mock.MagicMock(
            return_value=(server_args, dev_cmdline)
        )

        (server_args_res, dev_args_list) = starter._parse_args([])

        server_args.log_dir = None
        self.assertEqual(server_args_res, server_args)
        self.assertEqual(len(dev_args_list), 3)
        self.assertTrue(isinstance(dev_args_list[0], argparse.Namespace))
        self.assertEqual(dev_args_list[0].board, "atlas")
        self.assertTrue(isinstance(dev_args_list[1], argparse.Namespace))
        self.assertEqual(dev_args_list[1].serialname, "serial")
        self.assertTrue(isinstance(dev_args_list[2], argparse.Namespace))
        self.assertEqual(dev_args_list[2].product, 3)
        self.assertEqual(dev_args_list[2].vendor, 4)

    @unittest.mock.patch(
        "servo.servod.ServodStarter.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    def test_parse_args_help(self):
        """Test _parse_args()."""
        starter = servod.ServodStarter()
        starter._init_parsers_and_option_helpers()
        starter.help_parser.print_help = unittest.mock.MagicMock()

        with self.assertRaises(SystemExit) as exit_h:
            starter._parse_args(["-h"])

        self.assertEqual(exit_h.exception.code, 0)
        starter.help_parser.print_help.assert_called_once()

        starter.help_parser.print_help.reset_mock()
        with self.assertRaises(SystemExit) as exit_help:
            starter._parse_args(["--help"])

        self.assertEqual(exit_help.exception.code, 0)
        starter.help_parser.print_help.assert_called_once()

    @unittest.mock.patch(
        "servo.servod.ServodStarter.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    @unittest.mock.patch(
        "servo.servo_parsing.ArgMarkedAsUserSupplied",
        unittest.mock.MagicMock(return_value=True),
    )
    @unittest.mock.patch(
        "xmlrpc.server.SimpleXMLRPCServer.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    def test_start_xml_server_user_supplied(self):
        """Test _start_xml_server()."""
        sopts = argparse.Namespace()
        sopts.port = 9999
        starter = servod.ServodStarter([])
        starter._host = "localhost"

        port = starter._start_xml_server(sopts)

        self.assertEqual(port, 9999)
        self.assertEqual(starter._servo_port, 9999)
        self.assertTrue(isinstance(starter._server, SimpleXMLRPCServer))
        SimpleXMLRPCServer.__init__.assert_called_once_with(
            ("localhost", 9999), logRequests=False
        )

    @unittest.mock.patch(
        "servo.servod.ServodStarter.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    @unittest.mock.patch(
        "servo.servo_parsing.ArgMarkedAsUserSupplied",
        unittest.mock.MagicMock(return_value=True),
    )
    def test_start_xml_server_user_supplied_busy_port(self):
        """Test _start_xml_server()."""
        sopts = argparse.Namespace()
        sopts.port = 9999
        starter = servod.ServodStarter([])
        starter._host = "localhost"
        starter._logger = unittest.mock.MagicMock()
        starter._logger.fatal = unittest.mock.MagicMock()
        err = socket.error()
        err.errno = errno.EADDRINUSE

        with self.assertRaises(SystemExit) as result:
            with unittest.mock.patch(
                "xmlrpc.server.SimpleXMLRPCServer.__init__",
                unittest.mock.MagicMock(side_effect=err),
            ):
                starter._start_xml_server(sopts)

        self.assertEqual(result.exception.code, -1)
        starter._logger.fatal.assert_called_once_with("Port 9999 is busy")

    @unittest.mock.patch(
        "servo.servod.ServodStarter.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    @unittest.mock.patch(
        "servo.servo_parsing.ArgMarkedAsUserSupplied",
        unittest.mock.MagicMock(return_value=True),
    )
    def test_start_xml_server_error(self):
        """Test _start_xml_server()."""
        sopts = argparse.Namespace()
        sopts.port = 9999
        starter = servod.ServodStarter([])
        starter._host = "localhost"
        starter._logger = unittest.mock.MagicMock()
        starter._logger.fatal = unittest.mock.MagicMock()
        err = socket.error()
        err.errno = errno.ERANGE

        with self.assertRaises(SystemExit) as result:
            with unittest.mock.patch(
                "xmlrpc.server.SimpleXMLRPCServer.__init__",
                unittest.mock.MagicMock(side_effect=err),
            ):
                starter._start_xml_server(sopts)

        self.assertEqual(result.exception.code, -1)
        starter._logger.fatal.assert_called_once_with(
            "Problem opening Server's socket: %s", err
        )

    @unittest.mock.patch(
        "servo.servod.ServodStarter.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    @unittest.mock.patch(
        "servo.servo_parsing.ArgMarkedAsUserSupplied",
        unittest.mock.MagicMock(return_value=False),
    )
    def test_start_xml_server_default_range(self):
        """Test _start_xml_server()."""
        sopts = argparse.Namespace()
        sopts.port = 9999
        starter = servod.ServodStarter([])
        starter._host = "localhost"
        err = socket.error()
        err.errno = errno.EADDRINUSE

        with unittest.mock.patch(
            "xmlrpc.server.SimpleXMLRPCServer.__init__",
            unittest.mock.MagicMock(side_effect=[err, err, err, None]),
        ):
            port = starter._start_xml_server(sopts)
            SimpleXMLRPCServer.__init__.assert_has_calls(
                [
                    unittest.mock.call(("localhost", 9999), logRequests=False),
                    unittest.mock.call(("localhost", 9998), logRequests=False),
                    unittest.mock.call(("localhost", 9997), logRequests=False),
                    unittest.mock.call(("localhost", 9996), logRequests=False),
                ]
            )

        self.assertEqual(port, 9996)
        self.assertEqual(starter._servo_port, 9996)
        self.assertTrue(isinstance(starter._server, SimpleXMLRPCServer))

    @unittest.mock.patch(
        "servo.servod.ServodStarter.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    @unittest.mock.patch(
        "servo.servo_parsing.ArgMarkedAsUserSupplied",
        unittest.mock.MagicMock(return_value=False),
    )
    def test_start_xml_server_default_range_busy_port(self):
        """Test _start_xml_server()."""
        sopts = argparse.Namespace()
        sopts.port = 9999
        starter = servod.ServodStarter([])
        starter._host = "localhost"
        starter._logger = unittest.mock.MagicMock()
        starter._logger.fatal = unittest.mock.MagicMock()
        err = socket.error()
        err.errno = errno.EADDRINUSE

        with self.assertRaises(SystemExit) as result:
            with unittest.mock.patch(
                "xmlrpc.server.SimpleXMLRPCServer.__init__",
                unittest.mock.MagicMock(side_effect=err),
            ):
                starter._start_xml_server(sopts)
                self.assertEqual(
                    SimpleXMLRPCServer.__init__.call_count, 9999 - 9200 + 1
                )

        self.assertEqual(result.exception.code, -1)
        starter._logger.fatal.assert_called_once_with(
            "Could not find a free port in 9200..9999 range"
        )

    @unittest.mock.patch(
        "servo.servod.ServodStarter.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    def test_setup_servod_server(self):
        """Test _setup_servod_server()."""
        starter = servod.ServodStarter([])
        starter._server = unittest.mock.MagicMock()
        starter._servod = servo_server.Servod()
        starter._server.register_introspection_functions = unittest.mock.MagicMock()
        starter._server.register_multicall_functions = unittest.mock.MagicMock()
        starter._server.register_instance = unittest.mock.MagicMock()

        starter._setup_servod_server()

        starter._server.register_introspection_functions.assert_called_once()
        starter._server.register_multicall_functions.assert_called_once()
        starter._server.register_instance.assert_called_once_with(starter._servod)

    @unittest.mock.patch(
        "servo.servod.ServodStarter.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    @unittest.mock.patch(
        "servo.utils.servo_dev_hierarchy.ServoDeviceHierarchy.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    @unittest.mock.patch(
        "servo.servo_dev_finder.ServoDeviceFinder.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    @unittest.mock.patch(
        "servo.servo_dev_finder.ServoDeviceFinder.discover_servos",
        unittest.mock.MagicMock(return_value=[]),
    )
    @unittest.mock.patch(
        "servo.servo_dev_finder.ServoDeviceFinder.choose_main_device",
        unittest.mock.MagicMock(return_value=None),
    )
    @unittest.mock.patch(
        "servo.servo_dev_finder.ServoDeviceFinder.generate_prefixes",
        unittest.mock.MagicMock(),
    )
    @unittest.mock.patch(
        "servo.servo_dev_finder.ServoDeviceFinder.validate_devopts",
        unittest.mock.MagicMock(),
    )
    def test_discover_servos(self):
        """Test _discover_servos()."""
        starter = servod.ServodStarter([])
        starter.devopts_generator = None
        starter._scratchutil = None
        sopts = argparse.Namespace()
        sopts.device_discovery = "full"

        res = starter._discover_servos(sopts, None)

        servo_dev_finder.ServoDeviceFinder.discover_servos.assert_called_once()
        servo_dev_finder.ServoDeviceFinder.choose_main_device.assert_called_once_with(
            []
        )
        servo_dev_finder.ServoDeviceFinder.generate_prefixes.assert_called_once_with(
            [], None
        )
        servo_dev_finder.ServoDeviceFinder.validate_devopts.assert_called_once_with([])
        self.assertEqual(res, ([], None))

    @unittest.mock.patch(
        "servo.servod.ServodStarter.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    @unittest.mock.patch(
        "servo.utils.servo_dev_hierarchy.ServoDeviceHierarchy.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    @unittest.mock.patch(
        "servo.servo_dev_finder.ServoDeviceFinder.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    @unittest.mock.patch(
        "servo.servo_dev_finder.ServoDeviceFinder.discover_servos",
        unittest.mock.MagicMock(return_value=[]),
    )
    @unittest.mock.patch(
        "servo.servo_dev_finder.ServoDeviceFinder.choose_main_device",
        unittest.mock.MagicMock(return_value=None),
    )
    @unittest.mock.patch(
        "servo.servo_dev_finder.ServoDeviceFinder.generate_prefixes",
        unittest.mock.MagicMock(),
    )
    @unittest.mock.patch(
        "servo.servo_dev_finder.ServoDeviceFinder.validate_devopts",
        unittest.mock.MagicMock(side_effect=servo_dev_finder.ServoDeviceFinderError()),
    )
    def test_discover_servos_error(self):
        """Test _discover_servos() in the case of error."""
        starter = servod.ServodStarter([])
        starter.devopts_generator = None
        starter._scratchutil = None
        starter._logger = unittest.mock.MagicMock()
        starter._logger.fatal = unittest.mock.MagicMock()
        sopts = argparse.Namespace()
        sopts.device_discovery = "full"

        with self.assertRaises(SystemExit) as result:
            starter._discover_servos(sopts, None)

        servo_dev_finder.ServoDeviceFinder.discover_servos.assert_called_once()
        servo_dev_finder.ServoDeviceFinder.choose_main_device.assert_called_once_with(
            []
        )
        servo_dev_finder.ServoDeviceFinder.generate_prefixes.assert_called_once_with(
            [], None
        )
        servo_dev_finder.ServoDeviceFinder.validate_devopts.assert_called_once_with([])
        starter._logger.fatal.assert_called_once_with(
            "Failure during discovering servo devices: %s", unittest.mock.ANY
        )
        self.assertEqual(result.exception.code, -1)

    @unittest.mock.patch(
        "servo.servod.ServodStarter.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    @unittest.mock.patch(
        "servo.utils.servo_dev_prober.DeviceProber.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    @unittest.mock.patch(
        "servo.servo_dev.ServoDevice.init_servo_interfaces", unittest.mock.MagicMock()
    )
    @unittest.mock.patch(
        "servo.servo_dev.ServoDevice.set_board_and_model",
        unittest.mock.MagicMock(return_value=False),
    )
    @unittest.mock.patch(
        "servo.servo_dev.ServoDevice.set_base_board", unittest.mock.MagicMock()
    )
    def test_setup_servos(self):
        """Test _setup_servos()."""
        starter = servod.ServodStarter([])
        starter._logger = unittest.mock.MagicMock()
        starter._servod = servo_server.Servod()
        starter._servod.update_known_ctrls = unittest.mock.MagicMock()
        starter._servod._get_system_config = unittest.mock.MagicMock()
        prober = servo_dev_prober.DeviceProber()
        prober.get_board_from_ec = unittest.mock.MagicMock(return_value="atlas")
        prober.get_model_from_ec = unittest.mock.MagicMock(return_value="nuvoton")
        main_dev_entry = unittest.mock.MagicMock()
        main_device = unittest.mock.MagicMock()
        root_device = unittest.mock.MagicMock()
        main_dev_entry.servo_device = main_device
        main_device.get_root_hub_device = unittest.mock.MagicMock(
            return_value=root_device
        )
        dev_entry_1 = unittest.mock.MagicMock()
        dev_entry_1.devopts = argparse.Namespace()
        dev_entry_1.devopts.noautoconfig = False
        dev_entry_1.devopts.config = ["extraconfig1", "extraconfig2"]
        dev_entry_1.devopts.prefix = [""]
        dev_entry_1.devopts.board = dev_entry_1.devopts.model = None
        dev_entry_1.devopts.interfaces = []
        dev_entry_1.devopts.token_db = "default"
        dev_entry_1.dev_template = servo_dev_templates.GetTemplateClassByName(
            "ccd_cr50"
        )
        dev_entry_2 = unittest.mock.MagicMock()
        dev_entry_2.devopts = argparse.Namespace()
        dev_entry_2.devopts.noautoconfig = False
        dev_entry_2.devopts.config = []
        dev_entry_2.devopts.prefix = ["v4"]
        dev_entry_2.devopts.board = dev_entry_2.devopts.model = "testing"
        dev_entry_2.devopts.interfaces = []
        dev_entry_2.devopts.token_db = "default"
        dev_entry_2.dev_template = servo_dev_templates.GetTemplateClassByName(
            "servo_v4p1"
        )
        dev_entries = [dev_entry_1, dev_entry_2]

        starter._setup_servos(dev_entries, main_dev_entry, prober)
        self.assertEqual(servo_dev.ServoDevice.init_servo_interfaces.call_count, 3)
        servo_dev.ServoDevice.init_servo_interfaces.assert_has_calls(
            [
                unittest.mock.call(fault_tolerant=True),  # ccd_cr50 only
                unittest.mock.call(),
                unittest.mock.call(),
            ]
        )
        self.assertEqual(dev_entry_1.devopts.board, "atlas")
        self.assertEqual(dev_entry_1.devopts.model, "nuvoton")
        servo_dev.ServoDevice.set_base_board.assert_called_once_with("atlas")
        servo_dev.ServoDevice.set_board_and_model.asset_has_calls(
            [
                unittest.mock.call("atlas", "nuvoton"),
                unittest.mock.call("testing", "testing"),
            ]
        )
        self.assertEqual(starter._servod.update_known_ctrls.call_count, 2)

    @unittest.mock.patch(
        "servo.servod.ServodStarter.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    @unittest.mock.patch(
        "servo.utils.servo_dev_prober.DeviceProber.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    @unittest.mock.patch(
        "servo.common.config.system_config.SystemConfig.display_config",
        unittest.mock.MagicMock(),
    )
    @unittest.mock.patch(
        "servo.common.config.system_config.SystemConfig.finalize",
        unittest.mock.MagicMock(),
    )
    @unittest.mock.patch(
        "servo.servo_dev.ServoDevice.init_servo_interfaces", unittest.mock.MagicMock()
    )
    @unittest.mock.patch(
        "servo.servo_dev.ServoDevice.set_board_and_model",
        unittest.mock.MagicMock(return_value=False),
    )
    @unittest.mock.patch(
        "servo.servo_dev.ServoDevice.set_base_board", unittest.mock.MagicMock()
    )
    def test_setup_servos_no_configs(self):
        """Test _setup_servos()."""
        starter = servod.ServodStarter([])
        starter._logger = unittest.mock.MagicMock()
        starter._servod = servo_server.Servod()
        prober = servo_dev_prober.DeviceProber()
        starter._servod._get_system_config = unittest.mock.MagicMock()
        prober.get_board_from_ec = unittest.mock.MagicMock(return_value="atlas")
        prober.get_model_from_ec = unittest.mock.MagicMock(return_value="nuvoton")
        main_dev_entry = unittest.mock.MagicMock()
        dev_entry_1 = unittest.mock.MagicMock()
        dev_entry_1.devopts = argparse.Namespace()
        dev_entry_1.devopts.noautoconfig = False
        dev_entry_1.devopts.config = ["extraconfig1", "extraconfig2"]
        dev_entry_1.devopts.prefix = [""]
        dev_entry_1.devopts.board = dev_entry_1.devopts.model = None
        dev_entry_1.devopts.interfaces = []
        dev_entry_1.devopts.token_db = "default"
        dev_entry_1.dev_template = servo_dev_templates.GetTemplateClassByName(
            "ccd_cr50"
        )
        dev_entry_2 = unittest.mock.MagicMock()
        dev_entry_2.devopts = argparse.Namespace()
        dev_entry_2.devopts.noautoconfig = True
        dev_entry_2.devopts.config = []
        dev_entry_2.devopts.prefix = ["v4"]
        dev_entry_2.devopts.board = dev_entry_2.devopts.model = "testing"
        dev_entry_2.devopts.interfaces = []
        dev_entry_2.devopts.token_db = "default"
        dev_entry_2.dev_template = servo_dev_templates.GetTemplateClassByName(
            "servo_v4p1"
        )
        dev_entries = [dev_entry_1, dev_entry_2]

        with self.assertRaisesRegex(
            servod.ServodError,
            "No automatic config found, and no config specified with -c <file>",
        ):
            starter._setup_servos(dev_entries, main_dev_entry, prober)
        servo_dev.ServoDevice.init_servo_interfaces.assert_called_once()
        servo_dev.ServoDevice.init_servo_interfaces.assert_called_once_with(
            fault_tolerant=True
        )
        self.assertEqual(dev_entry_1.devopts.board, "atlas")
        self.assertEqual(dev_entry_1.devopts.model, "nuvoton")
        servo_dev.ServoDevice.set_base_board.assert_called_once_with("atlas")
        servo_dev.ServoDevice.set_board_and_model.assert_called_once_with(
            "atlas", "nuvoton"
        )

    @unittest.mock.patch(
        "servo.servod.ServodStarter.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    def test_cleanup(self):
        """Test cleanup()."""
        starter = servod.ServodStarter([])
        starter._logger = unittest.mock.MagicMock()
        starter._scratchutil = unittest.mock.MagicMock()
        starter._scratchutil.RemoveEntry = unittest.mock.MagicMock()
        starter._host = "localhost"
        starter._servo_port = 9999

        starter.cleanup()
        starter._scratchutil.RemoveEntry.assert_called_once_with(starter._servo_port)

    @unittest.mock.patch(
        "servo.servod.ServodStarter.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    def test__serve(self):
        """Test _serve()."""
        starter = servod.ServodStarter([])
        starter._logger = unittest.mock.MagicMock()
        starter._server = unittest.mock.MagicMock()
        starter._server.serve_forever = unittest.mock.MagicMock()
        starter._host = "localhost"
        starter._servo_port = 9999
        starter._exit_status = 0

        starter._serve()
        starter._server.serve_forever.assert_called_once()
        self.assertEqual(starter._exit_status, 0)

    @unittest.mock.patch(
        "servo.servod.ServodStarter.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    def test__serve_error(self):
        """Test _serve()."""
        starter = servod.ServodStarter([])
        starter._logger = unittest.mock.MagicMock()
        starter._server = unittest.mock.MagicMock()
        starter._server.serve_forever = unittest.mock.MagicMock(side_effect=Exception())
        starter._host = "localhost"
        starter._servo_port = 9999
        starter._exit_status = 0

        starter._serve()
        starter._server.serve_forever.assert_called_once()
        self.assertEqual(starter._exit_status, 1)

    @unittest.mock.patch(
        "servo.servod.ServodStarter.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    @unittest.mock.patch("signal.signal", unittest.mock.MagicMock())
    @unittest.mock.patch("signal.pause", unittest.mock.MagicMock())
    def test_serve(self):
        """Test serve()."""
        starter = servod.ServodStarter([])
        starter._servo_port = 9999
        starter._exit_status = 0
        starter._logger = unittest.mock.MagicMock()
        starter._logger.error = unittest.mock.MagicMock()
        starter._servod = unittest.mock.MagicMock()
        starter._servod.get_servo_serials = unittest.mock.MagicMock(
            return_value={"dev1": "serial1", "dev2": "serial2"}
        )
        starter._scratchutil = unittest.mock.MagicMock()
        starter._scratchutil.AddEntry = unittest.mock.MagicMock()
        starter._scratchutil.MarkActive = unittest.mock.MagicMock()
        starter._watchdog_thread = unittest.mock.MagicMock()
        starter._watchdog_thread.start = unittest.mock.MagicMock()
        starter._watchdog_thread.deactivate = unittest.mock.MagicMock()
        starter._watchdog_thread.join = unittest.mock.MagicMock()
        starter._watchdog_thread.is_alive = unittest.mock.MagicMock(return_value=False)
        starter._server_thread = unittest.mock.MagicMock()
        starter._server_thread.start = unittest.mock.MagicMock()
        starter._server_thread.join = unittest.mock.MagicMock()
        starter._server_thread.is_alive = unittest.mock.MagicMock(return_value=False)
        starter.cleanup = unittest.mock.MagicMock()

        with self.assertRaises(SystemExit) as result:
            starter.serve()

        self.assertEqual(result.exception.code, 0)
        starter._scratchutil.AddEntry.assert_called_once_with(
            9999, set(["serial1", "serial2"]), unittest.mock.ANY
        )
        starter._watchdog_thread.start.assert_called_once()
        starter._server_thread.start.assert_called_once()
        starter._scratchutil.MarkActive.assert_called_once_with(9999)
        starter._watchdog_thread.deactivate.assert_called_once()
        starter._watchdog_thread.join.assert_called_once()
        starter._server_thread.join.assert_called_once()
        starter.cleanup.assert_called_once()
        starter._logger.error.assert_not_called()

    @unittest.mock.patch(
        "servo.servod.ServodStarter.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    def test_serve_scratch_error(self):
        """Test serve() in case of scratch error."""
        starter = servod.ServodStarter([])
        starter._servod = unittest.mock.MagicMock()
        starter._servod.get_servo_serials = unittest.mock.MagicMock(
            return_value={"dev1": "serial1", "dev2": "serial2"}
        )
        starter._servod.close = unittest.mock.MagicMock()
        starter._scratchutil = unittest.mock.MagicMock()
        starter._scratchutil.AddEntry = unittest.mock.MagicMock(
            side_effect=scratch.ScratchError()
        )
        starter._servo_port = 9999

        with self.assertRaises(SystemExit) as result:
            starter.serve()

        self.assertEqual(result.exception.code, 1)
        starter._scratchutil.AddEntry.assert_called_once_with(
            9999, set(["serial1", "serial2"]), unittest.mock.ANY
        )
        starter._servod.close.assert_called_once()

    @unittest.mock.patch(
        "servo.servod.ServodStarter.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    @unittest.mock.patch("signal.signal", unittest.mock.MagicMock())
    @unittest.mock.patch("signal.pause", unittest.mock.MagicMock())
    def test_serve_cannot_close_threads(self):
        """Test serve()."""
        starter = servod.ServodStarter([])
        starter._servo_port = 9999
        starter._exit_status = 0
        starter._logger = unittest.mock.MagicMock()
        starter._logger.error = unittest.mock.MagicMock()
        starter._servod = unittest.mock.MagicMock()
        starter._servod.get_servo_serials = unittest.mock.MagicMock(
            return_value={"dev1": "serial1", "dev2": "serial2"}
        )
        starter._scratchutil = unittest.mock.MagicMock()
        starter._scratchutil.AddEntry = unittest.mock.MagicMock()
        starter._scratchutil.MarkActive = unittest.mock.MagicMock()
        starter._watchdog_thread = unittest.mock.MagicMock()
        starter._watchdog_thread.start = unittest.mock.MagicMock()
        starter._watchdog_thread.deactivate = unittest.mock.MagicMock()
        starter._watchdog_thread.join = unittest.mock.MagicMock()
        starter._watchdog_thread.is_alive = unittest.mock.MagicMock(return_value=True)
        starter._server_thread = unittest.mock.MagicMock()
        starter._server_thread.start = unittest.mock.MagicMock()
        starter._server_thread.join = unittest.mock.MagicMock()
        starter._server_thread.is_alive = unittest.mock.MagicMock(return_value=True)
        starter.cleanup = unittest.mock.MagicMock()

        with self.assertRaises(SystemExit) as result:
            starter.serve()

        self.assertEqual(result.exception.code, 0)
        starter._scratchutil.AddEntry.assert_called_once_with(
            9999, set(["serial1", "serial2"]), unittest.mock.ANY
        )
        starter._watchdog_thread.start.assert_called_once()
        starter._server_thread.start.assert_called_once()
        starter._scratchutil.MarkActive.assert_called_once_with(9999)
        starter._watchdog_thread.deactivate.assert_called_once()
        starter._watchdog_thread.join.assert_called_once()
        starter._server_thread.join.assert_called_once()
        starter.cleanup.assert_called_once()
        starter._logger.error.assert_has_calls(
            [
                unittest.mock.call(
                    "Server thread not turned down after %s s.", starter.EXIT_TIMEOUT_S
                ),
                unittest.mock.call(
                    "Watchdog thread not turned down after %s s.",
                    starter.EXIT_TIMEOUT_S,
                ),
            ]
        )


class TestMain(unittest.TestCase):
    """Test Main."""

    @unittest.mock.patch(
        "servo.servod.ServodStarter.__init__",
        unittest.mock.MagicMock(return_value=None),
    )
    @unittest.mock.patch("servo.servod.ServodStarter.serve", unittest.mock.MagicMock())
    def test_main(self):
        """Test main()."""
        servod.main(["-b", "atlas"])

        servod.ServodStarter.__init__.assert_called_once_with(["-b", "atlas"])
        servod.ServodStarter.serve.assert_called_once()

    @unittest.mock.patch(
        "servo.servod.ServodStarter.__init__",
        unittest.mock.MagicMock(side_effect=servod.ServodError("err")),
    )
    @unittest.mock.patch("servo.servod.ServodStarter.serve", unittest.mock.MagicMock())
    def test_main_error(self):
        """Test main()."""
        with self.assertRaises(SystemExit) as cm:
            servod.main(["-b", "atlas"])

        servod.ServodStarter.__init__.assert_called_once_with(["-b", "atlas"])
        servod.ServodStarter.serve.assert_not_called()
        self.assertEqual(cm.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
