# Copyright 2019 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for the logic inside servo_parsing."""

import copy
import os
import shutil
import socket
import tempfile
import unittest

from servo.common import servo_parsing
from servo.core import client
from servo.utils import scratch


# Throughout all the tests in this file, parse_known_args is used instead of
# parse args. This is to avoid having to clutter the tests with unrelated
# cmdline options.


class TestRCFile(unittest.TestCase):
    """Test RC file parsing logic, with emphasis on error handling."""

    @staticmethod
    def create_fake_rc_file(name, serial, board=None, model=None, tempdir=None):
        """Helper to create a fake RC file with one entry based on args."""
        if not tempdir:
            tempdir = tempfile.mkdtemp()
        rc_file = os.path.join(tempdir, "rc")
        with open(rc_file, "w", encoding="utf-8") as f:
            # 0 as PORT is no longer supported, but the slot is still there for
            # legacy reasons.
            entry_pieces = [name, serial, "0"]
            if board:
                entry_pieces.append(board)
                if model:
                    # Only add model if board is also given.
                    entry_pieces.append(model)
            entry = "%s\n" % ", ".join(entry_pieces)
            f.write(entry)
        return rc_file

    def setUp(self):
        """Prepare cmdline, and a fake RC file to test RC file parsing."""
        # create a fake RC file
        unittest.TestCase.setUp(self)
        self._name = "Alfred"
        self._serialname = "this-is-a-fake-serial"
        self._board = "fake-board"
        self._rc_file = TestRCFile.create_fake_rc_file(
            name=self._name, serial=self._serialname, board=self._board
        )
        self._cmdline = ["--name", self._name]

    def tearDown(self):
        """Delete the temporary directory and its content."""
        shutil.rmtree(os.path.dirname(self._rc_file))
        unittest.TestCase.tearDown(self)

    def test_normal_rc_file(self):
        """A well configured RC file generates the expected rc dictionary."""
        rcd = servo_parsing.ServodRCParser.parse_rc(self._rc_file)
        assert self._name in rcd
        rcd_entry = rcd[self._name]
        assert self._serialname == rcd_entry["sn"]
        assert self._board == rcd_entry["board"]

    def test_no_rc_file(self):
        """Passed in RC file does not exist: return empty runtime config dict."""
        rcd = servo_parsing.ServodRCParser.parse_rc("/tmp/this-is-a-fake-file")
        # Expected return value is {} so this seems appropriate regardless of python
        # internals
        assert not rcd

    def test_rc_file_misconfigured(self):
        """RC file is misconfigured (no commas): return empty runtime config dict."""
        with open(self._rc_file, "w", encoding="utf-8") as f:
            # Extra space is just for padding
            f.write(
                "%s %s %s %s      \n" % (self._name, self._serialname, "0", self._board)
            )
        rcd = servo_parsing.ServodRCParser.parse_rc(self._rc_file)
        # Expected return value is {} so this seems appropriate regardless of python
        # internals
        assert not rcd


class TestServodRCParser(unittest.TestCase):
    """Test ServodRCParser substitution and overwrite logic."""

    def setUp(self):
        """Setup cmdline args, create fake RC file, and setup parser for tests."""
        unittest.TestCase.setUp(self)
        self._invalid_name = "NotAlfred"
        self._valid_name = "Alfred"
        self._serialname = "this-is-a-fake-serial"
        self._board = "fake-board"
        self._rc_file = TestRCFile.create_fake_rc_file(
            name=self._valid_name, serial=self._serialname, board=self._board
        )
        self._original_env = copy.deepcopy(os.environ)
        # Overwrite default file to use the test's rc file
        self._original_rc = servo_parsing.DEFAULT_RC_FILE
        servo_parsing.DEFAULT_RC_FILE = self._rc_file
        self.setup_parser()

    def setup_parser(self):
        """Helper to add parser."""
        self._parser = servo_parsing.ServodRCParser()
        # The default ServodRC parser does not have --board argument as this is
        # not relevant for servod clients. Add it here to test some board logic.
        self._parser.add_argument("-b", "--board", type=str)

    def tearDown(self):
        """Remove fake RC file and restore the os environment variables."""
        shutil.rmtree(os.path.dirname(self._rc_file))
        os.environ = self._original_env
        servo_parsing.DEFAULT_RC_FILE = self._original_rc
        unittest.TestCase.tearDown(self)

    def test_env_name_no_serial_no_name(self):
        """Name defined in environment, no serial, no name: take name from env."""
        os.environ[servo_parsing.NAME_ENV_VAR] = self._valid_name
        # Regenerate the parser as this test modifies the os.environ map.
        self.setup_parser()
        cmdline = []
        opts, _unused = self._parser.parse_known_args(cmdline)
        assert self._serialname == opts.serialname

    def test_env_name_serial_no_name(self):
        """Name defined in environment, serial, no name: honor serial."""
        os.environ[servo_parsing.NAME_ENV_VAR] = self._valid_name
        # Regenerate the parser as this test modifies the os.environ map.
        self.setup_parser()
        cmdline = ["--serialname", self._serialname]
        opts, _unused = self._parser.parse_known_args(cmdline)
        assert self._serialname == opts.serialname

    def test_env_name_no_serial_name_in_cmdline(self):
        """Name defined in environment, serial, name: honor cmdline name."""
        os.environ[servo_parsing.NAME_ENV_VAR] = self._invalid_name
        # Regenerate the parser as this test modifies the os.environ map.
        self.setup_parser()
        cmdline = ["--name", self._valid_name]
        opts, _unused = self._parser.parse_known_args(cmdline)
        assert self._serialname == opts.serialname

    def test_name_serial(self):
        """Serial and name defined: raise an error."""
        cmdline = ["--name", self._valid_name, "--serialname", self._serialname]
        with self.assertRaisesRegex(SystemExit, "2"):
            _unused = self._parser.parse_known_args(cmdline)

    def test_name_no_serial_board(self):
        """Name, and board defined: name maps to serial but no board overwrite."""
        new_board = "new-board"
        cmdline = ["--name", self._valid_name, "--board", new_board]
        opts, _unused = self._parser.parse_known_args(cmdline)
        assert self._serialname == opts.serialname
        assert new_board == opts.board

    def test_name_no_serial_no_board(self):
        """Only name defined: name maps to serial and adds board."""
        cmdline = ["--name", self._valid_name]
        opts, _unused = self._parser.parse_known_args(cmdline)
        assert self._serialname == opts.serialname
        assert self._board == opts.board

    def test_name_not_in_rc_no_serial(self):
        """Name is provided but no in RC: SystemExit from the parser."""
        cmdline = ["--name", self._invalid_name]
        with self.assertRaisesRegex(
            servo_parsing.ServodParserError, "Name %r not in rc" % self._invalid_name
        ):
            _unused = self._parser.parse_known_args(cmdline)

    def test_no_name_serial_in_rc_no_board(self):
        """Serial shows up in the RC, & no board specified: take the rc's board."""
        cmdline = ["--serialname", self._serialname]
        opts, _unused = self._parser.parse_known_args(cmdline)
        assert self._board == opts.board


class TestServodClientParser(unittest.TestCase):
    """Test ServoScratch based routing in ServodClientParser."""

    def setUp(self):
        """Create fake scratch entry, and setup cmdline args for tests."""
        unittest.TestCase.setUp(self)
        self._original_env = copy.deepcopy(os.environ)
        # The tests that want to manipulate the environment will do so themselves.
        # Thus, remove potential environments from the directory the test is being
        # run in.
        for env_var in [servo_parsing.PORT_ENV_VAR, servo_parsing.NAME_ENV_VAR]:
            if env_var in os.environ:
                del os.environ[env_var]
        self._scratchdir = tempfile.mkdtemp()
        self._scratch = scratch.Scratch(self._scratchdir)
        self._fakesock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._fakesock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._fakesock.bind(("localhost", 0))
        self._scratchport = self._fakesock.getsockname()[1]

        self._serial = "this-is-a-fake-serial"
        self._invalid_serial = "this-is-an-invalid-fake-serial"
        # PID not stored as a variable as it's not part of the test.
        self._scratch.add_entry(
            port=self._scratchport, serials=[self._serial], pid=1234
        )
        self.setup_parser()
        # Bind a fake socket to the port to avoid the ServoScratch from
        # cleaning up this invalid entry when the parser initializes it.
        self._rc_name = "valid_name"
        self._rc_file = TestRCFile.create_fake_rc_file(
            name=self._rc_name, serial=self._serial, board="fake-board"
        )
        # Overwrite default file to use the test's rc file
        self._original_rc = servo_parsing.DEFAULT_RC_FILE
        servo_parsing.DEFAULT_RC_FILE = self._rc_file

    def setup_parser(self):
        """Helper to add parser."""
        self._parser = servo_parsing.ServodClientParser(scratchdir=self._scratchdir)

    def tearDown(self):
        """Remove fake scratch entry, and close fake socket."""
        shutil.rmtree(os.path.dirname(self._rc_file))
        shutil.rmtree(self._scratchdir)
        servo_parsing.DEFAULT_RC_FILE = self._original_rc
        self._fakesock.close()
        os.environ = self._original_env
        unittest.TestCase.tearDown(self)

    def test_no_port_serial(self):
        """No port but serialname in cmdline: look for the port in scratch."""
        cmdline = ["--serialname", self._serial]
        opts, _unused = self._parser.parse_known_args(cmdline)
        assert self._scratchport == opts.port

    def test_env_port_serial(self):
        """Env port and serialname in cmdline: look for the port in scratch."""
        os.environ[servo_parsing.PORT_ENV_VAR] = "1782"
        # Regenerate the parser as this test modifies the os.environ map.
        self.setup_parser()
        cmdline = ["--serialname", self._serial]
        opts, _unused = self._parser.parse_known_args(cmdline)
        assert self._scratchport == opts.port

    def test_env_port_invalid_env_name(self):
        """Env port and unknown name. An error is expected."""
        os.environ[servo_parsing.PORT_ENV_VAR] = str(self._scratchport)
        rc_name = "random_name"
        os.environ[servo_parsing.NAME_ENV_VAR] = rc_name
        # Regenerate the parser as this test modifies the os.environ map.
        self.setup_parser()
        cmdline = []
        with self.assertRaisesRegex(
            servo_parsing.ServodParserError, "Name %r not in rc" % rc_name
        ):
            _unused = self._parser.parse_known_args(cmdline)

    def test_env_port_valid_env_name_in_scratch(self):
        """Env port and known name. Name is used to lookup port in scratch."""
        port = "912749"
        # This port should not be used as a known name is provided that has a
        # scratch entry.
        os.environ[servo_parsing.PORT_ENV_VAR] = port
        os.environ[servo_parsing.NAME_ENV_VAR] = self._rc_name
        # Regenerate the parser as this test modifies the os.environ map.
        self.setup_parser()
        cmdline = []
        opts, _unused = self._parser.parse_known_args(cmdline)
        assert self._scratchport == opts.port

    def test_env_port_valid_env_name_not_in_scratch(self):
        """Env port and known name that is not in scratch. Throw error."""
        # Removing the scratch entry so that the port lookup fails.
        self._scratch.remove_entry(self._scratchport)
        port = "912749"
        # This port should be used as an unknown name is provided that does not
        # have a scratch entry.
        os.environ[servo_parsing.PORT_ENV_VAR] = port
        os.environ[servo_parsing.NAME_ENV_VAR] = self._rc_name
        # Regenerate the parser as this test modifies the os.environ map.
        self.setup_parser()
        cmdline = []
        with self.assertRaisesRegex(SystemExit, "2"):
            _unused = self._parser.parse_known_args(cmdline)

    def test_no_port_no_serial(self):
        """No port and no serialname in cmdline: revert to default port."""
        cmdline = []
        opts, _unused = self._parser.parse_known_args(cmdline)
        assert client.DEFAULT_PORT == opts.port

    def test_no_port_serial_no_dut_on_serial(self):
        """No port and serialname in cmdline, serialname not in scratch: error."""
        cmdline = ["--serialname", self._invalid_serial]
        # Argparse raises sys.exit(2) on error.
        with self.assertRaisesRegex(SystemExit, "2"):
            _unused = self._parser.parse_known_args(cmdline)


if __name__ == "__main__":
    unittest.main()
