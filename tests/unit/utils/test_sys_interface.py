# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


from unittest.mock import patch

from servo.utils import sys_interface


class TestSysInterface:
    def test_openpty(self):
        sys = sys_interface.SysInterface()
        with patch("servo.utils.sys_interface.pty.openpty", return_value=(1, 2)):
            assert sys.openpty() == (1, 2)

    def test_system(self):
        sys = sys_interface.SysInterface()
        with patch("servo.utils.sys_interface.os.system", return_value=0):
            assert sys.system("echo") == 0

    def test_managed_pty(self):
        sys = sys_interface.SysInterface()
        with patch("servo.utils.sys_interface.pty.openpty", return_value=(1, 2)):
            with patch("servo.utils.sys_interface.os.close") as mock_close:
                with sys.managed_pty() as (m, s):
                    assert m == 1
                    assert s == 2
                mock_close.assert_any_call(1)
                mock_close.assert_any_call(2)

    def test_managed_pipe_oserror(self):
        sys = sys_interface.SysInterface()
        with patch("servo.utils.sys_interface.os.pipe", return_value=(1, 2)):
            with patch(
                "servo.utils.sys_interface.os.close", side_effect=OSError("error")
            ) as mock_close:
                with sys.managed_pipe() as (unused_r, unused_w):
                    pass
                mock_close.assert_any_call(2)

    def test_managed_open(self):
        sys = sys_interface.SysInterface()
        with patch("servo.utils.sys_interface.os.open", return_value=1):
            with patch("servo.utils.sys_interface.os.close") as mock_close:
                with sys.managed_open("test", 0) as fd:
                    assert fd == 1
                mock_close.assert_called_with(1)

    def test_methods(self):
        sys = sys_interface.SysInterface()
        with patch("servo.utils.sys_interface.os.close") as mock_close:
            sys.close(1)
            mock_close.assert_called_with(1)

        with patch("servo.utils.sys_interface.os.pipe", return_value=(1, 2)):
            assert sys.pipe() == (1, 2)

        with patch("servo.utils.sys_interface.os.fdopen", return_value="f"):
            assert sys.fdopen(1) == "f"

        with patch("servo.utils.sys_interface.os.write", return_value=5):
            assert sys.write(1, b"data") == 5

        with patch("servo.utils.sys_interface.os.read", return_value=b"data"):
            assert sys.read(1, 5) == b"data"

        with patch("servo.utils.sys_interface.os.chmod"):
            sys.chmod("path", 0)

        with patch("servo.utils.sys_interface.os.fchmod"):
            sys.fchmod(1, 0)

        with patch("servo.utils.sys_interface.os.fchown"):
            sys.fchown(1, 0, 0)

        with patch("servo.utils.sys_interface.os.ttyname", return_value="tty"):
            assert sys.ttyname(1) == "tty"

        with patch("servo.utils.sys_interface.os.statvfs", return_value="stat"):
            assert sys.statvfs("path") == "stat"

        with patch("servo.utils.sys_interface.os.kill"):
            sys.kill(1, 9)

        with patch("servo.utils.sys_interface.os.rmdir"):
            sys.rmdir("path")

        with patch("servo.utils.sys_interface.os.remove"):
            sys.remove("path")

        with patch("servo.utils.sys_interface.subprocess.call", return_value=0):
            assert sys.call(["ls"]) == 0

        with patch("servo.utils.sys_interface.subprocess.check_call", return_value=0):
            assert sys.check_call(["ls"]) == 0

        with patch(
            "servo.utils.sys_interface.subprocess.check_output", return_value=b"out"
        ):
            assert sys.check_output(["ls"]) == b"out"

        with patch("servo.utils.sys_interface.subprocess.run", return_value="run"):
            assert sys.run(["ls"]) == "run"

        with patch("servo.utils.sys_interface.subprocess.Popen", return_value="popen"):
            assert sys.popen(["ls"]) == "popen"

    def test_managed_pty_oserror(self):
        sys = sys_interface.SysInterface()
        with patch("servo.utils.sys_interface.pty.openpty", return_value=(1, 2)):
            with patch(
                "servo.utils.sys_interface.os.close", side_effect=OSError("error")
            ) as mock_close:
                with sys.managed_pty() as (unused_m, unused_s):
                    pass
                mock_close.assert_any_call(2)

    def test_managed_pipe(self):
        sys = sys_interface.SysInterface()
        with patch("servo.utils.sys_interface.os.pipe", return_value=(1, 2)):
            with patch("servo.utils.sys_interface.os.close") as mock_close:
                with sys.managed_pipe() as (r, w):
                    assert r == 1
                    assert w == 2
                mock_close.assert_any_call(1)
                mock_close.assert_any_call(2)

    def test_managed_open_oserror(self):
        sys = sys_interface.SysInterface()
        with patch("servo.utils.sys_interface.os.open", return_value=1):
            with patch(
                "servo.utils.sys_interface.os.close", side_effect=OSError("error")
            ) as mock_close:
                with sys.managed_open("test", 0) as unused_fd:
                    pass
                mock_close.assert_called_with(1)
