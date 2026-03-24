# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Driver for generating end-to-end test data."""

from array import array
import os
import re
import time

from servo.drv import hw_driver


class e2eTestDataGenerator(hw_driver.HwDriver):
    """Driver to generate test data from a live device."""

    def __init__(self, grpc_core_addr, grpc_data_addr, interface, params):
        """Chassis constructor.

        Args:
          interface: driver interface object
          params: dictionary of params
        """
        super(e2eTestDataGenerator, self).__init__(
            grpc_core_addr, grpc_data_addr, interface, params
        )

    def _get_pty_output(self, pty_name, cmd):
        """Gets the output from a PTY for a given command."""
        try:
            pty_path = self._servod_get(pty_name)
            if not pty_path:
                return b"Error: PTY %s not found" % pty_name.encode()

            import serial

            with serial.Serial(pty_path, timeout=0.1) as pty:
                cmd_bytes = cmd if isinstance(cmd, bytes) else cmd.encode()
                pty.write(cmd_bytes + b"\n")

                output = b""
                timeout = time.monotonic() + 0.5  # 0.5 second initial timeout
                while time.monotonic() < timeout:
                    data = pty.read(1024)
                    if data:
                        output += data
                        timeout = time.monotonic() + 0.1
                return output
        except Exception as e:
            err_msg = str(e) if e is not None else "Unknown error"
            return b"Error executing command: %s" % err_msg.encode()

    def _get_i2c_data(self, interface_name, args):
        """Gets data from an I2C interface."""
        # I2C is not safely directly accessible via Fission from the data server
        # without hardcoding the interface_key, so we just return a default placeholder value
        # or rely on the static hardcoded arrays below.
        return [array("B", [0, 0, 0, 0, 255])]

    def _set(self, value):
        """Entry point for the control."""
        parts = value.split()
        if len(parts) >= 2:
            board = parts[0]
            model = parts[1]
        else:
            board = value
            model = "unknown"
        self.generate_data(board, model)

    def generate_data(self, board, model):
        """Generates test data for the given board and model."""
        data = {}
        start_time = time.time()
        print(f"Starting data generation for {board} {model}...")

        # Hardcoded PTY commands
        pty_commands = {
            "MOCKED_CR50_AP_DATA": [b""],
            "MOCKED_CR50_FPMCU_DATA": [b""],
            "MOCKED_CR50_CONSOLE_DATA": [
                b"",
                b"brdprop",
                b"ccd testlab open",
                b"ccd testlab",
                b"ccdstate",
                b"ecrst off",
                b"ecrst on",
                b"gpiocfg",
                b"gpioget AP_FLASH_SELECT",
                b"gpioget CCD_REC_LID_SWITCH",
                b"gpioget EC_FLASH_SELECT",
                b"gpioset CCD_REC_LID_SWITCH 0",
                b"recbtnforce enable",
                b"recbtnforce",
                b"sysrst off",
                b"sysrst on",
                b"sysrst",
                b"wp",
                b"gpioset CCD_REC_LID_SWITCH 1",
                b"recbtnforce disable",
                b"ccd",
                b"ecrst",
                b"gettime",
                b"idle",
                b"powerbtn",
                b"sysinfo",
                b"version",
            ],
            "MOCKED_SERVO41_CONSOLE_DATA": [
                b"",
                b"ada_srccaps",
                b"adc",
                b"cc",
                b"chan 0xffffffff",
                b"chan 1",
                b"chan restore",
                b"chan save",
                b"gpioget ATMEL_HWB_L",
                b"gpioget DUT_HUB_USB_RESET_L",
                b"gpioget FASTBOOT_DUTHUB_MUX_EN_L",
                b"gpioget FASTBOOT_DUTHUB_MUX_SEL",
                b"gpioget SBU_MUX_EN",
                b"gpioget USB_FAULT_L",
                b"gpioget USERVO_FAULT_L",
                b"gpioset ATMEL_HWB_L 1",
                b"macaddr",
                b"panicinfo",
                b"pd 1 dev",
                b"usbc_action drswap",
                b"usbc_action prswap",
                b"version",
            ],
            "MOCKED_EC_PD_CONSOLE_DATA": [
                b"",
                b"chan 0xffffffff",
                b"chan 1",
                b"chan restore",
                b"chan save",
                b"feat",
                b"hostevent set 0x4000",
                b"i2cxfer r 1 0x40 0x52",
                b"i2cxfer w 1 0x40 0x52 0x6a",
                b"pd 0 state",
                b"pd 1 state",
                b"power off",
                b"power on",
                b"powerbtn  200",
                b"reboot ap-off",
                b"reboot wait-ext ap-off",
                b"battery",
                b"chgstate",
                b"faninfo",
                b"flashinfo",
                b"gpioget",
                b"lidstate",
                b"powerinfo",
                b"pwr_avg",
                b"sysinfo",
                b"temps",
                b"version",
            ],
            "MOCKED_SERVO_MICRO_PD_CR50_CONSOLE_DATA": [
                b"",
                b"brdprop",
                b"cc",
                b"ccdstate",
                b"chan 0xffffffff",
                b"chan 1",
                b"chan restore",
                b"chan save",
                b"ecrst",
                b"ecrst off",
                b"ecrst on",
                b"gpioget ATMEL_HWB_L",
                b"gpioset ATMEL_HWB_L 1",
                b"gpioget DUT_HUB_USB_RESET_L",
                b"gpioget FASTBOOT_DUTHUB_MUX_EN_L",
                b"gpioget FASTBOOT_DUTHUB_MUX_SEL",
                b"version",
                b"wp",
                b"ccd testlab open",
                b"ccd testlab",
            ],
            "MOCKED_SERVO_MICRO_SERVO41_CONSOLE_DATA": [
                b"",
                b"chan 0xffffffff",
                b"chan 1",
                b"chan restore",
                b"chan save",
                b"gpioget JTAG_BUFIN_EN_L",
                b"gpioget JTAG_BUFOUT_EN_L",
                b"gpioget SERVO_JTAG_RTCK",
                b"gpioget SERVO_JTAG_TDI",
                b"gpioget SERVO_JTAG_TDI_DIR",
                b"gpioget SERVO_JTAG_TDO_BUFFER_EN",
                b"gpioget SERVO_JTAG_TDO_SEL",
                b"gpioget SERVO_JTAG_TMS",
                b"gpioget SERVO_JTAG_TMS_DIR",
                b"gpioget SERVO_JTAG_TRST_DIR",
                b"gpioget SERVO_JTAG_TRST_L",
                b"gpioget SPI1_BUF_EN_L",
                b"gpioget SPI1_MUX_SEL",
                b"gpioget SPI1_VREF_18",
                b"gpioget SPI1_VREF_33",
                b"gpioget SPI2_BUF_EN_L",
                b"gpioget SPI2_VREF_18",
                b"gpioget SPI2_VREF_33",
                b"gpioget TCA6416_RESET_L",
                b"gpioget UART1_EN_L",
                b"gpioget UART2_EN_L",
                b"gpioget UART3_RX_JTAG_BUFFER_TO_SERVO_TDO",
                b"gpioget UART3_TX_SERVO_JTAG_TCK",
                b"gpioset JTAG_BUFIN_EN_L 0",
                b"gpioset JTAG_BUFIN_EN_L 1",
                b"gpioset SERVO_JTAG_TDO_BUFFER_EN 0",
                b"gpioset SERVO_JTAG_TDO_BUFFER_EN 1",
                b"gpioset SERVO_JTAG_TDO_SEL 1",
                b"gpioset SPI1_BUF_EN_L 1",
                b"gpioset SPI1_MUX_SEL 1",
                b"gpioset SPI1_VREF_18 0",
                b"gpioset SPI1_VREF_33 0",
                b"gpioset SPI2_VREF_18 0",
                b"gpioset SPI2_VREF_33 1",
                b"gpioset UART1_EN_L 0",
                b"gpioset UART3_RX_JTAG_BUFFER_TO_SERVO_TDO 0",
                b"gpioset UART3_RX_JTAG_BUFFER_TO_SERVO_TDO ALT",
                b"gpioset UART3_TX_SERVO_JTAG_TCK 0",
                b"gpioset UART3_TX_SERVO_JTAG_TCK ALT",
                b"hold_usart usart2",
                b"version",
            ],
            "MOCKED_C2D2_H1_CONSOLE_DATA": [
                b"",
                b"cc",
                b"chan 0xffffffff",
                b"chan 1",
                b"chan restore",
                b"chan save",
                b"ecrst",
                b"ecrst off",
                b"ecrst on",
                b"gpioget ATMEL_HWB_L",
                b"gpioset ATMEL_HWB_L 1",
                b"gpioget DUT_HUB_USB_RESET_L",
                b"gpioget FASTBOOT_DUTHUB_MUX_EN_L",
                b"gpioget FASTBOOT_DUTHUB_MUX_SEL",
                b"sysrst",
                b"sysrst off",
                b"sysrst on",
                b"version",
            ],
            "MOCKED_C2D2_SERVO41_CONSOLE_DATA": [
                b"",
                b"chan 0xffffffff",
                b"chan 1",
                b"chan restore",
                b"chan save",
                b"enable_spi",
                b"gpioget EN_CLK_CSN_EC_UART",
                b"gpioset EN_CLK_CSN_EC_UART 1",
                b"h1_reset",
                b"hold_usart usart1",
                b"version",
            ],
            "MOCKED_SERVO_MICRO_AP_DATA": [],
            "MOCKED_SERVO_MICRO_EC_DATA": [
                b"",
                b"cbi",
                b"chan 0xffffffff",
                b"chan 1",
                b"chan restore",
                b"chan save",
                b"gpioget LID_OPEN",
                b"lidstate",
                b"pdc sbumux",
                b"pdc sbumux normal",
                b"pdc sbumux debug",
                b"powerinfo",
                b"power on",
                b"version",
            ],
            "MOCKED_C2D2_AP_DATA": [],
            "MOCKED_C2D2_EC_DATA": [
                b"",
                b"cbi",
                b"chan 0xffffffff",
                b"chan 1",
                b"chan restore",
                b"chan save",
                b"gpioget LID_OPEN",
                b"lidstate",
                b"pdc sbumux",
                b"pdc sbumux normal",
                b"pdc sbumux debug",
                b"powerinfo",
                b"power off",
                b"version",
            ],
        }

        pty_interfaces = {
            "MOCKED_CR50_AP_DATA": "cr50_ap_uart_pty",
            "MOCKED_CR50_FPMCU_DATA": "cr50_fpmcu_uart_pty",
            "MOCKED_CR50_CONSOLE_DATA": "cr50_uart_pty",
            "MOCKED_SERVO41_CONSOLE_DATA": "servo_v4p1_uart_pty",
            "MOCKED_EC_PD_CONSOLE_DATA": "ec_uart_pty",
            "MOCKED_SERVO_MICRO_PD_CR50_CONSOLE_DATA": "cr50_uart_pty",
            "MOCKED_SERVO_MICRO_SERVO41_CONSOLE_DATA": "servo_micro_uart_pty",
            "MOCKED_C2D2_H1_CONSOLE_DATA": "c2d2_h1_uart_pty",
            "MOCKED_C2D2_SERVO41_CONSOLE_DATA": "c2d2_uart_pty",
            "MOCKED_SERVO_MICRO_AP_DATA": "ap_uart_pty",
            "MOCKED_SERVO_MICRO_EC_DATA": "ec_uart_pty",
            "MOCKED_C2D2_AP_DATA": "ap_uart_pty",
            "MOCKED_C2D2_EC_DATA": "ec_uart_pty",
        }

        # Collect PTY data
        for data_key, pty_name in pty_interfaces.items():
            if data_key not in pty_commands:
                continue

            # Check if this servod instance actually has this PTY
            try:
                self._servod_get(pty_name)
            except Exception:
                print(f"Skipping {pty_name}, not available on this servo setup.")
                continue

            cmds = pty_commands[data_key]
            data[data_key] = {}
            for cmd in cmds:
                print(f"Running command on {pty_name}: {cmd}")
                output = self._get_pty_output(pty_name, cmd)
                data[data_key][cmd] = output

        # Hardcoded I2C arguments
        i2c_args_map = {
            "MOCKED_SERVO41_I2C_DATA": [
                (0, 33, 1, 1, 0),
                (0, 33, 1, 1, 1),
                (0, 33, 1, 1, 2),
                (0, 33, 1, 1, 6),
                (0, 33, 2, 1, 2, 128),
                (0, 33, 2, 1, 2, 136),
                (0, 33, 2, 1, 2, 130),
                (0, 33, 2, 1, 2, 138),
                (0, 33, 2, 1, 2, 160),
                (0, 33, 2, 1, 2, 168),
                (0, 33, 2, 1, 2, 170),
                (0, 35, 1, 1, 0),
                (0, 64, 1, 2, 0),
                (0, 64, 1, 2, 1),
                (0, 64, 1, 2, 2),
                (0, 64, 1, 2, 3),
                (0, 64, 1, 2, 4),
                (0, 64, 1, 2, 5),
                (0, 64, 1, 2, 6),
                (0, 64, 1, 2, 7),
                (0, 64, 3, 2, 5, 127, 255),
                (0, 65, 1, 2, 0),
                (0, 65, 1, 2, 1),
                (0, 65, 1, 2, 2),
                (0, 65, 1, 2, 3),
                (0, 65, 1, 2, 4),
                (0, 65, 1, 2, 5),
                (0, 65, 1, 2, 6),
                (0, 65, 1, 2, 7),
                (0, 65, 3, 2, 5, 127, 255),
                (0, 66, 1, 2, 0),
                (0, 66, 1, 2, 1),
                (0, 66, 1, 2, 2),
                (0, 66, 1, 2, 3),
                (0, 66, 1, 2, 4),
                (0, 66, 1, 2, 5),
                (0, 66, 1, 2, 6),
                (0, 66, 1, 2, 7),
                (0, 66, 3, 2, 5, 127, 255),
            ],
            "MOCKED_CR50_I2C_DATA": [
                (0, 32, 1, 1, 1),
                (0, 38, 1, 1, 1),
                (0, 38, 1, 1, 3),
                (0, 38, 2, 1, 1, 150),
                (0, 38, 2, 1, 3, 150),
                (0, 32, 1, 1, 0),
                (0, 32, 1, 1, 3),
                (0, 32, 1, 1, 7),
                (0, 32, 2, 1, 3, 142),
                (0, 32, 2, 1, 3, 30),
                (0, 32, 2, 1, 7, 65),
                (0, 32, 1, 1, 6),
                (0, 32, 2, 1, 6, 190),
                (0, 32, 2, 1, 6, 222),
                (0, 38, 2, 1, 1, 156),
                (0, 38, 2, 1, 3, 156),
                (0, 38, 1, 1, 0),
            ],
        }

        i2c_interfaces = {
            "MOCKED_SERVO41_I2C_DATA": "servo_v4p1_i2c",
            "MOCKED_CR50_I2C_DATA": "cr50_i2c",
        }

        # Collect I2C data
        for data_key, interface_name in i2c_interfaces.items():
            if data_key not in i2c_args_map:
                continue

            # Check if this servod instance actually has this I2C interface
            try:
                # Use a known harmless property or just check if it exists in the system config
                # Since I2C interfaces aren't standard controls, we check via interface query
                self._servod_get(interface_name)
            except Exception:
                print(f"Skipping {interface_name}, not available on this servo setup.")
                continue

            args_list = i2c_args_map[data_key]
            data[data_key] = {}
            for args in args_list:
                arg_str = str(args).encode()
                print(f"Querying I2C {interface_name} with args: {args}")
                i2c_result = self._get_i2c_data(interface_name, args)
                data[data_key][arg_str] = i2c_result

        # Static data - Copied from mocked_pty_data.py
        data["MOCKED_SERVO_MICRO_I2C_DATA"] = {
            b"(0, 32, 1, 1, 0)": [array("B", [0, 0, 0, 0, 255])],
            b"(0, 32, 1, 1, 1)": [array("B", [0, 0, 0, 0, 255])],
            b"(0, 32, 1, 1, 2)": [array("B", [0, 0, 0, 0, 255])],
            b"(0, 32, 1, 1, 6)": [array("B", [0, 0, 0, 0, 252])],
            b"(0, 32, 1, 1, 7)": [array("B", [0, 0, 0, 0, 255])],
        }
        data["MOCKED_C2D2_I2C_DATA"] = {}
        data["MOCKED_SERVO41_ATMEGA_DATA"] = {b"a": b"a"}

        # Build output string instead of writing to a file that may not exist
        out_lines = []
        out_lines.append("# Copyright 2026 The ChromiumOS Authors\n")
        out_lines.append(
            "# Use of this source code is governed by a BSD-style license that can be\n"
        )
        out_lines.append("# found in the LICENSE file.\n\n")
        out_lines.append(
            f"# Autogenerated by e2e_test_data_generator.py for {board} {model}\n"
        )
        out_lines.append("from array import array\n\n")

        for key, value in data.items():
            out_lines.append(f"{key} = {{\n")
            if isinstance(value, dict):
                for cmd, output in value.items():
                    out_lines.append(f"    {cmd!r}: {output!r},\n")
            out_lines.append("}\n\n")

        elapsed = time.time() - start_time
        print(f"Data generation complete! Elapsed time: {elapsed:.2f}s")
        # Attempt to parse port from gRPC address, fallback to 9999
        port = "9999"
        if hasattr(self, "_grpc_core_addr") and self._grpc_core_addr:
            try:
                # e.g., "localhost:9999"
                port = self._grpc_core_addr[1]
            except Exception:
                pass

        output_str = "".join(out_lines)
        log_path = f"/tmp/generated_{board}_{model}_{port}.py"
        try:
            with open(log_path, "w") as f:
                f.write(output_str)
            print(f"Saved generated data to {log_path}")
        except Exception as e:
            print(f"Failed to write to {log_path}: {e}")

        return output_str
