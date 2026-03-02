# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from unittest.mock import MagicMock
from unittest.mock import mock_open
from unittest.mock import patch

import pytest

from servo_updater import servo_updater


@patch("servo_updater.servo_updater.os.path.isfile")
@patch("servo_updater.servo_updater.get_updater_path")
def test_get_files_and_version_missing_config(mock_get_path, mock_isfile):
    mock_get_path.return_value = ("/test/updater", "/test/firmware", "/test/configs")
    mock_isfile.return_value = False

    with pytest.raises(servo_updater.ServoUpdaterException) as exc:
        servo_updater.get_files_and_version("missing_board")
    assert "Can't find config file" in str(exc.value)


@patch("servo_updater.servo_updater.os.path.isfile")
@patch("servo_updater.servo_updater.get_updater_path")
@patch("builtins.open", new_callable=mock_open, read_data='{"board": "testboard"}')
@patch("servo_updater.servo_updater._extract_version")
def test_get_files_and_version_missing_firmware(
    unused_mock_extract, unused_mock_open_file, mock_get_path, mock_isfile
):
    mock_get_path.return_value = ("/test/updater", "/test/firmware", "/test/configs")
    mock_isfile.side_effect = (
        lambda path: path.endswith(".json") or path == "testboard.json"
    )

    with pytest.raises(servo_updater.ServoUpdaterException) as exc:
        servo_updater.get_files_and_version("testboard.json")
    assert "Can't find firmware binary" in str(exc.value)


@patch("servo_updater.servo_updater.subprocess.check_output")
def test_do_with_retries(mock_output):
    mock_output.__name__ = "mock_func"
    mock_output.side_effect = [Exception("fail 1"), Exception("fail 2"), b"success"]
    result = servo_updater.do_with_retries(mock_output, "test")
    assert result == b"success"
    assert mock_output.call_count == 3


@patch("servo_updater.servo_updater.subprocess.check_output")
@patch("servo_updater.servo_updater.time.sleep")
def test_do_with_retries_fail(unused_mock_sleep, mock_output):
    mock_output.__name__ = "mock_func"
    mock_output.side_effect = Exception("fail")
    with pytest.raises(Exception, match="fail"):
        servo_updater.do_with_retries(mock_output)
    assert mock_output.call_count > 1


@patch("servo_updater.servo_updater.fw_update.Supdate.stop")
@patch("servo_updater.servo_updater.fw_update.Supdate.start")
@patch("servo_updater.servo_updater.fw_update.Supdate.load_file")
@patch("builtins.open", new_callable=mock_open)
@patch("servo_updater.servo_updater.os.path.getsize", return_value=1024)
@patch("servo_updater.servo_updater.fw_update.Supdate.write_file")
@patch("servo_updater.servo_updater.fw_update.Supdate.connect_usb")
@patch("servo_updater.servo_updater.print_servod_warning")
@patch("servo_updater.servo_updater.subprocess.call", return_value=0)
@patch("servo_updater.servo_updater.subprocess.check_output")
@patch("servo_updater.servo_updater.fw_update.Supdate.load_board")
def test_flash(
    unused_mock_load,
    unused_mock_output,
    unused_mock_call,
    unused_mock_warn,
    unused_mock_connect,
    unused_mock_write,
    unused_mock_getsize,
    unused_mock_open_file,
    unused_mock_load_file,
    unused_mock_start,
    unused_mock_stop,
):
    servo_updater.flash("board.json", "1234", "fw.bin")


@patch("servo_updater.servo_updater.subprocess.check_output")
@patch("servo_updater.servo_updater.subprocess.call", return_value=0)
def test_flash2(mock_call, unused_mock_output):
    mock_call.return_value = 0
    servo_updater.flash2("0483:df11", "1234", "fw.bin")
    mock_call.assert_called()


def test_select():
    mock_tiny = MagicMock()
    mock_tiny.pty = MagicMock()
    mock_tiny.pty._issue_cmd_get_results.return_value = [("match", "rw")]
    servo_updater.select(mock_tiny, "rw")
    mock_tiny.pty._issue_cmd.assert_called_with("sysjump rw")


def test_do_version():
    mock_tiny = MagicMock()
    mock_tiny.pty = MagicMock()
    mock_tiny.pty._issue_cmd_get_results.return_value = [("match", "v1.0")]
    mock_tiny.bootloader_version.return_value = "bl1.0"
    servo_updater.do_version(mock_tiny)
    mock_tiny.pty._issue_cmd_get_results.assert_called()


def test_do_updater_version():
    mock_tiny = MagicMock()
    mock_tiny.pty = MagicMock()
    mock_tiny.pty._issue_cmd_get_results.return_value = [("match", "_v1.1.5800")]
    servo_updater.do_updater_version(mock_tiny)
    mock_tiny.pty._issue_cmd_get_results.assert_called()


@patch("servo_updater.servo_updater.get_firmware_channel", return_value="dev")
@patch(
    "servo_updater.servo_updater.get_files_and_version",
    return_value=("board.json", "fw.bin", "v2.0"),
)
@patch("servo_updater.servo_updater.subprocess.call", return_value=0)
@patch("servo_updater.servo_updater.print_servod_warning")
@patch("servo_updater.servo_updater.c.wait_for_usb")
@patch("servo_updater.servo_updater.tiny_servod.TinyServod")
def test_update_no_reboot(
    mock_tinys,
    unused_mock_wait,
    unused_mock_warn,
    unused_mock_call,
    unused_mock_get_files,
    unused_mock_get_chan,
):
    mock_dev = MagicMock()
    mock_dev.serialno = "1234"
    mock_dev.idVendor = 0x18D1
    mock_dev.idProduct = 0x501A  # SERVO_V4

    class MockArgs:
        board = "servo_v4"
        file = None
        channel = "dev"
        force = True
        reboot = False
        allow_rollback = True
        verbose = False

    devmap = {
        "18d1:501a": ("board_obj", "servo_v4", "iface", "board.json", "fw.bin", "v2.0")
    }

    # State keeping for the mock
    class State:
        region = "ro"

    def mock_issue_cmd(cmd, unused_regex=None):
        if "sysinfo" in cmd:
            return [("match", State.region)]
        if "sysjump" in cmd:
            State.region = cmd.split()[1]
            return [("match", "")]
        if "reboot" in cmd:
            State.region = "ro"
            return [("match", "")]
        if "version" in cmd:
            return [("match", "_v1.1.5800")]
        return [("match", "ro")]

    mock_tinys.return_value.pty._issue_cmd_get_results.side_effect = mock_issue_cmd
    mock_tinys.return_value.pty._issue_cmd.side_effect = mock_issue_cmd

    with patch("servo_updater.servo_updater.flash2") as mock_flash2:
        servo_updater.update(mock_dev, "1234", MockArgs(), devmap)
        mock_flash2.assert_called()


@patch("servo_updater.servo_updater.argparse.ArgumentParser.parse_args")
@patch("servo_updater.servo_updater.sys.exit")
def test_main_board_print(unused_mock_exit, mock_args):
    args = MagicMock()
    args.print_only = True
    args.json_only = False
    args.board = "servo_v4"
    args.all = False
    args.channel = "dev"
    mock_args.return_value = args

    with patch("servo_updater.servo_updater.print_versions") as mock_print:
        servo_updater.main(["--print"])
        mock_print.assert_called()
