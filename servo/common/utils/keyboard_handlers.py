# Copyright 2013 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Expects to be run in an environment with sudo and no interactive password
# prompt, such as within the ChromiumOS development chroot.

# pylint: skip-file

import json
import logging
import time

from google.protobuf import json_format
from google.protobuf import struct_pb2
import serial

from servo.common.exceptions import HwDriverError
from servo.common.grpc_client import GrpcClient
from servo.common.proto import servo_dev_grpc
from servo.common.utils import json_utils


class InvalidJsonConfigError(HwDriverError):
    """Exception class for JSON errors."""


class _HandlerTemplate:
    """Template for all handlers to support common open/close operations."""

    def __init__(self, grpc_core_addr):
        # The base subclasses need to handle opening themselves up.
        self._logger = logging.getLogger(type(self).__name__)
        self._open = False
        # Create a gRPC channel to the specified host and port
        if grpc_core_addr is not None:
            grpc_core_host, grpc_core_port = grpc_core_addr
            channel = GrpcClient.create_grpc_channel(grpc_core_host, grpc_core_port)
            self._driver_client = servo_dev_grpc.ServoService(channel)

    def _servod_get(self, control):
        """Get the value of the given control with proper prefix."""
        service = self._driver_client.GetServo(control_name=control)
        return service.response

    def _servod_set(self, control, value):
        """Set the value of the given control with proper prefix."""
        val_pb = json_utils.wrap_value(value)
        self._driver_client.SetServo(control_name=control, value=val_pb)

    def is_open(self):
        """Query whether keyboard handler is open for use."""
        return self._open

    def open(self):
        """Open the keyboard handler for use."""
        self._open = True

    def close(self):
        """Close the keyboard handler for use."""
        self._open = False


class NoopHandler(_HandlerTemplate):
    """Noop keyboard handler that always keeps the keyboard closed.

    For some use-cases a proper keyboard handler cannot be initialized e.g.
    missing hardware. If those cases are not necessarily blocking, use a
    NoopHandler. It will warn every time open/close are being used that
    they are noops, but will not issue an exception.

    As open open() and close() just print warnings, |self._open| stays False
    and is_open() always returns False
    """

    _BASE_WRN = (
        "Using a noop keyboard handler. Check logs to see why it is "
        "in use and address issue if full keyboard functionality is "
        "needed."
    )

    def open(self):
        """Print warning only."""
        self._logger.warning(self._BASE_WRN)

    def close(self):
        """Print warning only."""
        self._logger.warning(self._BASE_WRN)


class _BaseHandler(_HandlerTemplate):
    """Base class for keyboard handlers."""

    # Power button press delays in seconds.
    #
    # The EC specification says that 8.0 seconds should be enough
    # for the long power press.  However, some platforms need a bit
    # more time.  Empirical testing has found these requirements:
    #   Alex: 8.2 seconds
    #   ZGB:  8.5 seconds
    # The actual value is set to the largest known necessary value.
    #
    # TODO(jrbarnette) Being generous is the right thing to do for
    # existing platforms, but if this code is to be used for
    # qualification of new hardware, we should be less generous.
    LONG_DELAY = 8.5
    SHORT_DELAY = 0.2
    NORMAL_TRANSITION_DELAY = 1.2

    # Maximum number of times to re-read power button on release.
    RELEASE_RETRY_MAX = 5

    # Default minimum time interval between 'press' and 'release'
    # keyboard events.
    SERVO_KEY_PRESS_DELAY = 0.1

    KEY_MATRIX = None

    def __init__(self, grpc_core_addr):
        """Sets up the servo communication infrastructure."""
        super().__init__(grpc_core_addr)
        self._arb_keys = []

    def power_long_press(self):
        """Simulate a long power button press."""
        # After a long power press, the EC may ignore the next power
        # button press (at least on Alex).  To guarantee that this
        # won't happen, we need to allow the EC one second to
        # collect itself.
        # TODO(waihong): Make this delay as one of board specific configs.
        self.power_key(self.LONG_DELAY)
        time.sleep(1.0)

    def power_normal_press(self):
        """Simulate a normal power button press."""
        self.power_key()

    def power_short_press(self):
        """Simulate a short power button press."""
        self.power_key(self.SHORT_DELAY)

    def power_key(self, press_secs=""):
        """Simulate a power button press.

        Args:
          press_secs: Time in seconds to simulate the keypress.
        """
        if press_secs == "":
            press_secs = self.NORMAL_TRANSITION_DELAY

        # Check if pwr_button control available, by setting it to
        # its current value. Use pwr_button control by default.
        # Otherwise, use pwr_button_hold which calls a single EC
        # console command to toggle power button, for the CCD case.
        is_ccd = self._servod_get("servo_class") == "ccd"

        self._logger.debug("power_key is_ccd: %r", is_ccd)
        if is_ccd:
            use_hold_command = True
        else:
            try:
                value = self._servod_get("pwr_button")
                self._servod_set("pwr_button", value)
                use_hold_command = False
            except HwDriverError:
                use_hold_command = True

        self._logger.info(
            "Using power_key %s", "hold" if use_hold_command else "press/release"
        )

        if use_hold_command:
            self.power_key_hold(press_secs)
        else:
            self.power_key_press_release(press_secs)

    def power_key_hold(self, press_secs):
        """Simulate a power button by a single EC console command.

        Args:
          press_secs: Time in seconds to simulate the keypress.
        """
        # Convert to milliseconds
        self._servod_set("pwr_button_hold", int(press_secs * 1000))

    def power_key_press_release(self, press_secs):
        """Simulate a power button by setting it to press and then release.

        Args:
          press_secs: Time in seconds to simulate the keypress.
        """
        self._logger.info("Pressing power button for %.4f secs", press_secs)
        self._driver_client.SetGetAll(
            ["pwr_button:press", "sleep:%.4f" % press_secs, "pwr_button:release"]
        )
        # TODO(tbroch) Different systems have different release times on the
        # power button that this loop addresses.  Longer term we may want to
        # make this delay platform specific.
        retry = 1
        while True:
            value = self._servod_get("pwr_button")
            if value == "release" or retry > self.RELEASE_RETRY_MAX:
                break
            self._logger.info("Waiting for pwr_button to release, retry %d.", retry)
            retry += 1
            time.sleep(self.SHORT_DELAY)

    def ctrl_d(self, press_secs=""):
        """Simulate Ctrl-d simultaneous button presses."""
        raise NotImplementedError()

    def ctrl_f(self, press_secs=""):
        """Simulate Ctrl-f simultaneous button presses."""
        raise NotImplementedError()

    def ctrl_r(self, press_secs=""):
        """Simulate Ctrl-r simultaneous button presses."""
        raise NotImplementedError()

    def ctrl_u(self, press_secs=""):
        """Simulate Ctrl-u simultaneous button presses."""
        raise NotImplementedError()

    def ctrl_s(self, press_secs=""):
        """Simulate Ctrl-s simultaneous button presses."""
        raise NotImplementedError()

    def ctrl_enter(self, press_secs=""):
        """Simulate Ctrl-enter simultaneous button presses."""
        raise NotImplementedError()

    def ctrl_key(self, press_secs=""):
        """Simulate Enter key button press."""
        raise NotImplementedError()

    def alt_f5(self, press_secs=""):
        """Simulate Alt-F5 simultaneous button presses."""
        raise NotImplementedError()

    def alt_f6(self, press_secs=""):
        """Simulate Alt-F6 simultaneous button presses."""
        raise NotImplementedError()

    def arrow_up(self, press_secs=""):
        """Simulate ArrowUp key button press."""
        raise NotImplementedError()

    def arrow_down(self, press_secs=""):
        """Simulate ArrowDown key button press."""
        raise NotImplementedError()

    def enter_key(self, press_secs=""):
        """Simulate Enter key button press."""
        raise NotImplementedError()

    def refresh_key(self, press_secs=""):
        """Simulate Refresh key (F3) button press."""
        raise NotImplementedError()

    def ctrl_refresh_key(self, press_secs=""):
        """Simulate Ctrl and Refresh (F3) simultaneous press.

        This key combination is an alternative of Space key.
        """
        raise NotImplementedError()

    def imaginary_key(self, press_secs=""):
        """Simulate imaginary key button press.

        Maps to a key that doesn't physically exist.
        """
        raise NotImplementedError()

    def sysrq_x(self, press_secs=""):
        """Simulate Alt VolumeUp X simultaneous press.

        This key combination is the kernel system request (sysrq) X.
        """
        raise NotImplementedError()

    def sysrq_r(self, press_secs=""):
        """Simulate Alt VolumeUp R simultaneous press.

        This key combination is the kernel system request (sysrq) R.
        """
        raise NotImplementedError()

    def arb_key(self, press_secs=""):
        """Simulate an arbitrary key press."""
        raise NotImplementedError()

    def arb_key_config(self, key):
        """Set key for an arbitrary key press."""
        self._arb_keys = [key]

    def arb_keys_config(self, json_list):
        """Set multiple keys for an arbitrary key press in JSON."""
        key_list = json.loads(json_list)
        if key_list is None:
            self._arb_keys = []
        elif isinstance(key_list, list):
            for x in key_list:
                if not isinstance(x, str):
                    raise InvalidJsonConfigError(
                        f"Cannot parse {json_list} as a list of keys"
                    )
            self._arb_keys = key_list
        else:
            raise InvalidJsonConfigError(f"Cannot parse {json_list} as a list of keys")


class MatrixKeyboardHandler(_BaseHandler):
    """Matrix keyboard handler for DUT with internal keyboards.

    It works on mostly all devices, with or without Chrome EC.
    """

    KEY_MATRIX = {
        "ctrl_refresh": ["0", "0", "0", "1"],
        "ctrl_d": ["0", "1", "0", "0"],
        "d": ["0", "1", "1", "1"],
        "ctrl_enter": ["1", "0", "0", "0"],
        "enter": ["1", "0", "1", "1"],
        "ctrl": ["1", "1", "0", "0"],
        "refresh": ["1", "1", "0", "1"],
        "unused": ["1", "1", "1", "0"],
        "none": ["1", "1", "1", "1"],
    }

    def __init__(self, grpc_core_addr):
        """Sets up the servo communication infrastructure."""
        super().__init__(grpc_core_addr)
        self.open()

    def _press_keys(self, key):
        """Simulate button presses.

        Note, key presses will remain on indefinitely. See
            _press_and_release_keys for release procedure.
        """
        (m1_a1, m1_a0, m2_a1, m2_a0) = self.KEY_MATRIX[key]
        self._driver_client.SetGetAll(
            [
                "kbd_m2_a0:%s" % m2_a0,
                "kbd_m2_a1:%s" % m2_a1,
                "kbd_m1_a0:%s" % m1_a0,
                "kbd_m1_a1:%s" % m1_a1,
                "kbd_en:on",
            ]
        )

    def _press_and_release_keys(self, key, press_secs=""):
        """Simulate button presses and release."""
        if press_secs == "":
            press_secs = self.SERVO_KEY_PRESS_DELAY
        self._press_keys(key)
        time.sleep(press_secs)
        self._servod_set("kbd_en", "off")

    def ctrl_d(self, press_secs=""):
        """Simulate Ctrl-d simultaneous button presses."""
        self._press_and_release_keys("ctrl_d", press_secs)

    def ctrl_enter(self, press_secs=""):
        """Simulate Ctrl-enter simultaneous button presses."""
        self._press_and_release_keys("ctrl_enter", press_secs)

    def ctrl_key(self, press_secs=""):
        """Simulate Enter key button press."""
        self._press_and_release_keys("ctrl", press_secs)

    def enter_key(self, press_secs=""):
        """Simulate Enter key button press."""
        self._press_and_release_keys("enter", press_secs)

    def refresh_key(self, press_secs=""):
        """Simulate Refresh key (F3) button press."""
        self._press_and_release_keys("refresh", press_secs)

    def ctrl_refresh_key(self, press_secs=""):
        """Simulate Ctrl and Refresh (F3) simultaneous press.

        This key combination is an alternative of Space key.
        """
        self._press_and_release_keys("ctrl_refresh", press_secs)

    def imaginary_key(self, press_secs=""):
        """Simulate imaginary key button press.

        Maps to a key that doesn't physically exist.
        """
        self._press_and_release_keys("unused", press_secs)


class StoutHandler(MatrixKeyboardHandler):
    """Stout keyboard handler for DUT with internal keyboards."""

    KEY_MATRIX = {
        "ctrl_d": ["0", "0", "0", "1"],
        "d": ["0", "0", "1", "1"],
        "unused": ["0", "1", "1", "1"],
        "rec_mode": ["1", "0", "0", "0"],
        "ctrl_enter": ["1", "0", "0", "1"],
        "enter": ["1", "0", "1", "1"],
        "ctrl": ["1", "1", "0", "1"],
        "refresh": ["1", "1", "1", "0"],
        "ctrl_refresh": ["1", "1", "1", "1"],
        "none": ["1", "1", "1", "1"],
    }

    def __init__(self, grpc_core_addr):
        """Sets up the servo communication infrastructure."""
        super().__init__(grpc_core_addr)
        self.open()


class ParrotHandler(MatrixKeyboardHandler):
    """Parrot keyboard handler for DUT with internal keyboards."""

    KEY_MATRIX = {
        "ctrl_d": ["0", "0", "1", "0"],
        "d": ["0", "0", "1", "1"],
        "ctrl_enter": ["0", "1", "1", "0"],
        "enter": ["0", "1", "1", "1"],
        "ctrl_refresh": ["1", "0", "0", "1"],
        "unused": ["1", "1", "0", "0"],
        "refresh": ["1", "1", "0", "1"],
        "ctrl": ["1", "1", "1", "0"],
        "none": ["1", "1", "1", "1"],
    }

    def __init__(self, grpc_core_addr):
        """Sets up the servo communication infrastructure."""
        super().__init__(grpc_core_addr)
        self.open()


class ChromeECHandler(_BaseHandler):
    """Chrome EC keyboard handler for DUT with Chrome EC."""

    # en-US key matrix (from "kb membrane pin matrix.pdf")
    KEY_MATRIX = {
        # key: (row, col)
        "`": (3, 1),
        "1": (6, 1),
        "2": (6, 4),
        "3": (6, 2),
        "4": (6, 3),
        "5": (3, 3),
        "6": (3, 6),
        "7": (6, 6),
        "8": (6, 5),
        "9": (6, 9),
        "0": (6, 8),
        "-": (3, 8),
        "=": (0, 8),
        "q": (7, 1),
        "w": (7, 4),
        "e": (7, 2),
        "r": (7, 3),
        "t": (2, 3),
        "y": (2, 6),
        "u": (7, 6),
        "i": (7, 5),
        "o": (7, 9),
        "p": (7, 8),
        "[": (2, 8),
        "]": (2, 5),
        "\\": (3, 11),
        "a": (4, 1),
        "s": (4, 4),
        "d": (4, 2),
        "f": (4, 3),
        "g": (1, 3),
        "h": (1, 6),
        "j": (4, 6),
        "k": (4, 5),
        "l": (4, 9),
        ";": (4, 8),
        "'": (1, 8),
        "z": (5, 1),
        "x": (5, 4),
        "c": (5, 2),
        "v": (5, 3),
        "b": (0, 3),
        "n": (0, 6),
        "m": (5, 6),
        ",": (5, 5),
        ".": (5, 9),
        "/": (5, 8),
        " ": (5, 11),
        "<right>": (6, 12),
        "<alt_r>": (0, 10),
        "<down>": (6, 11),
        "<tab>": (2, 1),
        "<f10>": (0, 4),
        "<shift_r>": (7, 7),
        "<ctrl_r>": (4, 0),
        "<esc>": (1, 1),
        "<backspace>": (1, 11),
        "<f2>": (3, 2),
        "<alt_l>": (6, 10),
        "<ctrl_l>": (2, 0),
        "<f1>": (0, 2),
        "<search>": (0, 1),
        "<f3>": (2, 2),
        "<f4>": (1, 2),
        "<f5>": (3, 4),
        "<f6>": (2, 4),
        "<f7>": (1, 4),
        "<f8>": (2, 9),
        "<f9>": (1, 9),
        "<up>": (7, 11),
        "<shift_l>": (5, 7),
        "<enter>": (4, 11),
        "<left>": (7, 12),
    }

    def __init__(self, grpc_core_addr):
        """Sets up the servo communication infrastructure.

        @param servo: A Servo object representing
                           the host running servod.
        """
        super().__init__(grpc_core_addr)
        base_board = self._driver_client.GetBaseBoard().response
        if base_board:
            self._ec_uart_regexp = base_board + "_ec_uart_regexp"
            self._ec_uart_cmd = base_board + "_ec_uart_cmd"
        else:
            self._ec_uart_regexp = "ec_uart_regexp"
            self._ec_uart_cmd = "ec_uart_cmd"
        self.open()

    def _send_command(self, command):
        """Send command through UART.

        This function opens UART pty when called, and then command is sent
        through UART.

        @param command: The command to send.
        """
        self._servod_set(self._ec_uart_regexp, "None")
        self._servod_set(self._ec_uart_cmd, command)

    def _press_and_release_keys(self, keys, press_secs=""):
        """Simulate a key combination press and release.

        The key combination (multiple keys) are all pressed and then
        all released.

        @param keys: A list of key names, which are the keys of KEY_MATRIX.
        """
        if press_secs == "":
            press_secs = self.SERVO_KEY_PRESS_DELAY
        for key in keys:
            # Send EC command: kbpress col row pressed
            self._send_command(
                "kbpress %d %d 1" % (self.KEY_MATRIX[key][1], self.KEY_MATRIX[key][0])
            )
        time.sleep(press_secs)
        for key in keys:
            # Send EC command: kbpress col row pressed
            self._send_command(
                "kbpress %d %d 0" % (self.KEY_MATRIX[key][1], self.KEY_MATRIX[key][0])
            )

    def ctrl_d(self, press_secs=""):
        """Simulate Ctrl-d simultaneous button presses."""
        self._press_and_release_keys(["<ctrl_l>", "d"], press_secs)

    def ctrl_f(self, press_secs=""):
        """Simulate Ctrl-f simultaneous button presses."""
        self._press_and_release_keys(["<ctrl_l>", "f"], press_secs)

    def ctrl_r(self, press_secs=""):
        """Simulate Ctrl-r simultaneous button presses."""
        self._press_and_release_keys(["<ctrl_l>", "r"], press_secs)

    def ctrl_u(self, press_secs=""):
        """Simulate Ctrl-u simultaneous button presses."""
        self._press_and_release_keys(["<ctrl_l>", "u"], press_secs)

    def ctrl_s(self, press_secs=""):
        """Simulate Ctrl-s simultaneous button presses."""
        self._press_and_release_keys(["<ctrl_l>", "s"], press_secs)

    def ctrl_enter(self, press_secs=""):
        """Simulate Ctrl-enter simultaneous button presses."""
        self._press_and_release_keys(["<enter>"], press_secs)

    def ctrl_key(self, press_secs=""):
        """Simulate Enter key button press."""
        self._press_and_release_keys(["<ctrl_l>"], press_secs)

    def alt_f5(self, press_secs=""):
        """Simulate Alt-F5 simultaneous button presses."""
        self._press_and_release_keys(["<alt_l>", "<f5>"], press_secs)

    def alt_f6(self, press_secs=""):
        """Simulate Alt-F6 simultaneous button presses."""
        self._press_and_release_keys(["<alt_l>", "<f6>"], press_secs)

    def arrow_up(self, press_secs=""):
        """Simulate ArrowUp key button press."""
        self._press_and_release_keys(["<up>"], press_secs)

    def arrow_down(self, press_secs=""):
        """Simulate ArrowDown key button press."""
        self._press_and_release_keys(["<down>"], press_secs)

    def enter_key(self, press_secs=""):
        """Simulate Enter key button press."""
        self._press_and_release_keys(["<enter>"], press_secs)

    def refresh_key(self, press_secs=""):
        """Simulate Refresh key (F3) button press."""
        self._press_and_release_keys(["<f3>"], press_secs)

    def ctrl_refresh_key(self, press_secs=""):
        """Simulate Ctrl and Refresh (F3) simultaneous press.

        This key combination is an alternative of Space key.
        """
        self._press_and_release_keys(["<ctrl_l>", "<f3>"], press_secs)

    def sysrq_x(self, press_secs=""):
        """Simulate Alt VolumeUp X simultaneous press.

        This key combination is the kernel system request (sysrq) x.
        """
        self._press_and_release_keys(["<alt_l>", "<f10>", "x"], press_secs)

    def sysrq_r(self, press_secs=""):
        """Simulate Alt VolumeUp R simultaneous press.

        This key combination is the kernel system request (sysrq) r.
        """
        self._press_and_release_keys(["<alt_l>", "<f10>", "r"], press_secs)

    def arb_key(self, press_secs=""):
        """Simulate an arbitrary key press."""
        self._press_and_release_keys(self._arb_keys, press_secs)


class ChromeECMithraxHandler(ChromeECHandler):
    """Mithrax is a brya family device that is re-using its OEM's custom
    keyboard matrix, thus it requires a custom key matrix here.
    """

    KEY_MATRIX = {
        # key: (row, col)
        "`": (3, 1),
        "1": (7, 1),
        "2": (6, 4),
        "3": (6, 2),
        "4": (6, 3),
        "5": (3, 3),
        "6": (3, 6),
        "7": (6, 6),
        "8": (6, 5),
        "9": (6, 9),
        "0": (0, 9),
        "-": (3, 8),
        "=": (0, 8),
        "q": (6, 12),
        "w": (7, 4),
        "e": (5, 8),
        "r": (7, 3),
        "t": (2, 3),
        "y": (2, 6),
        "u": (7, 6),
        "i": (7, 5),
        "o": (6, 8),
        "p": (7, 8),
        "[": (2, 8),
        "]": (2, 5),
        "\\": (1, 11),
        "a": (4, 1),
        "s": (5, 6),
        "d": (0, 14),
        "f": (4, 3),
        "g": (1, 3),
        "h": (1, 6),
        "j": (4, 6),
        "k": (4, 5),
        "l": (4, 9),
        ";": (4, 8),
        "'": (1, 8),
        "z": (7, 9),
        "x": (5, 5),
        "c": (7, 13),
        "v": (7, 2),
        "b": (0, 3),
        "n": (0, 6),
        "m": (5, 1),
        ",": (5, 4),
        ".": (5, 9),
        "/": (6, 11),
        " ": (5, 3),
        "<right>": (1, 12),
        "<alt_r>": (0, 10),
        "<down>": (5, 11),
        "<tab>": (6, 1),
        "<f10>": (1, 4),
        "<shift_r>": (7, 7),
        "<ctrl_r>": (4, 0),
        "<esc>": (1, 1),
        "<backspace>": (7, 11),
        "<f2>": (3, 2),
        "<alt_l>": (6, 10),
        "<ctrl_l>": (2, 0),
        "<f1>": (4, 2),
        "<search>": (3, 0),
        "<f3>": (2, 2),
        "<f4>": (1, 2),
        "<f5>": (4, 4),
        "<f6>": (3, 4),
        "<f7>": (2, 4),
        "<f8>": (2, 9),
        "<f9>": (1, 9),
        "<up>": (2, 11),
        "<shift_l>": (1, 7),
        "<enter>": (4, 11),
        "<left>": (0, 12),
    }

    def __init__(self, grpc_core_addr):
        """Sets up the servo communication infrastructure."""
        super().__init__(grpc_core_addr)
        self.open()


class ChromeECFrostflowHandler(ChromeECHandler):
    """Frostflow is a skyrim family device that is re-using its OEM's custom
    keyboard matrix, thus it requires a custom key matrix here.
    """

    KEY_MATRIX = {
        # key: (row, col)
        "`": (3, 1),
        "1": (7, 1),
        "2": (6, 4),
        "3": (6, 2),
        "4": (6, 3),
        "5": (3, 3),
        "6": (3, 6),
        "7": (6, 6),
        "8": (6, 5),
        "9": (6, 9),
        "0": (0, 9),
        "-": (3, 8),
        "=": (0, 8),
        "q": (6, 12),
        "w": (7, 4),
        "e": (5, 8),
        "r": (7, 3),
        "t": (2, 3),
        "y": (2, 6),
        "u": (7, 6),
        "i": (7, 5),
        "o": (6, 8),
        "p": (7, 8),
        "[": (2, 8),
        "]": (2, 5),
        "\\": (1, 11),
        "a": (4, 1),
        "s": (5, 6),
        "d": (0, 14),
        "f": (4, 3),
        "g": (1, 3),
        "h": (1, 6),
        "j": (4, 6),
        "k": (4, 5),
        "l": (4, 9),
        ";": (4, 8),
        "'": (1, 8),
        "z": (7, 9),
        "x": (5, 5),
        "c": (7, 13),
        "v": (7, 2),
        "b": (0, 3),
        "n": (0, 6),
        "m": (5, 1),
        ",": (5, 4),
        ".": (5, 9),
        "/": (6, 11),
        " ": (5, 3),
        "<right>": (1, 12),
        "<alt_r>": (0, 10),
        "<down>": (5, 11),
        "<tab>": (6, 1),
        "<f10>": (1, 4),
        "<shift_r>": (7, 7),
        "<ctrl_r>": (4, 0),
        "<esc>": (1, 1),
        "<backspace>": (7, 11),
        "<f2>": (3, 2),
        "<alt_l>": (6, 10),
        "<ctrl_l>": (2, 0),
        "<f1>": (4, 2),
        "<search>": (3, 0),
        "<f3>": (2, 2),
        "<f4>": (1, 2),
        "<f5>": (4, 4),
        "<f6>": (3, 4),
        "<f7>": (2, 4),
        "<f8>": (2, 9),
        "<f9>": (1, 9),
        "<up>": (2, 11),
        "<shift_l>": (1, 7),
        "<enter>": (4, 11),
        "<left>": (0, 12),
    }

    def __init__(self, grpc_core_addr):
        """Sets up the servo communication infrastructure."""
        super().__init__(grpc_core_addr)
        self.open()


class ChromeECOsirisHandler(ChromeECHandler):
    """Osiris is a brya family device that is re-using its OEM's custom
    keyboard matrix, thus it requires a custom key matrix here.
    """

    KEY_MATRIX = {
        # key: (row, col)
        "`": (3, 1),
        "1": (7, 1),
        "2": (6, 4),
        "3": (6, 2),
        "4": (6, 3),
        "5": (3, 3),
        "6": (3, 6),
        "7": (6, 6),
        "8": (6, 5),
        "9": (6, 9),
        "0": (0, 9),
        "-": (3, 8),
        "=": (0, 8),
        "q": (6, 12),
        "w": (7, 4),
        "e": (5, 8),
        "r": (7, 3),
        "t": (2, 3),
        "y": (2, 6),
        "u": (7, 6),
        "i": (7, 5),
        "o": (6, 8),
        "p": (7, 8),
        "[": (2, 8),
        "]": (2, 5),
        "\\": (1, 11),
        "a": (4, 1),
        "s": (5, 6),
        "d": (0, 14),
        "f": (4, 3),
        "g": (1, 3),
        "h": (1, 6),
        "j": (4, 6),
        "k": (4, 5),
        "l": (4, 9),
        ";": (4, 8),
        "'": (1, 8),
        "z": (7, 9),
        "x": (5, 5),
        "c": (7, 13),
        "v": (7, 2),
        "b": (0, 3),
        "n": (0, 6),
        "m": (5, 1),
        ",": (5, 4),
        ".": (5, 9),
        "/": (6, 11),
        " ": (5, 3),
        "<right>": (1, 12),
        "<alt_r>": (0, 10),
        "<down>": (5, 11),
        "<tab>": (6, 1),
        "<f10>": (1, 4),
        "<shift_r>": (7, 7),
        "<ctrl_r>": (4, 0),
        "<esc>": (1, 1),
        "<backspace>": (7, 11),
        "<f2>": (3, 2),
        "<alt_l>": (6, 10),
        "<ctrl_l>": (2, 0),
        "<f1>": (4, 2),
        "<search>": (3, 0),
        "<f3>": (2, 2),
        "<f4>": (1, 2),
        "<f5>": (4, 4),
        "<f6>": (3, 4),
        "<f7>": (2, 4),
        "<f8>": (2, 9),
        "<f9>": (1, 9),
        "<up>": (2, 11),
        "<shift_l>": (1, 7),
        "<enter>": (4, 11),
        "<left>": (0, 12),
    }

    def __init__(self, grpc_core_addr):
        """Sets up the servo communication infrastructure."""
        super().__init__(grpc_core_addr)
        self.open()


class ChromeECBansheeHandler(ChromeECHandler):
    """Banshee is a brya family device that is re-using its OEM's custom
    keyboard matrix, thus it requires a custom key matrix here.
    """

    KEY_MATRIX = {
        "`": (4, 2),
        "1": (5, 2),
        "2": (5, 5),
        "3": (5, 4),
        "4": (5, 6),
        "5": (4, 6),
        "6": (4, 7),
        "7": (5, 7),
        "8": (5, 10),
        "9": (5, 8),
        "0": (4, 13),
        "-": (2, 13),
        "=": (4, 14),
        "q": (0, 2),
        "w": (6, 5),
        "e": (2, 4),
        "r": (6, 6),
        "t": (3, 6),
        "y": (3, 7),
        "u": (6, 7),
        "i": (6, 10),
        "o": (3, 8),
        "p": (5, 13),
        "[": (6, 13),
        "]": (6, 14),
        "\\": (2, 8),
        "a": (7, 2),
        "s": (4, 5),
        "d": (7, 14),
        "f": (7, 6),
        "g": (2, 6),
        "h": (2, 7),
        "j": (7, 7),
        "k": (7, 10),
        "l": (7, 8),
        ";": (7, 13),
        "'": (0, 14),
        "z": (1, 5),
        "x": (0, 5),
        "c": (0, 0),
        "v": (0, 6),
        "b": (1, 6),
        "n": (1, 7),
        "m": (0, 7),
        ",": (0, 10),
        ".": (0, 8),
        "/": (0, 13),
        " ": (1, 4),
        "<right>": (2, 15),
        "<alt_r>": (0, 3),
        "<down>": (1, 8),
        "<tab>": (3, 2),
        "<f10>": (4, 8),
        "<shift_r>": (0, 9),
        "<ctrl_r>": (0, 12),
        "<esc>": (7, 5),
        "<backspace>": (5, 14),
        "<f2>": (2, 5),
        "<alt_l>": (1, 3),
        "<ctrl_l>": (1, 12),
        "<f1>": (3, 5),
        "<search>": (4, 4),
        "<f3>": (6, 4),
        "<f4>": (3, 4),
        "<f5>": (4, 10),
        "<f6>": (3, 10),
        "<f7>": (2, 10),
        "<f8>": (1, 15),
        "<f9>": (3, 11),
        "<up>": (1, 13),
        "<shift_l>": (1, 9),
        "<enter>": (1, 14),
        "<left>": (6, 11),
    }

    def __init__(self, grpc_core_addr):
        """Sets up the servo communication infrastructure.

        @param servo: A Servo object representing
                           the host running servod.
        """
        super().__init__(grpc_core_addr)
        self.open()


class ChromeECPujjoloHandler(ChromeECHandler):
    """Pujjolo is a nissa family device that is re-using its OEM's custom
    keyboard matrix, thus it requires a custom key matrix here.
    """

    KEY_MATRIX = {
        "`": (3, 1),
        "1": (5, 1),
        "2": (6, 4),
        "3": (6, 2),
        "4": (6, 3),
        "5": (3, 3),
        "6": (3, 8),
        "7": (6, 8),
        "8": (6, 5),
        "9": (6, 9),
        "0": (6, 6),
        "-": (3, 6),
        "=": (0, 8),
        "q": (7, 5),
        "w": (7, 6),
        "e": (7, 8),
        "r": (7, 9),
        "t": (2, 3),
        "y": (2, 6),
        "u": (7, 1),
        "i": (7, 2),
        "o": (7, 3),
        "p": (7, 4),
        "[": (2, 8),
        "]": (2, 5),
        "\\": (3, 11),
        "a": (4, 1),
        "s": (3, 4),
        "d": (4, 2),
        "f": (4, 3),
        "g": (1, 3),
        "h": (1, 6),
        "j": (4, 6),
        "k": (4, 5),
        "l": (4, 9),
        ";": (4, 8),
        "'": (1, 8),
        "z": (6, 1),
        "x": (5, 8),
        "c": (5, 5),
        "v": (5, 9),
        "b": (0, 3),
        "n": (0, 5),
        "m": (5, 11),
        ",": (5, 2),
        ".": (5, 3),
        "/": (5, 4),
        " ": (5, 6),
        "<right>": (6, 12),
        "<alt_r>": (0, 10),
        "<down>": (6, 11),
        "<tab>": (2, 1),
        "<f10>": (0, 4),
        "<shift_r>": (7, 7),
        "<ctrl_r>": (3, 14),
        "<esc>": (1, 1),
        "<backspace>": (1, 11),
        "<f2>": (3, 2),
        "<alt_l>": (6, 13),
        "<ctrl_l>": (1, 14),
        "<f1>": (0, 2),
        "<search>": (3, 0),
        "<f3>": (2, 2),
        "<f4>": (1, 2),
        "<f5>": (4, 4),
        "<f6>": (2, 4),
        "<f7>": (1, 4),
        "<f8>": (2, 11),
        "<f9>": (1, 9),
        "<up>": (7, 11),
        "<shift_l>": (5, 7),
        "<enter>": (4, 11),
        "<left>": (7, 12),
    }

    def __init__(self, servo):
        """Sets up the servo communication infrastructure.

        @param servo: A Servo object representing
                           the host running servod.
        """
        super().__init__(servo)
        self.open()


class ChromeECDelbinHandler(ChromeECHandler):
    """Delbin is a volteer family device that is re-using its OEM's custom
    keyboard matrix, thus it requires a custom key matrix here.
    """

    KEY_MATRIX_DELBING = {
        # key: (row, col)
        "`": (3, 1),
        "1": (7, 1),
        "2": (6, 4),
        "3": (6, 2),
        "4": (6, 3),
        "5": (3, 3),
        "6": (3, 6),
        "7": (6, 6),
        "8": (6, 5),
        "9": (6, 9),
        "0": (0, 9),
        "-": (3, 8),
        "=": (0, 8),
        "q": (6, 12),
        "w": (7, 4),
        "e": (5, 8),
        "r": (7, 3),
        "t": (2, 3),
        "y": (2, 6),
        "u": (7, 6),
        "i": (7, 5),
        "o": (6, 8),
        "p": (7, 8),
        "[": (2, 8),
        "]": (2, 5),
        "\\": (1, 11),
        "a": (4, 1),
        "s": (5, 6),
        "d": (0, 14),
        "f": (4, 3),
        "g": (1, 3),
        "h": (1, 6),
        "j": (4, 6),
        "k": (4, 5),
        "l": (4, 9),
        ";": (4, 8),
        "'": (1, 8),
        "z": (7, 9),
        "x": (5, 5),
        "c": (7, 13),
        "v": (7, 2),
        "b": (0, 3),
        "n": (0, 6),
        "m": (5, 1),
        ",": (5, 4),
        ".": (5, 9),
        "/": (6, 11),
        " ": (5, 3),
        "<right>": (1, 12),
        "<alt_r>": (0, 10),
        "<down>": (5, 11),
        "<tab>": (6, 1),
        "<f10>": (1, 4),
        "<shift_r>": (7, 7),
        "<ctrl_r>": (4, 0),
        "<esc>": (1, 1),
        "<backspace>": (7, 11),
        "<f2>": (3, 2),
        "<alt_l>": (6, 10),
        "<ctrl_l>": (2, 0),
        "<f1>": (4, 2),
        "<search>": (3, 0),
        "<f3>": (2, 2),
        "<f4>": (1, 2),
        "<f5>": (4, 4),
        "<f6>": (3, 4),
        "<f7>": (2, 4),
        "<f8>": (2, 9),
        "<f9>": (1, 9),
        "<up>": (2, 11),
        "<shift_l>": (1, 7),
        "<enter>": (4, 11),
        "<left>": (0, 12),
    }

    def __init__(self, grpc_core_addr):
        """Sets up the servo communication infrastructure."""
        super().__init__(grpc_core_addr)

        # Try to query SKU_ID or FW_CONFIG from EC Uart
        self._servod_set("ec_uart_regexp", r'["SKU_ID:\\s+(\\d+)\\s+"]')
        # servo.set('ec_uart_regexp', 'r["FW_CONFIG:\\s+(\\d+)\\s+"]')
        self._servod_set("ec_uart_cmd", "cbi")

        sku_id = self._servod_get("ec_uart_cmd")

        if "65543" in sku_id or "65542" in sku_id:
            self.KEY_MATRIX = self.KEY_MATRIX_DELBING

        self._servod_set("ec_uart_regexp", "None")
        self.open()


class ChromeECChinchouHandler(ChromeECHandler):
    """Chinchou is a corsola family device that is re-using its OEM's custom
    keyboard matrix, thus it requires a custom key matrix here.
    """

    KEY_MATRIX = {
        # key: (row, col)
        "`": (3, 1),
        "1": (6, 1),
        "2": (6, 4),
        "3": (6, 2),
        "4": (6, 3),
        "5": (3, 3),
        "6": (3, 6),
        "7": (6, 6),
        "8": (6, 5),
        "9": (6, 9),
        "0": (6, 8),
        "-": (3, 8),
        "=": (0, 8),
        "q": (7, 1),
        "w": (7, 4),
        "e": (7, 2),
        "r": (7, 3),
        "t": (2, 3),
        "y": (2, 6),
        "u": (7, 6),
        "i": (7, 5),
        "o": (7, 9),
        "p": (7, 8),
        "[": (2, 8),
        "]": (2, 5),
        "\\": (3, 11),
        "a": (4, 1),
        "s": (4, 4),
        "d": (4, 2),
        "f": (4, 3),
        "g": (1, 3),
        "h": (1, 6),
        "j": (4, 6),
        "k": (4, 5),
        "l": (4, 9),
        ";": (4, 8),
        "'": (1, 8),
        "z": (5, 1),
        "x": (5, 4),
        "c": (5, 2),
        "v": (5, 3),
        "b": (0, 3),
        "n": (0, 6),
        "m": (5, 6),
        ",": (5, 5),
        ".": (5, 9),
        "/": (5, 8),
        " ": (5, 11),
        "<right>": (6, 12),
        "<alt_r>": (0, 10),
        "<down>": (6, 11),
        "<tab>": (2, 1),
        "<f10>": (0, 4),
        "<shift_r>": (7, 7),
        "<ctrl_r>": (3, 14),
        "<esc>": (1, 1),
        "<backspace>": (1, 11),
        "<f2>": (3, 2),
        "<alt_l>": (6, 13),
        "<ctrl_l>": (1, 14),
        "<f1>": (0, 2),
        "<search>": (3, 0),
        "<f3>": (2, 2),
        "<f4>": (1, 2),
        "<f5>": (3, 4),
        "<f6>": (2, 4),
        "<f7>": (1, 4),
        "<f8>": (2, 9),
        "<f9>": (1, 9),
        "<up>": (7, 11),
        "<shift_l>": (5, 7),
        "<enter>": (4, 11),
        "<left>": (7, 12),
    }


class ChromeECGreenbayupocHandler(ChromeECHandler):
    """Greenbayupoc is a brox family device that is re-using its OEM's custom
    keyboard matrix, thus it requires a custom key matrix here.
    """

    KEY_MATRIX = {
        "`": (3, 1),
        "1": (6, 1),
        "2": (6, 5),
        "3": (6, 2),
        "4": (6, 4),
        "5": (3, 4),
        "6": (3, 8),
        "7": (6, 8),
        "8": (6, 6),
        "9": (6, 11),
        "0": (6, 10),
        "-": (3, 10),
        "=": (0, 10),
        "q": (7, 1),
        "w": (7, 5),
        "e": (7, 2),
        "r": (7, 4),
        "t": (2, 4),
        "y": (2, 8),
        "u": (7, 8),
        "i": (7, 6),
        "o": (7, 11),
        "p": (7, 10),
        "[": (2, 10),
        "]": (2, 6),
        "\\": (3, 14),
        "a": (4, 1),
        "s": (4, 5),
        "d": (4, 2),
        "f": (4, 4),
        "g": (1, 4),
        "h": (1, 8),
        "j": (4, 8),
        "k": (4, 6),
        "l": (4, 11),
        ";": (4, 10),
        "'": (1, 10),
        "z": (5, 1),
        "x": (5, 5),
        "c": (5, 2),
        "v": (5, 4),
        "b": (0, 4),
        "n": (0, 8),
        "m": (5, 8),
        ",": (5, 6),
        ".": (5, 11),
        "/": (5, 10),
        " ": (5, 14),
        "<right>": (6, 15),
        "<alt_r>": (0, 13),
        "<down>": (6, 14),
        "<tab>": (2, 1),
        "<shift_r>": (7, 9),
        "<ctrl_r>": (4, 0),
        "<esc>": (1, 1),
        "<backspace>": (1, 14),
        "<f2>": (3, 2),
        "<alt_l>": (6, 13),
        "<ctrl_l>": (2, 0),
        "<f1>": (0, 2),
        "<search>": (1, 3),
        "<f3>": (2, 2),
        "<f4>": (1, 2),
        "<f5>": (3, 5),
        "<f6>": (2, 5),
        "<f7>": (1, 5),
        "<f8>": (0, 5),
        "<f9>": (3, 11),
        "<f10>": (2, 11),
        "<f11>": (1, 11),
        "<f12>": (0, 11),
        "<up>": (7, 14),
        "<shift_l>": (5, 9),
        "<enter>": (4, 14),
        "<left>": (7, 15),
    }

    def __init__(self, grpc_core_addr):
        """Sets up the servo communication infrastructure.

        @param servo: A Servo object representing
                           the host running servod.
        """
        super().__init__(grpc_core_addr)
        self.open()


class ChromeMatrix30Handler(ChromeECHandler):
    """To support scan matrix v30, add key matrix here."""

    KEY_MATRIX = {
        # key: (row, col)
        "`": (3, 1),
        "1": (5, 1),
        "2": (6, 4),
        "3": (6, 2),
        "4": (6, 3),
        "5": (3, 3),
        "6": (3, 8),
        "7": (6, 8),
        "8": (6, 5),
        "9": (6, 9),
        "0": (6, 6),
        "-": (3, 6),
        "=": (0, 8),
        "q": (7, 5),
        "w": (7, 6),
        "e": (7, 8),
        "r": (7, 9),
        "t": (2, 3),
        "y": (2, 6),
        "u": (7, 1),
        "i": (7, 2),
        "o": (7, 3),
        "p": (7, 4),
        "[": (2, 8),
        "]": (2, 5),
        # For UK: "\\": (6, 10),
        "\\": (3, 11),
        "a": (4, 1),
        "s": (3, 4),
        "d": (4, 2),
        "f": (4, 3),
        "g": (1, 3),
        "h": (1, 6),
        "j": (4, 6),
        "k": (4, 5),
        "l": (4, 9),
        ";": (4, 8),
        "'": (1, 8),
        "z": (6, 1),
        "x": (5, 8),
        "c": (5, 5),
        "v": (5, 9),
        "b": (0, 3),
        "n": (0, 5),
        "m": (5, 11),
        ",": (5, 2),
        ".": (5, 3),
        "/": (5, 4),
        " ": (5, 6),
        "<right>": (6, 12),
        "<left>": (7, 12),
        "<down>": (6, 11),
        "<up>": (7, 11),
        "<tab>": (2, 1),
        "<shift_r>": (7, 7),
        "<shift_l>": (5, 7),
        "<esc>": (1, 1),
        "<backspace>": (1, 11),
        "<alt_r>": (0, 10),
        "<alt_l>": (6, 13),
        "<ctrl_r>": (3, 14),
        "<ctrl_l>": (1, 14),
        "<f1>": (0, 2),
        "<f2>": (3, 2),
        "<f3>": (2, 2),
        "<f4>": (1, 2),
        "<f5>": (4, 4),
        "<f6>": (2, 4),
        "<f7>": (1, 4),
        "<f8>": (2, 11),
        "<f9>": (1, 9),
        "<f10>": (0, 4),
        "<f11>": (0, 1),
        "<f12>": (1, 5),
        "<f13>": (3, 5),
        "<f14>": (0, 11),
        "<f15>": (0, 12),
        "<enter>": (4, 11),
    }

    def __init__(self, grpc_core_addr):
        """Sets up the servo communication infrastructure.

        @param servo: A Servo object representing
                           the host running servod.
        """
        super().__init__(grpc_core_addr)
        self.open()


class USBkm232Handler(_BaseHandler):
    """Keyboard handler for devices without internal keyboard."""

    MAX_RSP_RETRIES = 10
    USB_QUEUE_DEPTH = 6
    CLEAR = b"\x38"
    KEYS = {
        # row 1
        "`": 1,
        "1": 2,
        "2": 3,
        "3": 4,
        "4": 5,
        "5": 6,
        "6": 7,
        "7": 8,
        "8": 9,
        "9": 10,
        "0": 11,
        "-": 12,
        "=": 13,
        "<undef1>": 14,
        "<backspace>": 15,
        "<tab>": 16,
        "q": 17,
        "w": 18,
        "e": 19,
        "r": 20,
        "t": 21,
        "y": 22,
        "u": 23,
        "i": 24,
        "o": 25,
        "p": 26,
        "[": 27,
        "]": 28,
        "\\": 29,
        # row 2
        "<capslock>": 30,
        "a": 31,
        "s": 32,
        "d": 33,
        "f": 34,
        "g": 35,
        "h": 36,
        "j": 37,
        "k": 38,
        "l": 39,
        ";": 40,
        "'": 41,
        "<undef2>": 42,
        "<enter>": 43,
        # row 3
        "<lshift>": 44,
        "<undef3>": 45,
        "z": 46,
        "x": 47,
        "c": 48,
        "v": 49,
        "b": 50,
        "n": 51,
        "m": 52,
        ",": 53,
        ".": 54,
        "/": 55,
        "[clear]": 56,
        "<rshift>": 57,
        # row 4
        "<lctrl>": 58,
        "<undef5>": 59,
        "<lalt>": 60,
        " ": 61,
        "<ralt>": 62,
        "<undef6>": 63,
        "<rctrl>": 64,
        "<undef7>": 65,
        "<mouse_left>": 66,
        "<mouse_right>": 67,
        "<mouse_up>": 68,
        "<mouse_down>": 69,
        "<lwin>": 70,
        "<rwin>": 71,
        "<win apl>": 72,
        "<mouse_lbtn_press>": 73,
        "<mouse_rbtn_press>": 74,
        "<insert>": 75,
        "<delete>": 76,
        "<mouse_mbtn_press>": 77,
        "<undef16>": 78,
        "<larrow>": 79,
        "<home>": 80,
        "<end>": 81,
        "<undef23>": 82,
        "<uparrow>": 83,
        "<downarrow>": 84,
        "<pgup>": 85,
        "<pgdown>": 86,
        "<mouse_scr_up>": 87,
        "<mouse_scr_down>": 88,
        "<rarrow>": 89,
        # numpad
        "<numlock>": 90,
        "<num7>": 91,
        "<num4>": 92,
        "<num1>": 93,
        "<undef27>": 94,
        "<num/>": 95,
        "<num8>": 96,
        "<num5>": 97,
        "<num2>": 98,
        "<num0>": 99,
        "<num*>": 100,
        "<num9>": 101,
        "<num6>": 102,
        "<num3>": 103,
        "<num.>": 104,
        "<num->": 105,
        "<num+>": 106,
        "<numenter>": 107,
        "<undef28>": 108,
        "<mouse_slow>": 109,
        # row 0
        "<esc>": 110,
        "<mouse_fast>": 111,
        "<f1>": 112,
        "<f2>": 113,
        "<f3>": 114,
        "<f4>": 115,
        "<f5>": 116,
        "<f6>": 117,
        "<f7>": 118,
        "<f8>": 119,
        "<f9>": 120,
        "<f10>": 121,
        "<f11>": 122,
        "<f12>": 123,
        "<prtscr>": 124,
        "<scrllk>": 125,
        "<pause/brk>": 126,
    }

    def __init__(self, grpc_core_addr, serial_device):
        """Constructor for usbkm232 class."""
        super().__init__(grpc_core_addr)
        if serial_device is None:
            raise Exception(
                "No device specified when initializing usbkm232 keyboard handler"
            )
        self.serial_device = serial_device
        self.serial = None
        self.open()
        self._logger.info("USBKM232: %s", self.serial_device)

    def open(self):
        """Open serial connection to serial_device."""
        if self.is_open():
            return
        self.serial = serial.Serial(self.serial_device, 9600, timeout=0.1)
        self.serial.interCharTimeout = 0.5
        self.serial.timeout = 0.5
        self.serial.writeTimeout = 0.5
        super().open()

    def close(self):
        """Close usbkm232 device, and assert rst on atmega if necessary."""
        if not self.is_open():
            return
        self.serial.close()
        super().close()

    def _test_atmega(self):
        """Send and receive a key from the atmega to verify it is present.

        Returns:
          Raises exception if no correct response is received.
        """
        self.serial.write(b"\0")
        rsp = self.serial.read(1)
        if not rsp or (ord(rsp) != 0xFF):
            self._logger.error(
                "Presence check response from atmega KB emu: rsp: %s", rsp
            )
            self._logger.error("Atmega KB offline: failed to communicate.")

    def _press(self, press_ch):
        """Encode and return character to press using usbkm232.

        Args:
          press_ch: character to press

        Returns:
          Proper encoding to send to the uart side of the usbkm232 to create the
          desired key press.
        """
        return b"%c" % self.KEYS[press_ch]

    def _release(self, release_ch):
        """Encode and return character to release using usbkm232.

        This value is simply the _press_ value + 128

        Args:
          release_ch: character to release

        Returns:
          Proper encoding to send to the uart side of the usbkm232 to create the
          desired key release.
        """
        return b"%c" % (self.KEYS[release_ch] | 0x80)

    def _rsp(self, orig_ch):
        """Check response after sending character to usbkm232.

        The response is the one's complement of the value sent.  This method
        blocks until proper response is received.

        Args:
          orig_ch: original character sent.

        Raises:
          Exception: if response was incorrect or timed out
        """
        count = 0
        rsp = self.serial.read(1)
        while (
            len(rsp) != 1 or ord(orig_ch) != (~ord(rsp) & 0xFF)
        ) and count < self.MAX_RSP_RETRIES:
            rsp = self.serial.read(1)
            print("re-read rsp")
            count += 1

        if count == self.MAX_RSP_RETRIES:
            raise Exception("Failed to get correct response from usbkm232")
        print("usbkm232: response [-] = \\0%03o 0x%02x" % (ord(rsp), ord(rsp)))

    def _write(self, mylist, check=False, clear=True):
        """Write list of commands to usbkm232.

        Args:
          mylist: list of encoded commands to send to the uart side of the
            usbkm232
          check: boolean determines whether response from usbkm232 should be
            checked.
          clear: boolean determines whether keystroke clear should be sent at end
            of the sequence.
        """
        # TODO(tbroch): USB queue depth is 6 might be more efficient to write
        #               more than just one make/break
        for i, write_ch in enumerate(mylist):
            print(
                "usbkm232: writing  [%d] = \\0%03o 0x%02x"
                % (i, ord(write_ch), ord(write_ch))
            )
            if hasattr(write_ch, "encode"):
                write_ch = write_ch.encode("utf-8")
            self.serial.write(write_ch)
            if check:
                self._rsp(write_ch)
            time.sleep(0.05)

        if clear:
            print("usbkm232: clearing keystrokes")
            self.serial.write(self.CLEAR)
            if check:
                self._rsp(self.CLEAR)

    def writestr(self, mystr):
        """Write string to usbkm232.

        Args:
          mystr: string to send across the usbkm232
        """
        rlist = []
        for write_ch in mystr:
            rlist.append(self._press(write_ch))
            rlist.append(self._release(write_ch))
        self._write(rlist)

    def ctrl_d(self, press_secs=""):
        """Press and release ctrl-d sequence."""
        self._write([self._press("<lctrl>"), self._press("d")])

    def ctrl_f(self, press_secs=""):
        """Press and release ctrl-f sequence."""
        self._write([self._press("<lctrl>"), self._press("f")])

    def ctrl_r(self, press_secs=""):
        """Press and release ctrl-r sequence."""
        self._write([self._press("<lctrl>"), self._press("r")])

    def ctrl_u(self, press_secs=""):
        """Press and release ctrl-u sequence."""
        self._write([self._press("<lctrl>"), self._press("u")])

    def ctrl_s(self, press_secs=""):
        """Press and release ctrl-s sequence."""
        self._write([self._press("<lctrl>"), self._press("s")])

    def alt_f5(self, press_secs=""):
        """Press and release alt-f5 sequence."""
        self._write([self._press("<lalt>"), self._press("<f5>")])

    def alt_f6(self, press_secs=""):
        """Press and release alt-f6 sequence."""
        self._write([self._press("<lalt>"), self._press("<f6>")])

    def arrow_up(self, press_secs=""):
        """Press and release ArrowUp key."""
        self._write([self._press("<uparrow>")])

    def arrow_down(self, press_secs=""):
        """Press and release ArrowDown key."""
        self._write([self._press("<downarrow>")])

    def enter_key(self, press_secs=""):
        """Press and release enter"""
        self._write([self._press("<enter>")])

    def ctrl_key(self, press_secs=""):
        """Simulate Enter key button press."""
        self._write([self._press("<lctrl>")])

    def crtl_enter(self):
        """Press and release ctrl+enter"""
        self._write([self._press("<lctrl>"), self._press("<enter>")])

    def space_key(self):
        """Press and release space key."""
        self._write([self._press(" ")])

    def refresh_key(self, press_secs=""):
        """Simulate Refresh key (F3) button press."""
        self._write([self._press("<f3>")])

    def ctrl_refresh_key(self, press_secs=""):
        """Simulate Ctrl and Refresh (F3) simultaneous press.
        This key combination is an alternative of Space key.
        """
        self._write([self._press("<lctrl>"), self._press("<f3>")])

    def sysrq_x(self, press_secs=""):
        """Simulate Alt VolumeUp X simultaneous press.

        This key combination is the kernel system request (sysrq) x.
        """
        self._write([self._press("<lalt>"), self._press("<f10>"), self._press("x")])

    def sysrq_r(self, press_secs=""):
        """Simulate Alt VolumeUp R simultaneous press.

        This key combination is the kernel system request (sysrq) r.
        """
        self._write([self._press("<lalt>"), self._press("<f10>"), self._press("r")])

    def arb_key(self, press_secs=""):
        """Simulate an arbitrary key press."""
        self._write([self._press(key) for key in self._arb_keys])

    def tab(self):
        """Press and release tab"""
        self._write([self._press("<tab>")])


class ServoUSBkm232Handler(USBkm232Handler):
    """Keyboard handler for devices without internal keyboard."""

    def __init__(self, grpc_core_addr, legacy):
        """
        Args:
          legacy: bool, true for servo v2 as they require more setup.
        """
        # Create a gRPC channel to the specified host and port
        grpc_core_host, grpc_core_port = grpc_core_addr
        channel = GrpcClient.create_grpc_channel(grpc_core_host, grpc_core_port)
        self._driver_client = servo_dev_grpc.ServoService(channel)
        time.sleep(0.5)
        self._servod_set("atmega_rst", "on")
        self._servod_set("at_hwb", "off")
        self._servod_set("atmega_rst", "off")
        serial = self._servod_get("atmega_pty")
        self.legacy = legacy
        # None as grpc address because driver client is already initialized up here
        super().__init__(None, serial)

    def _servod_get(self, control):
        """Get the value of the given control with proper prefix."""
        service = self._driver_client.GetServo(control_name=control)
        return service.response

    def _servod_set(self, control, value):
        """Set the value of the given control with proper prefix."""
        val_pb = json_utils.wrap_value(value)
        self._driver_client.SetServo(control_name=control, value=val_pb)

    def open(self):
        """Take atmega out of reset, and potentially do legacy setup."""
        if self.is_open():
            return
        # Ensure that the atmega is not in reset
        self._servod_set("atmega_rst", "off")
        # Do proper setup for legacy devices
        if self.legacy:
            self._servod_set("atmega_baudrate", "9600")
            self._servod_set("atmega_bits", "eight")
            self._servod_set("atmega_parity", "none")
            self._servod_set("atmega_sbits", "one")
            self._servod_set("usb_mux_sel4", "on")
            self._servod_set("usb_mux_oe4", "on")
        # Give the board enough time to boot up.
        time.sleep(1)
        super().open()
        self._test_atmega()

    def close(self):
        """Set the atmega to reset before closing the serial port."""
        if not self.is_open():
            return
        # If using the atmega, ensure that the atmega is in reset.
        self._servod_set("atmega_rst", "on")
        super().close()
