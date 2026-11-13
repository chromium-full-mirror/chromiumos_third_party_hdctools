# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys
import unittest
from unittest.mock import MagicMock
from unittest.mock import patch


# Append development_environment to path so start_servod can be imported
sys.path.append(
    os.path.join(os.path.dirname(__file__), "../../development_environment")
)
# pylint: disable=import-error,wrong-import-position
import start_servod


class TestStartServod(unittest.TestCase):
    def setUp(self):
        # Set up common patches
        self.mock_docker_env = patch("start_servod.docker.from_env").start()
        self.mock_exists = patch(
            "start_servod.os.path.exists", return_value=True
        ).start()
        self.mock_needs_update = patch(
            "docker_utils.needs_update_check", return_value=False
        ).start()
        self.mock_get_image = patch(
            "start_servod.get_image", return_value="servod:dev"
        ).start()
        self.mock_makedirs = patch("start_servod.os.makedirs").start()
        self.mock_exit = patch("sys.exit").start()
        self.mock_thread = patch("start_servod.threading.Thread").start()

        # Mock docker client and container
        self.mock_client = MagicMock()
        self.mock_docker_env.return_value = self.mock_client
        self.mock_container = MagicMock(status="created")
        self.mock_container.exec_run.return_value = (0, b"")
        self.mock_client.containers.run.return_value = self.mock_container

    def tearDown(self):
        patch.stopall()

    def test_dump_xml_argument_passthrough(self):
        test_args = [
            "start-servod",
            "--dump-xml",
            "/tmp/host_file.xml",
            "-b",
            "brask",
            "--",
            "--usbkm232",
            "/dev/ttyUSB0",
        ]
        with patch.object(sys, "argv", test_args):
            args = start_servod.parse_args()

            # Verify argparse captured it correctly
            self.assertEqual(args.dump_xml, "/tmp/host_file.xml")
            self.assertIn("--usbkm232", args.passthrough)

            # Run the main logic
            start_servod.main()

            # Assert docker container run was called with correct volumes and command
            self.mock_client.containers.run.assert_called_once()
            call_kwargs = self.mock_client.containers.run.call_args[1]

            # Check volumes
            volumes = call_kwargs.get("volumes", [])
            self.assertTrue(
                any("/tmp/dump_xml/" in v for v in volumes),
                "dump_xml volume should be mounted",
            )

            # Check command
            command = " ".join(call_kwargs.get("command", []))
            self.assertIn("--dump-xml /tmp/dump_xml/host_file.xml", command)
            self.assertNotIn("-- --usbkm232", command)  # "--" should be stripped
            self.assertIn("--usbkm232 /dev/ttyUSB0", command)

    def test_noboard_argument_passthrough(self):
        test_args = ["start-servod", "--noboard"]
        with patch.object(sys, "argv", test_args):
            args = start_servod.parse_args()
            self.assertTrue(args.noboard)

            start_servod.main()

            self.mock_client.containers.run.assert_called_once()
            call_kwargs = self.mock_client.containers.run.call_args[1]
            command = " ".join(call_kwargs.get("command", []))
            self.assertIn("--noboard", command)

    def test_logs_dir_mounting(self):
        test_args = ["start-servod", "--logs", "/my/custom/logs/dir"]
        with patch.object(sys, "argv", test_args):
            start_servod.main()

            self.mock_client.containers.run.assert_called_once()
            call_kwargs = self.mock_client.containers.run.call_args[1]
            volumes = call_kwargs.get("volumes", [])

            # The host logs dir should be mounted to
            # /var/log/servod_9999 inside container
            self.assertTrue(
                any(
                    v.startswith("/my/custom/logs/dir") and "/var/log/servod_9999" in v
                    for v in volumes
                ),
                f"Expected logs directory in volumes: {volumes}",
            )

    def test_dual_servo_micro_and_ccd_console_output(self):
        test_args = ["start-servod", "-s", "SERVOV4P1-S-2106191847"]

        def exec_run_side_effect(cmd):
            if cmd == "servodtool instance wait-for-active --timeout 1 -p 9999":
                return (0, b"")
            if cmd == "dut-control servo_type":
                return (
                    0,
                    b"servo_type:servo_v4p1_with_servo_micro_and_ccd_gsc_nt\n",
                )
            if (
                cmd == "dut-control servo_micro.ec_uart_pty "
                "servo_micro.cpu_uart_pty servo_micro.gsc_uart_pty"
            ):
                return (
                    0,
                    b"servo_micro.ec_uart_pty:/dev/pts/2\n"
                    b"servo_micro.cpu_uart_pty:/dev/pts/1\n"
                    b"servo_micro.gsc_uart_pty:/dev/pts/0\n",
                )
            if cmd == "dut-control servo_micro.fpmcu_uart_pty":
                return (1, b"No control named servo_micro.fpmcu_uart_pty\n")
            if (
                cmd == "dut-control ccd_gsc.ec_uart_pty "
                "ccd_gsc.cpu_uart_pty ccd_gsc.gsc_uart_pty"
            ):
                return (
                    0,
                    b"ccd_gsc.ec_uart_pty:/dev/pts/6\n"
                    b"ccd_gsc.cpu_uart_pty:/dev/pts/5\n"
                    b"ccd_gsc.gsc_uart_pty:/dev/pts/3\n",
                )
            if cmd == "dut-control ccd_gsc.fpmcu_uart_pty":
                return (0, b"ccd_gsc.fpmcu_uart_pty:/dev/pts/7\n")
            if cmd == "dut-control active_dut_controller":
                return (0, b"active_dut_controller:servo_micro\n")
            if (
                cmd == "dut-control active.ec_uart_pty "
                "active.cpu_uart_pty active.gsc_uart_pty"
            ):
                return (
                    0,
                    b"active.ec_uart_pty:/dev/pts/2\n"
                    b"active.cpu_uart_pty:/dev/pts/1\n"
                    b"active.gsc_uart_pty:/dev/pts/0\n",
                )
            if cmd == "dut-control active.fpmcu_uart_pty":
                return (1, b"No control named active.fpmcu_uart_pty\n")
            return (0, b"")

        self.mock_container.exec_run.side_effect = exec_run_side_effect

        with (
            patch.object(sys, "argv", test_args),
            patch("builtins.print") as mock_print,
        ):
            start_servod.main()

            printed_text = "\n".join(
                " ".join(str(a) for a in call.args)
                for call in mock_print.call_args_list
            )
            self.assertIn("Servo Micro console locations:", printed_text)
            self.assertIn("servo_micro.ec_uart_pty:/dev/pts/2", printed_text)
            self.assertNotIn("servo_micro.fpmcu_uart_pty", printed_text)
            self.assertIn("\nCCD console locations:", printed_text)
            self.assertIn("ccd_gsc.ec_uart_pty:/dev/pts/6", printed_text)
            self.assertIn("ccd_gsc.fpmcu_uart_pty:/dev/pts/7", printed_text)
            self.assertIn(
                "Active console locations (active_dut_controller: servo_micro):",
                printed_text,
            )
            self.assertIn("active.ec_uart_pty:/dev/pts/2", printed_text)
            self.assertIn("active.cpu_uart_pty:/dev/pts/1", printed_text)
            self.assertIn("active.gsc_uart_pty:/dev/pts/0", printed_text)
            self.assertNotIn("active.fpmcu_uart_pty", printed_text)

    def test_dual_c2d2_and_ccd_console_output(self):
        test_args = ["start-servod", "-s", "SERVOV4P1-S-2106191847"]

        def exec_run_side_effect(cmd):
            if cmd == "servodtool instance wait-for-active --timeout 1 -p 9999":
                return (0, b"")
            if cmd == "dut-control servo_type":
                return (
                    0,
                    b"servo_type:servo_v4p1_with_c2d2_and_ccd_cr50\n",
                )
            if (
                cmd == "dut-control c2d2.ec_uart_pty "
                "c2d2.cpu_uart_pty c2d2.gsc_uart_pty"
            ):
                return (
                    0,
                    b"c2d2.ec_uart_pty:/dev/pts/2\n"
                    b"c2d2.cpu_uart_pty:/dev/pts/1\n"
                    b"c2d2.gsc_uart_pty:/dev/pts/0\n",
                )
            if (
                cmd == "dut-control ccd_gsc.ec_uart_pty "
                "ccd_gsc.cpu_uart_pty ccd_gsc.gsc_uart_pty"
            ):
                return (
                    0,
                    b"ccd_gsc.ec_uart_pty:/dev/pts/6\n"
                    b"ccd_gsc.cpu_uart_pty:/dev/pts/5\n"
                    b"ccd_gsc.gsc_uart_pty:/dev/pts/3\n",
                )
            if cmd == "dut-control active_dut_controller":
                return (0, b"active_dut_controller:c2d2\n")
            if (
                cmd == "dut-control active.ec_uart_pty "
                "active.cpu_uart_pty active.gsc_uart_pty"
            ):
                return (
                    0,
                    b"active.ec_uart_pty:/dev/pts/2\n"
                    b"active.cpu_uart_pty:/dev/pts/1\n"
                    b"active.gsc_uart_pty:/dev/pts/0\n",
                )
            if "fpmcu_uart_pty" in cmd:
                return (1, b"")
            return (0, b"")

        self.mock_container.exec_run.side_effect = exec_run_side_effect

        with (
            patch.object(sys, "argv", test_args),
            patch("builtins.print") as mock_print,
        ):
            start_servod.main()

            printed_text = "\n".join(
                " ".join(str(a) for a in call.args)
                for call in mock_print.call_args_list
            )
            self.assertIn("C2D2 console locations:", printed_text)
            self.assertIn("c2d2.ec_uart_pty:/dev/pts/2", printed_text)
            self.assertIn("\nCCD console locations:", printed_text)
            self.assertIn(
                "Active console locations (active_dut_controller: c2d2):",
                printed_text,
            )
            self.assertIn("active.ec_uart_pty:/dev/pts/2", printed_text)

    def test_single_controller_console_output(self):
        test_args = ["start-servod", "-s", "SERVOV4P1-S-2106191847"]

        def exec_run_side_effect(cmd):
            if cmd == "servodtool instance wait-for-active --timeout 1 -p 9999":
                return (0, b"")
            if cmd == "dut-control servo_type":
                return (0, b"servo_type:servo_v4p1_with_ccd_gsc_nt\n")
            if cmd == "dut-control ec_uart_pty cpu_uart_pty gsc_uart_pty":
                return (
                    0,
                    b"ec_uart_pty:/dev/pts/10\n"
                    b"cpu_uart_pty:/dev/pts/12\n"
                    b"gsc_uart_pty:/dev/pts/8\n",
                )
            if cmd == "dut-control fpmcu_uart_pty":
                return (0, b"fpmcu_uart_pty:/dev/pts/14\n")
            if (
                cmd == "dut-control active.ec_uart_pty "
                "active.cpu_uart_pty active.gsc_uart_pty"
            ):
                return (
                    0,
                    b"active.ec_uart_pty:/dev/pts/10\n"
                    b"active.cpu_uart_pty:/dev/pts/12\n"
                    b"active.gsc_uart_pty:/dev/pts/8\n",
                )
            if cmd == "dut-control active.fpmcu_uart_pty":
                return (0, b"active.fpmcu_uart_pty:/dev/pts/14\n")
            return (0, b"")

        self.mock_container.exec_run.side_effect = exec_run_side_effect

        with (
            patch.object(sys, "argv", test_args),
            patch("builtins.print") as mock_print,
        ):
            start_servod.main()

            printed_text = "\n".join(
                " ".join(str(a) for a in call.args)
                for call in mock_print.call_args_list
            )
            self.assertIn("Main console locations:", printed_text)
            self.assertIn("ec_uart_pty:/dev/pts/10", printed_text)
            self.assertIn("fpmcu_uart_pty:/dev/pts/14", printed_text)
            self.assertIn("\nActive console locations:", printed_text)
            self.assertIn("active.ec_uart_pty:/dev/pts/10", printed_text)
            self.assertIn("active.fpmcu_uart_pty:/dev/pts/14", printed_text)


if __name__ == "__main__":
    unittest.main()
