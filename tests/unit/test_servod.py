# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import errno
import json
import socket
import unittest

# pylint: disable=too-many-function-args
from unittest import mock
from unittest.mock import MagicMock
from unittest.mock import mock_open
from unittest.mock import patch
from xmlrpc.server import SimpleXMLRPCServer

from servo.common import servo_dev_templates
from servo.common import servo_parsing
from servo.core import servo_dev_finder
from servo.core import servod
from servo.utils import scratch


class TestServoStarter(unittest.TestCase):
    """Test ServoStarter."""

    @patch("servo.utils.scratch.Scratch.__init__", return_value=None)
    @patch("servo.core.servod.ServodStarter._init_parsers_and_option_helpers")
    @patch("servo.core.servod.ServodStarter._start_xml_server", return_value=9999)
    @patch(
        "servo.core.servod.ServodStarter._discover_servos", return_value=(None, None)
    )
    @patch("servo.core.servod.ServodStarter._setup_servos")
    @patch("servo.core.servod.ServodStarter._setup_servod_server")
    @patch("servo.core.recovery.set_recovery_active")
    @patch("servo.common.utils.servo_logging.setup")
    @patch("servo.core.servo_server.Servod")
    @patch("servo.core.watchdog.DeviceWatchdog")
    @patch("servo.core.servod.disable_unusable_usb3_hubs")
    @patch("servo.common.proto.system_config_grpc")
    @patch("grpc.insecure_channel")
    @patch("threading.Thread")
    def test_init(
        self,
        mock_thread,
        _mock_insecure_channel,
        _mock_sys_config_grpc,
        mock_disable_hubs,
        mock_watchdog,
        mock_servod_class,
        mock_logging_setup,
        mock_recovery_active,
        mock_setup_servod_server,
        mock_setup_servos,
        mock_discover_servos,
        mock_start_xml_server,
        mock_init_parsers,
        _mock_scratch_init,
    ):
        """Test __init__()."""
        # Setup mocks
        mock_servod_instance = mock_servod_class.return_value
        mock_servod_instance.clear = MagicMock()

        sopts = MagicMock()
        sopts.host = "localhost"
        sopts.servo_recovery = True
        sopts.usbkm232 = None
        sopts.step_init = False
        sopts.fetch_token_db = False
        sopts.dump_xml = None
        sopts.grpc_core_port = 9991
        sopts.grpc_data_host = "localhost"
        sopts.grpc_data_port = 9992
        sopts.reconnect_timeout = 10.0
        sopts.no_hwinit = False

        with patch(
            "servo.core.servod.ServodStarter._parse_args", return_value=(sopts, [])
        ):
            starter = servod.ServodStarter([])

        # Verification
        mock_init_parsers.assert_called_once()
        mock_start_xml_server.assert_called_once()
        mock_discover_servos.assert_called_once_with(sopts, [])
        mock_setup_servos.assert_called_once()
        mock_setup_servod_server.assert_called_once()
        mock_recovery_active.assert_called_once()
        mock_logging_setup.assert_called_once()

        mock_servod_instance.hwinit.assert_called_once_with(
            verbose=True,
            step_init=False,
        )
        mock_servod_instance.validate_dut_controller.assert_called_once()
        mock_disable_hubs.assert_called_once()

        # Check process and thread creation

        mock_thread.assert_called()
        self.assertGreaterEqual(mock_thread.call_count, 1)
        mock_watchdog.assert_called_once()

        self.assertFalse(starter._turndown_initiated)
        self.assertEqual(starter._exit_status, 0)
        self.assertEqual(starter._host, "localhost")

    @patch("servo.core.servod.ServodStarter.__init__", return_value=None)
    def test_check_for_excluded_modules_none(self, _mock_init):
        """Test _check_for_excluded_modules() when no modules match."""
        starter = servod.ServodStarter([])
        starter._logger = MagicMock()
        with patch("os.path.exists", return_value=True):
            with patch(
                "builtins.open",
                mock_open(read_data="module1 1234 0\nmodule2 5678 0\n"),
            ):
                starter._check_for_excluded_modules()
        starter._logger.fatal.assert_not_called()

    @patch("servo.core.servod.ServodStarter.__init__", return_value=None)
    def test_check_for_excluded_modules_found(self, _mock_init):
        """Test _check_for_excluded_modules() when a module matches."""
        starter = servod.ServodStarter([])
        starter._logger = MagicMock()
        with patch("os.path.exists", return_value=True):
            with patch(
                "builtins.open",
                mock_open(read_data="GobiNet 1234 0\nmodule2 5678 0\n"),
            ):
                with self.assertRaises(SystemExit) as cm:
                    starter._check_for_excluded_modules()
                self.assertEqual(cm.exception.code, 1)
        starter._logger.fatal.assert_called()

    @patch("servo.core.servod.ServodStarter.__init__", return_value=None)
    def test_handle_sig(self, _mock_init):
        """Test handle_sig()."""
        starter = servod.ServodStarter([])
        starter._turndown_initiated = False
        starter._logger = MagicMock()
        starter._grpc_server = MagicMock()  # Mock the gRPC server attribute
        starter._server = (
            MagicMock()
        )  # Keep this as it's still used for XMLRPC shutdown
        starter._servod = MagicMock()

        starter.handle_sig(0)

        self.assertTrue(starter._turndown_initiated)
        starter._grpc_server.stop.assert_called_once_with(0)
        starter._server.shutdown.assert_called_once()
        starter._server.server_close.assert_called_once()
        starter._servod.close.assert_called_once()

    @patch("servo.core.servod.ServodStarter.__init__", return_value=None)
    def test_init_parsers_and_option_helpers(self, _mock_init):
        """Test _init_parsers_and_option_helpers()."""
        starter = servod.ServodStarter([])

        starter._init_parsers_and_option_helpers()

        self.assertTrue(
            isinstance(starter.help_parser, servo_parsing._BaseServodParser)
        )
        self.assertTrue(isinstance(starter.server_pars, servo_parsing.BaseServodParser))
        self.assertTrue(isinstance(starter.dev_pars, servo_parsing.ServodRCParser))
        self.assertTrue(isinstance(starter.devopts_generator(), argparse.Namespace))

    @patch("servo.core.servod.ServodStarter.__init__", return_value=None)
    def test_parse_args(self, _mock_init):
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
        starter.server_pars.parse_known_args = MagicMock(
            return_value=(server_args, dev_cmdline)
        )

        (server_args_res, dev_args_list) = starter._parse_args([])

        server_args.log_dir = None
        self.assertEqual(server_args_res, server_args)
        self.assertEqual(len(dev_args_list), 3)
        self.assertEqual(dev_args_list[0].board, "atlas")
        self.assertEqual(dev_args_list[1].serialname, "serial")
        self.assertEqual(dev_args_list[2].product, 3)
        self.assertEqual(dev_args_list[2].vendor, 4)

    @patch("servo.core.servod.ServodStarter.__init__", return_value=None)
    def test_parse_args_help(self, _mock_init):
        """Test _parse_args()."""
        starter = servod.ServodStarter([])
        starter._init_parsers_and_option_helpers()
        starter.help_parser.print_help = MagicMock()
        starter.help_parser.exit = MagicMock(side_effect=SystemExit(0))

        with self.assertRaises(SystemExit) as cm:
            starter._parse_args(["-h"])
        self.assertEqual(cm.exception.code, 0)
        starter.help_parser.print_help.assert_called_once()
        starter.help_parser.exit.assert_called_once()

        starter.help_parser.print_help.reset_mock()
        starter.help_parser.exit.reset_mock()

        with self.assertRaises(SystemExit) as cm:
            starter._parse_args(["--help"])
        self.assertEqual(cm.exception.code, 0)
        starter.help_parser.print_help.assert_called_once()
        starter.help_parser.exit.assert_called_once()

    @patch("servo.core.servod.ServodStarter.__init__", return_value=None)
    @patch("servo.common.servo_parsing.arg_marked_as_user_supplied", return_value=True)
    @patch("xmlrpc.server.SimpleXMLRPCServer.__init__", return_value=None)
    def test_start_xml_server_user_supplied(self, mock_rpc_init, _mock_arg, _mock_init):
        """Test _start_xml_server()."""
        sopts = argparse.Namespace()
        sopts.port = 9999
        starter = servod.ServodStarter([])
        starter._host = "localhost"

        port = starter._start_xml_server(sopts)

        self.assertEqual(port, 9999)
        self.assertEqual(starter._servo_port, 9999)
        self.assertTrue(isinstance(starter._server, SimpleXMLRPCServer))
        mock_rpc_init.assert_called_once_with(("localhost", 9999), logRequests=False)

    @patch("servo.core.servod.ServodStarter.__init__", return_value=None)
    @patch("servo.common.servo_parsing.arg_marked_as_user_supplied", return_value=True)
    def test_start_xml_server_user_supplied_busy_port(self, _mock_arg, _mock_init):
        """Test _start_xml_server()."""
        sopts = argparse.Namespace()
        sopts.port = 9999
        starter = servod.ServodStarter([])
        starter._host = "localhost"
        starter._logger = MagicMock()

        err = socket.error()
        err.errno = errno.EADDRINUSE

        with self.assertRaises(SystemExit):
            with patch("xmlrpc.server.SimpleXMLRPCServer.__init__", side_effect=err):
                starter._start_xml_server(sopts)

        starter._logger.fatal.assert_called_once_with("Port 9999 is busy")

    @patch("servo.core.servod.ServodStarter.__init__", return_value=None)
    @patch("servo.common.servo_parsing.arg_marked_as_user_supplied", return_value=True)
    def test_start_xml_server_error(self, _mock_arg, _mock_init):
        """Test _start_xml_server()."""
        sopts = argparse.Namespace()
        sopts.port = 9999
        starter = servod.ServodStarter([])
        starter._host = "localhost"
        starter._logger = MagicMock()

        err = socket.error()
        err.errno = errno.ERANGE

        with self.assertRaises(SystemExit):
            with patch("xmlrpc.server.SimpleXMLRPCServer.__init__", side_effect=err):
                starter._start_xml_server(sopts)

        starter._logger.fatal.assert_called_once_with(
            "Problem opening Server's socket: %s", err
        )

    @patch("servo.core.servod.ServodStarter.__init__", return_value=None)
    @patch("servo.common.servo_parsing.arg_marked_as_user_supplied", return_value=False)
    def test_start_xml_server_default_range(self, _mock_arg, _mock_init):
        """Test _start_xml_server()."""
        sopts = argparse.Namespace()
        sopts.port = 9999
        starter = servod.ServodStarter([])
        starter._host = "localhost"
        err = socket.error()
        err.errno = errno.EADDRINUSE

        with patch(
            "xmlrpc.server.SimpleXMLRPCServer.__init__",
            side_effect=[err, err, err, None],
        ) as mock_rpc_init:
            port = starter._start_xml_server(sopts)
            mock_rpc_init.assert_has_calls(
                [
                    mock.call(("localhost", 9999), logRequests=False),
                    mock.call(("localhost", 9998), logRequests=False),
                    mock.call(("localhost", 9997), logRequests=False),
                    mock.call(("localhost", 9996), logRequests=False),
                ]
            )

        self.assertEqual(port, 9996)
        self.assertEqual(starter._servo_port, 9996)

    @patch("servo.core.servod.ServodStarter.__init__", return_value=None)
    @patch("servo.common.servo_parsing.arg_marked_as_user_supplied", return_value=False)
    def test_start_xml_server_default_range_busy_port(self, _mock_arg, _mock_init):
        """Test _start_xml_server()."""
        sopts = argparse.Namespace()
        sopts.port = 9999
        starter = servod.ServodStarter([])
        starter._host = "localhost"
        starter._logger = MagicMock()
        err = socket.error()
        err.errno = errno.EADDRINUSE

        with self.assertRaises(SystemExit) as result:
            with patch(
                "xmlrpc.server.SimpleXMLRPCServer.__init__",
                side_effect=err,
            ) as mock_rpc_init:
                starter._start_xml_server(sopts)
                self.assertEqual(mock_rpc_init.call_count, 9999 - 9200 + 1)

        self.assertEqual(result.exception.code, -1)
        starter._logger.fatal.assert_called_once_with(
            "Could not find a free port in 9200..9999 range"
        )

    @patch("servo.core.servod.ServodStarter.__init__", return_value=None)
    def test_setup_servod_server(self, _mock_init):
        """Test _setup_servod_server()."""
        starter = servod.ServodStarter([])
        starter._server = MagicMock()
        starter._servod = MagicMock()  # We don't need real Servod here

        starter._setup_servod_server()

        starter._server.register_introspection_functions.assert_called_once()
        starter._server.register_multicall_functions.assert_called_once()
        starter._server.register_instance.assert_called_once_with(starter._servod)

    @patch("servo.core.servod.ServodStarter.__init__", return_value=None)
    @patch(
        "servo.utils.servo_dev_hierarchy.ServoDeviceHierarchy.__init__",
        return_value=None,
    )
    @patch("servo.core.servo_dev_finder.ServoDeviceFinder.__init__", return_value=None)
    @patch(
        "servo.core.servo_dev_finder.ServoDeviceFinder.discover_servos", return_value=[]
    )
    @patch(
        "servo.core.servo_dev_finder.ServoDeviceFinder.choose_main_device",
        return_value=None,
    )
    @patch("servo.core.servo_dev_finder.ServoDeviceFinder.generate_prefixes")
    @patch("servo.core.servo_dev_finder.ServoDeviceFinder.validate_devopts")
    def test_discover_servos(
        self,
        mock_validate,
        mock_generate,
        mock_choose,
        mock_discover,
        _mock_finder_init,
        _mock_hierarchy_init,
        _mock_init,
    ):
        """Test _discover_servos()."""
        starter = servod.ServodStarter([])
        starter.devopts_generator = None
        starter._scratchutil = None
        sopts = argparse.Namespace()
        sopts.device_discovery = "full"

        res = starter._discover_servos(sopts, None)

        mock_discover.assert_called_once()
        mock_choose.assert_called_once_with([])
        mock_generate.assert_called_once_with([], None)
        mock_validate.assert_called_once_with([])
        self.assertEqual(res, ([], None))

    @patch("servo.core.servod.ServodStarter.__init__", return_value=None)
    @patch(
        "servo.utils.servo_dev_hierarchy.ServoDeviceHierarchy.__init__",
        return_value=None,
    )
    @patch("servo.core.servo_dev_finder.ServoDeviceFinder.__init__", return_value=None)
    @patch(
        "servo.core.servo_dev_finder.ServoDeviceFinder.discover_servos", return_value=[]
    )
    @patch(
        "servo.core.servo_dev_finder.ServoDeviceFinder.choose_main_device",
        return_value=None,
    )
    @patch("servo.core.servo_dev_finder.ServoDeviceFinder.generate_prefixes")
    @patch(
        "servo.core.servo_dev_finder.ServoDeviceFinder.validate_devopts",
        side_effect=servo_dev_finder.ServoDeviceFinderError(),
    )
    def test_discover_servos_error(
        self,
        _mock_validate,
        _mock_generate,
        _mock_choose,
        _mock_discover,
        _mock_finder_init,
        _mock_hierarchy_init,
        _mock_init,
    ):
        """Test _discover_servos() in the case of error."""
        starter = servod.ServodStarter([])
        starter.devopts_generator = None
        starter._scratchutil = None
        starter._logger = MagicMock()
        sopts = argparse.Namespace()
        sopts.device_discovery = "full"

        with self.assertRaises(servo_dev_finder.ServoDeviceFinderError):
            starter._discover_servos(sopts, None)

    @patch("servo.core.servod.ServodStarter._init_parsers_and_option_helpers")
    @patch("servo.core.servod.ServodStarter._parse_args")
    @patch("servo.core.servod.ServodStarter._start_xml_server", return_value=9999)
    @patch("servo.core.servod.ServodStarter._discover_servos")
    @patch("servo.common.utils.servo_logging.setup")
    @patch("servo.utils.scratch.Scratch.__init__", return_value=None)
    def test_init_discover_error(
        self,
        _mock_scratch_init,
        _mock_logging_setup,
        mock_discover_servos,
        _mock_start_xml_server,
        mock_parse_args,
        _mock_init_parsers,
    ):
        """Test __init__() in the case of error during _discover_servos."""
        sopts = MagicMock()
        sopts.host = "localhost"
        sopts.servo_recovery = False
        sopts.usbkm232 = None
        sopts.step_init = False
        sopts.fetch_token_db = False
        sopts.log_dir = None
        sopts.debug = False
        sopts.log_dir_backup_count = 0
        sopts.reconnect_timeout = 10.0
        mock_parse_args.return_value = (sopts, [])

        mock_discover_servos.side_effect = servo_dev_finder.ServoDeviceFinderError(
            "Error message"
        )

        with self.assertRaises(SystemExit) as result:
            servod.ServodStarter([])

        self.assertEqual(result.exception.code, -1)

    @patch("servo.core.servod.ServodStarter.__init__", return_value=None)
    @patch("servo.core.servo_dev.ServoDevice.init_servo_interfaces")
    @patch("servo.core.servo_dev.ServoDevice.set_board_and_model", return_value=True)
    @patch("servo.core.servo_dev.ServoDevice.set_base_board")
    @patch("servo.core.servo_dev.GrpcClient")  # Mock GrpcClient to avoid network
    @patch("servo.common.proto.system_config_grpc.SystemConfig")
    def test_setup_servos(
        self,
        mock_sys_config_grpc,
        _mock_grpc_client,
        mock_set_base,
        mock_set_board,
        _mock_init_interfaces,
        _mock_init,
    ):
        """Test _setup_servos()."""
        starter = servod.ServodStarter([])
        starter.opts = MagicMock()
        starter.opts.debug = True
        starter._logger = MagicMock()
        starter._servod = MagicMock()

        # Mock add_device/get_devices to simulate storage
        devices_list = []
        starter._servod.add_device.side_effect = (
            lambda dev, prefix: devices_list.append(dev)
        )
        starter._servod.get_devices.side_effect = lambda: devices_list

        # Setup SystemConfig mock response
        mock_client = mock_sys_config_grpc.return_value
        mock_response = MagicMock()
        mock_response.systemConfig = []
        mock_response.loglines = []
        mock_client.GetFileContent.return_value = mock_response
        mock_client.AddCfgFile.return_value = mock_response
        mock_client.Finalize.return_value = None
        mock_client.GetAvailableModels.return_value = MagicMock(models=[])

        mock_interfaces = MagicMock()
        mock_interfaces.interface_list_json = json.dumps(["interface1"])
        mock_client.GetServoInterfaces.return_value = mock_interfaces

        # Setup dev entries
        main_dev_entry = MagicMock()

        dev_entry_1 = MagicMock()
        dev_entry_1.devopts.noautoconfig = False
        dev_entry_1.devopts.config = ["extraconfig1"]
        dev_entry_1.devopts.prefix = [""]
        dev_entry_1.devopts.board = "atlas"
        dev_entry_1.devopts.model = None
        dev_entry_1.devopts.noboard = False
        dev_entry_1.devopts.nomodel = False
        dev_entry_1.devopts.board_supplied_by_user = False
        dev_entry_1.devopts.model_supplied_by_user = False
        dev_entry_1.dev_template = servo_dev_templates.get_template_class_by_name(
            "ccd_cr50"
        )
        dev_entry_1.vid = 0x18D1
        dev_entry_1.pid = 0x5014
        dev_entry_1.serial = "serial1"

        dev_entry_2 = MagicMock()
        dev_entry_2.devopts.noautoconfig = False
        dev_entry_2.devopts.config = []
        dev_entry_2.devopts.prefix = ["v4"]
        dev_entry_2.devopts.board = "testing"
        dev_entry_2.devopts.model = "testing"
        dev_entry_2.devopts.noboard = False
        dev_entry_2.devopts.nomodel = False
        dev_entry_2.devopts.board_supplied_by_user = True
        dev_entry_2.devopts.model_supplied_by_user = True
        dev_entry_2.dev_template = servo_dev_templates.get_template_class_by_name(
            "servo_v4p1"
        )
        dev_entry_2.vid = 0x18D1
        dev_entry_2.pid = 0x501B
        dev_entry_2.serial = "serial2"

        dev_entries = [dev_entry_1, dev_entry_2]

        # Call with fake grpc address
        starter._setup_servos(dev_entries, main_dev_entry, ("localhost", 9992))
        self.assertEqual(dev_entry_1.devopts.board, "atlas")
        mock_set_base.assert_called_once_with("atlas")
        mock_set_board.assert_has_calls(
            [
                mock.call("atlas", None),
                mock.call("testing", "testing"),
            ]
        )
        self.assertEqual(starter._servod.update_known_ctrls.call_count, 2)

    @patch("servo.core.servod.ServodStarter.__init__", return_value=None)
    @patch("servo.core.servo_dev.ServoDevice.init_servo_interfaces")
    @patch("servo.core.servo_dev.ServoDevice.set_board_and_model", return_value=True)
    @patch("servo.core.servo_dev.ServoDevice.set_base_board")
    @patch("servo.common.proto.system_config_grpc.SystemConfig")
    @patch("grpc.insecure_channel")
    def test_setup_servos_no_configs(
        self,
        _mock_channel,
        mock_sys_config_grpc,
        mock_set_base,
        mock_set_board,
        _mock_init_interfaces,
        _mock_init,
    ):
        """Test _setup_servos()."""
        starter = servod.ServodStarter([])
        starter.opts = MagicMock()
        starter.opts.debug = True
        starter._logger = MagicMock()
        starter._servod = MagicMock()
        main_dev_entry = MagicMock()

        dev_entry_1 = MagicMock()
        dev_entry_1.devopts.noautoconfig = False
        dev_entry_1.devopts.config = ["extraconfig1", "extraconfig2"]
        dev_entry_1.devopts.prefix = [""]
        dev_entry_1.devopts.board = "atlas"
        dev_entry_1.devopts.model = None
        dev_entry_1.devopts.noboard = False
        dev_entry_1.devopts.nomodel = False
        dev_entry_1.devopts.board_supplied_by_user = False
        dev_entry_1.devopts.model_supplied_by_user = False
        dev_entry_1.devopts.interfaces = []
        dev_entry_1.devopts.token_db = "default"
        dev_entry_1.dev_template = servo_dev_templates.get_template_class_by_name(
            "ccd_cr50"
        )
        dev_entry_1.vid = 0
        dev_entry_1.pid = 0
        dev_entry_1.serial = ""

        dev_entry_2 = MagicMock()
        dev_entry_2.devopts.noautoconfig = True
        dev_entry_2.devopts.config = []
        dev_entry_2.devopts.prefix = ["v4"]
        dev_entry_2.devopts.board = dev_entry_2.devopts.model = "testing"
        dev_entry_2.devopts.noboard = False
        dev_entry_2.devopts.nomodel = False
        dev_entry_2.devopts.board_supplied_by_user = True
        dev_entry_2.devopts.model_supplied_by_user = True
        dev_entry_2.devopts.interfaces = []
        dev_entry_2.devopts.token_db = "default"
        dev_entry_2.dev_template = servo_dev_templates.get_template_class_by_name(
            "servo_v4p1"
        )
        dev_entry_2.vid = 0
        dev_entry_2.pid = 0
        dev_entry_2.serial = ""
        dev_entries = [dev_entry_1, dev_entry_2]

        # Setup SystemConfig mock response
        mock_client = mock_sys_config_grpc.return_value
        mock_response = MagicMock()
        mock_response.loglines = []
        mock_client.AddCfgFile.return_value = mock_response
        mock_client.Finalize.return_value = None
        mock_client.GetAvailableModels.return_value = MagicMock(models=[])

        mock_interfaces = MagicMock()
        mock_interfaces.interface_list_json = json.dumps(["interface1"])
        mock_client.GetServoInterfaces.return_value = mock_interfaces

        with self.assertRaisesRegex(
            servod.ServodError,
            "No automatic config found, and no config specified with -c <file>",
        ):
            starter._setup_servos(dev_entries, main_dev_entry, ("localhost", 9999))
        self.assertEqual(dev_entry_1.devopts.board, "atlas")
        mock_set_base.assert_called_once_with("atlas")
        mock_set_board.assert_called_once_with("atlas", None)

    @patch("servo.core.servod.ServodStarter.__init__", return_value=None)
    def test_cleanup(self, _mock_init):
        """Test cleanup()."""
        starter = servod.ServodStarter([])
        starter._logger = MagicMock()
        starter._scratchutil = MagicMock()
        starter._grpc_server = MagicMock()
        starter._host = "localhost"
        starter._servo_port = 9999

        starter.cleanup()
        starter._scratchutil.remove_entry.assert_called_once_with(9999)

    @patch("servo.core.servod.ServodStarter.__init__", return_value=None)
    def test__serve(self, _mock_init):
        """Test _serve()."""
        starter = servod.ServodStarter([])
        starter._logger = MagicMock()
        starter._server = MagicMock()
        starter._host = "localhost"
        starter._servo_port = 9999
        starter._exit_status = 0

        starter._serve()
        starter._server.serve_forever.assert_called_once()
        self.assertEqual(starter._exit_status, 0)

    @patch("servo.core.servod.ServodStarter.__init__", return_value=None)
    def test__serve_error(self, _mock_init):
        """Test _serve() in case of error."""
        starter = servod.ServodStarter([])
        starter._logger = MagicMock()
        starter._server = MagicMock()
        starter._server.serve_forever.side_effect = Exception()
        starter._host = "localhost"
        starter._servo_port = 9999
        starter._exit_status = 0

        starter._serve()
        starter._server.serve_forever.assert_called_once()
        self.assertEqual(starter._exit_status, 1)

    @patch("servo.core.servod.ServodStarter.__init__", return_value=None)
    @patch("signal.signal")
    @patch("signal.pause")
    def test_serve(self, mock_pause, _mock_signal, _mock_init):
        """Test serve()."""
        # Instead of exiting, we simulate that pause was interrupted by a signal,
        # allowing the rest of the function to execute naturally and clean up.
        # We also need to mock sys.exit to prevent the actual exit at the end.
        mock_pause.return_value = None

        starter = servod.ServodStarter([])
        starter.EXIT_TIMEOUT_S = 0.01
        starter._servo_port = 9999
        starter._exit_status = 0
        starter._logger = MagicMock()
        starter._servod = MagicMock()
        starter._servod.get_servo_serials.return_value = {"dev1": "serial1"}

        starter._scratchutil = MagicMock()
        starter._grpc_server = MagicMock()
        starter._watchdog_thread = MagicMock()
        starter._watchdog_thread.is_alive.return_value = True
        starter._server_thread = MagicMock()
        starter._server_thread.is_alive.return_value = False

        # Mock grpc_server_process

        starter.cleanup = MagicMock()

        with patch("sys.exit") as mock_exit:
            starter.serve()

        mock_exit.assert_called_once_with(0)

        starter._watchdog_thread.start.assert_called_once()
        starter._server_thread.start.assert_called_once()
        starter._scratchutil.mark_active.assert_called_once()
        starter._watchdog_thread.deactivate.assert_called_once()
        starter._watchdog_thread.join.assert_called_once()
        starter._server_thread.join.assert_called_once()
        starter.cleanup.assert_called_once()

        # Verify process killed

    @patch("servo.core.servod.ServodStarter.__init__", return_value=None)
    def test_serve_scratch_error(self, _mock_init):
        """Test serve() in case of scratch error."""
        starter = servod.ServodStarter([])
        starter._servod = MagicMock()
        starter._servod.get_servo_serials.return_value = {"dev1": "serial1"}
        starter._servod.close = MagicMock()
        starter._scratchutil = MagicMock()
        starter._grpc_server = MagicMock()
        starter._scratchutil.add_entry.side_effect = scratch.ScratchError()
        starter._servo_port = 9999
        starter._logger = MagicMock()

        with self.assertRaises(SystemExit) as result:
            starter.serve()

        self.assertEqual(result.exception.code, 1)
        starter._servod.close.assert_called_once()

    @patch("servo.core.servod.ServodStarter.__init__", return_value=None)
    @patch("signal.signal")
    @patch("signal.pause")
    def test_serve_cannot_close_threads(self, mock_pause, _mock_signal, _mock_init):
        """Test serve() with stuck threads."""
        mock_pause.return_value = None

        starter = servod.ServodStarter([])
        starter.EXIT_TIMEOUT_S = 0.01
        starter._servo_port = 9999
        starter._exit_status = 0
        starter._logger = MagicMock()
        starter._servod = MagicMock()
        starter._servod.get_servo_serials.return_value = {"dev1": "serial1"}

        starter._scratchutil = MagicMock()
        starter._grpc_server = MagicMock()
        starter._watchdog_thread = MagicMock()
        starter._watchdog_thread.is_alive.return_value = True
        starter._server_thread = MagicMock()
        starter._server_thread.is_alive.return_value = True

        starter.cleanup = MagicMock()

        with patch("sys.exit") as mock_exit:
            starter.serve()

        mock_exit.assert_called_once_with(0)
        starter._logger.error.assert_any_call(
            "Server thread not turned down after %s s.", starter.EXIT_TIMEOUT_S
        )
        starter._logger.error.assert_any_call(
            "Watchdog thread not turned down after %s s.", starter.EXIT_TIMEOUT_S
        )


class TestMain(unittest.TestCase):
    """Test Main."""

    @patch("servo.core.servod.ServodStarter.__init__", return_value=None)
    @patch("servo.core.servod.ServodStarter.serve")
    def test_main(self, _mock_serve, _mock_init):
        """Test main()."""
        servod.main(["-b", "atlas"])

        servod.ServodStarter.__init__.assert_called_once_with(["-b", "atlas"])
        servod.ServodStarter.serve.assert_called_once()

    @patch(
        "servo.core.servod.ServodStarter.__init__",
        side_effect=servod.ServodError("err"),
    )
    @patch("servo.core.servod.ServodStarter.serve")
    def test_main_error(self, _mock_serve, _mock_init):
        """Test main()."""
        with self.assertRaises(SystemExit) as cm:
            servod.main(["-b", "atlas"])

        servod.ServodStarter.__init__.assert_called_once_with(["-b", "atlas"])
        servod.ServodStarter.serve.assert_not_called()
        self.assertEqual(cm.exception.code, 1)


class TestServodValidation(unittest.TestCase):
    """Test board/model enforcement logic."""

    @patch("servo.core.servod.ServodStarter.__init__", return_value=None)
    @patch("servo.common.proto.system_config_grpc.SystemConfig")
    @patch("servo.common.proto.driver_grpc.DriverService")
    @patch("servo.common.grpc_client.GrpcClient.create_grpc_channel")
    @patch("grpc.insecure_channel")
    def test_setup_servos_enforcement(
        self,
        _mock_channel,
        _mock_create_channel,
        mock_driver_grpc,
        mock_sys_config_grpc,
        _mock_init,
    ):
        starter = servod.ServodStarter([])
        starter.opts = MagicMock()
        starter.opts.debug = True
        starter._logger = MagicMock()
        starter._servod = MagicMock()

        mock_client = mock_sys_config_grpc.return_value
        mock_driver_client = mock_driver_grpc.return_value
        mock_driver_client.InitInterface.return_value = MagicMock()

        # Mock interfaces response
        mock_interfaces = MagicMock()
        mock_interfaces.interface_list_json = "[]"
        mock_client.GetServoInterfaces.return_value = mock_interfaces

        # Mock other config methods
        mock_response = MagicMock()
        mock_response.systemConfig = []
        mock_response.loglines = []
        mock_client.GetFileContent.return_value = mock_response
        mock_client.AddCfgFile.return_value = mock_response
        mock_client.Finalize.return_value = None
        mock_client.GetAvailableModels.return_value = MagicMock(models=[])

        # Helper to create a dev_entry
        def create_dev_entry(board=None, model=None, noboard=False):
            dev_entry = MagicMock()
            dev_entry.devopts.board = board
            dev_entry.devopts.model = model
            dev_entry.devopts.noboard = noboard
            dev_entry.devopts.nomodel = False
            dev_entry.devopts.board_supplied_by_user = bool(board)
            dev_entry.devopts.model_supplied_by_user = bool(model)
            dev_entry.devopts.noautoconfig = False
            dev_entry.devopts.config = []
            dev_entry.devopts.prefix = [""]
            dev_entry.devopts.interfaces = []
            dev_entry.devopts.token_db = "default"
            dev_entry.dev_template = servo_dev_templates.get_template_class_by_name(
                "ccd_cr50"
            )
            dev_entry.vid = 0x18D1
            dev_entry.pid = 0x5014
            dev_entry.serial = "1234"
            return dev_entry

        # Test 1: No board, no noboard, probing fails (empty board)
        dev_entry = create_dev_entry(board="", noboard=False)
        with self.assertRaisesRegex(
            servod.ServodError, "No board provided. Please provide"
        ):
            starter._setup_servos([dev_entry], None, ("localhost", 9999))

        # Test 2: No board, but --noboard is provided. Should NOT raise.
        dev_entry = create_dev_entry(board="", noboard=True)
        # We need to mock other things to avoid failure later in _setup_servos
        starter._servod.add_device = MagicMock()
        starter._setup_servos([dev_entry], None, ("localhost", 9999))

        # Test 3: Board provided, has models, but no --model provided.
        dev_entry = create_dev_entry(board="brya", model="", noboard=False)
        mock_client.GetAvailableModels.return_value = MagicMock(
            models=["banshee", "vell"]
        )

        with self.assertRaisesRegex(
            servod.ServodError, "Board brya has models: banshee, vell"
        ):
            starter._setup_servos([dev_entry], None, ("localhost", 9999))

        # Test 4: Both board and noboard provided.
        dev_entry = create_dev_entry(board="brya", noboard=True)
        with self.assertRaisesRegex(
            servod.ServodError, "Cannot provide both --board and --noboard"
        ):
            starter._setup_servos([dev_entry], None, ("localhost", 9999))

        # Test 5: Board provided, has models, and model is provided. Should NOT raise.
        dev_entry = create_dev_entry(board="brya", model="banshee", noboard=False)
        starter._servod.add_device = MagicMock()

        # Test 5.1: If set_board_and_model returns True, it succeeds.
        with patch(
            "servo.core.servo_dev.ServoDevice.set_board_and_model", return_value=True
        ):
            starter._setup_servos([dev_entry], None, ("localhost", 9999))

        # Test 6: Board provided, but XML config not found. Should raise.
        dev_entry = create_dev_entry(
            board="fakeboard", model="fakemodel", noboard=False
        )
        with patch(
            "servo.core.servo_dev.ServoDevice.set_board_and_model", return_value=False
        ):
            with self.assertRaisesRegex(
                servod.ServodError, "Cannot find XML overlay for board fakeboard"
            ):
                starter._setup_servos([dev_entry], None, ("localhost", 9999))

        # Test 7: Board provided, has models, --nomodel provided. Should NOT raise.
        dev_entry = create_dev_entry(board="brya", model="", noboard=False)
        dev_entry.devopts.nomodel = True
        mock_client.GetAvailableModels.return_value = MagicMock(
            models=["banshee", "vell"]
        )
        with patch(
            "servo.core.servo_dev.ServoDevice.set_board_and_model", return_value=True
        ):
            starter._setup_servos([dev_entry], None, ("localhost", 9999))

        # Test 8: Board and model provided, has models, model not found.
        # Should NOT raise. (This implicitly tests the graceful fallback in
        # system_config resolving to True)
        dev_entry = create_dev_entry(board="brya", model="unknown_model", noboard=False)
        mock_client.GetAvailableModels.return_value = MagicMock(
            models=["banshee", "vell"]
        )
        with patch(
            "servo.core.servo_dev.ServoDevice.set_board_and_model", return_value=True
        ):
            starter._setup_servos([dev_entry], None, ("localhost", 9999))


if __name__ == "__main__":
    unittest.main()
