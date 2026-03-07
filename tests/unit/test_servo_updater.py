# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for servo_updater."""

from unittest import mock

import pytest

from servo_updater import servo_updater


def test_do_with_retries():
    def mock_func(*_args):
        mock_func.call_count += 1
        if mock_func.call_count == 1:
            raise ValueError("fail")
        return "success"

    mock_func.call_count = 0
    mock_func.__name__ = "mock_func"

    res = servo_updater.do_with_retries(mock_func)
    assert res == "success"
    assert mock_func.call_count == 2

    def mock_func2(*args):
        raise ValueError("fail")

    mock_func2.__name__ = "mock_func2"
    with pytest.raises(servo_updater.ServoUpdaterException):
        servo_updater.do_with_retries(mock_func2)


@mock.patch("servo_updater.servo_updater.fw_update.Supdate")
def test_flash(mock_supdate):
    mock_instance = mock.Mock()
    mock_supdate.return_value = mock_instance
    mock_instance.connect_usb.return_value = True

    res = servo_updater.flash("board.json", "12345", "fw.bin")
    assert res is None
    mock_instance.connect_usb.assert_called_once()
    mock_instance.start.assert_called_once()


@mock.patch("subprocess.call")
def test_flash2(mock_call):
    mock_call.return_value = 0
    res = servo_updater.flash2("18d1:501a", "12345", "fw.bin")
    assert res == 0
    assert mock_call.call_count >= 1


@mock.patch("subprocess.check_output")
def test_extract_version(mock_check_output, tmp_path):
    bin_file = tmp_path / "test.bin"
    bin_file.write_text("mock")

    mock_check_output.return_value = "servo_v4_v1.2.3\n"
    res = servo_updater._extract_version("servo_v4", str(bin_file))
    assert (
        res == "servo_v4_v1.2.3"
    )  # The code actually returns m.group(0), so the full match

    mock_check_output.return_value = "something_else\n"
    with pytest.raises(servo_updater.ServoUpdaterException):
        servo_updater._extract_version("servo_v4", str(bin_file))


@mock.patch("servo_updater.servo_updater.get_updater_path")
@mock.patch("servo_updater.servo_updater._extract_version")
@mock.patch("os.path.exists")
def test_get_files_and_version(mock_exists, mock_extract, mock_get_path):
    mock_get_path.return_value = ("/boards", "/fw", "/fwp")
    mock_exists.return_value = True
    mock_extract.return_value = "v1.2.3"

    with mock.patch("os.path.isfile", return_value=True), mock.patch(
        "builtins.open", mock.mock_open(read_data='{"board": "servo_v4"}')
    ):
        paths = servo_updater.get_files_and_version("servo_v4")

    assert len(paths) == 3
    assert paths[2] == "v1.2.3"


@mock.patch("servo_updater.servo_updater.sys.exit")
@mock.patch("servo_updater.servo_updater.flash2")
@mock.patch("servo_updater.servo_updater.get_files_and_version")
def test_update(mock_get_files, mock_flash2, _mock_exit):
    dev = mock.Mock()
    dev.idVendor = 0x18D1
    dev.idProduct = 0x501A

    args = mock.Mock()
    args.file = None
    args.channel = "stable"
    args.reboot = False
    args.force = False
    args.yes = True

    devmap = {
        "18d1:501a": [
            "servo_v4",
            "servo_v4",
            1,
            "board.json",
            "fw.bin",
            "v1.0.0",  # newvers from devmap
        ]
    }

    mock_get_files.return_value = ("board.bin", "fw.bin", "v1.0.0")

    with mock.patch(
        "servo_updater.servo_updater.do_version", return_value="servo_v4_v0.0.0"
    ), mock.patch(
        "servo_updater.servo_updater.tiny_servod.TinyServod", return_value=mock.Mock()
    ), mock.patch(
        "servo_updater.servo_updater.select", return_value=None
    ), mock.patch(
        "servo_updater.servo_updater.do_updater_version", return_value=6
    ), mock.patch(
        "servo_updater.ecusb.tiny_servo_common.wait_for_usb", return_value={"dev"}
    ):
        servo_updater.update(dev, "12345", args, devmap)

    assert mock_flash2.call_count == 2


@mock.patch("time.sleep", return_value=None)
def test_select_ro(_mock_sleep):
    """Test select 'ro' region."""
    mock_tinys = mock.Mock()
    mock_tinys.pty._issue_cmd_get_results.return_value = [[None, "RO"]]
    servo_updater.select(mock_tinys, "ro")
    mock_tinys.pty._issue_cmd.assert_called_with("reboot")
    mock_tinys.close.assert_called_once()
    mock_tinys.reinitialize.assert_called_once()


@mock.patch("time.sleep", return_value=None)
def test_select_rw(_mock_sleep):
    """Test select 'rw' region."""
    mock_tinys = mock.Mock()
    mock_tinys.pty._issue_cmd_get_results.return_value = [[None, "RW"]]
    servo_updater.select(mock_tinys, "rw")
    mock_tinys.pty._issue_cmd.assert_called_with("sysjump rw")


def test_select_invalid_region():
    """Test select invalid region."""
    mock_tinys = mock.Mock()
    with pytest.raises(
        servo_updater.ServoUpdaterException, match="Region must be ro or rw"
    ):
        servo_updater.select(mock_tinys, "invalid")


@mock.patch("time.sleep", return_value=None)
def test_select_fail_verify(_mock_sleep):
    """Test select region verification failure."""
    mock_tinys = mock.Mock()
    mock_tinys.pty._issue_cmd_get_results.return_value = [[None, "RW"]]
    with pytest.raises(
        servo_updater.ServoUpdaterException, match="Invalid region: rw/ro"
    ):
        servo_updater.select(mock_tinys, "ro")


def test_main_no_board():
    """Test main requires board if not all."""
    with pytest.raises(
        servo_updater.ServoUpdaterException, match="Use --board parameter"
    ):
        servo_updater.main([])


@mock.patch("sys.stdout", new_callable=mock.Mock)
@mock.patch("servo_updater.servo_updater.print_versions")
@mock.patch("servo_updater.servo_updater.print_json")
def test_main_print_only(mock_print_json, mock_print_versions, _mock_stdout):
    """Test main with --print."""
    servo_updater.main(["--board", "servo_micro", "--print"])
    mock_print_versions.assert_called_once()
    mock_print_json.assert_not_called()


@mock.patch("sys.stdout", new_callable=mock.Mock)
@mock.patch("servo_updater.servo_updater.print_versions")
@mock.patch("servo_updater.servo_updater.print_json")
def test_main_json_only(mock_print_json, mock_print_versions, _mock_stdout):
    """Test main with --json."""
    servo_updater.main(["--board", "servo_micro", "--json"])
    mock_print_json.assert_called_once()
    mock_print_versions.assert_not_called()


def test_main_print_and_json():
    """Test main with both print and json."""
    with pytest.raises(
        servo_updater.ServoUpdaterException, match="Can't use both --print and --json"
    ):
        servo_updater.main(["--board", "servo_micro", "--print", "--json"])


def test_print_servod_warning(capsys):
    """Test print_servod_warning."""
    servo_updater.print_servod_warning()
    captured = capsys.readouterr()
    assert "Couldn't connect to servo" in captured.out
    assert "stop-servod" in captured.out


@mock.patch("sys.exit")
@mock.patch("servo_updater.servo_updater.print_servod_warning")
def test_do_version_ptyerror(mock_warning, _mock_exit):
    """Test do_version handles PtyError."""
    mock_tinys = mock.Mock()
    mock_tinys.pty._issue_cmd_get_results.side_effect = servo_updater.PtyError("error")
    _mock_exit.side_effect = SystemExit(1)
    with pytest.raises(SystemExit):
        servo_updater.do_version(mock_tinys)
    mock_warning.assert_called_once()
    _mock_exit.assert_called_once_with(1)


def test_main_print_no_board():
    """Test main with print but no board."""
    with pytest.raises(
        servo_updater.ServoUpdaterException, match="Use --board parameter"
    ):
        servo_updater.main(["--print"])


@mock.patch("servo_updater.servo_updater.update")
@mock.patch("servo_updater.ecusb.tiny_servo_common.wait_for_usb")
@mock.patch("servo_updater.servo_updater.get_files_and_version")
def test_main_full_update(mock_get_files, mock_wait, _mock_update, tmp_path):
    """Test main full run."""
    brdfile = tmp_path / "board.json"
    brdfile.write_text(
        '{"vid": "0x18d1", "pid": "0x501a", "console": "0", "board": "servo_micro"}'
    )
    mock_get_files.return_value = (str(brdfile), "binfile", "1.0")

    mock_dev = mock.Mock()
    mock_wait.return_value = [mock_dev]

    servo_updater.main(["--board", "servo_micro"])

    mock_wait.assert_called_once()
    _mock_update.assert_called_once_with(mock_dev, None, mock.ANY, mock.ANY)


@mock.patch("servo_updater.servo_updater.update")
@mock.patch("servo_updater.ecusb.tiny_servo_common.wait_for_usb")
@mock.patch("servo_updater.servo_updater.get_files_and_version")
def test_main_multiple_devices_error(mock_get_files, mock_wait, _mock_update, tmp_path):
    """Test main with multiple devices found and not --all."""
    brdfile = tmp_path / "board.json"
    brdfile.write_text(
        '{"vid": "0x18d1", "pid": "0x501a", "console": "0", "board": "servo_micro"}'
    )
    mock_get_files.return_value = (str(brdfile), "binfile", "1.0")

    mock_wait.return_value = [mock.Mock(), mock.Mock()]

    with pytest.raises(
        servo_updater.ServoUpdaterException, match="Found 2 matching devices"
    ):
        servo_updater.main(["--board", "servo_micro"])
