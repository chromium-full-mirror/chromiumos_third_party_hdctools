# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility to manage information about different instances."""

import fcntl
import json
import logging
import os
import socket
import time


# This is a well-known path that should be consistent for every servod instance
# and client in a given runtime environment.
SERVO_SCRATCH_DIR = "/run/servoscratch"


# Key used to store whether the instance is active yet or still coming up.
ACTIVE_ENTRY_KEY = "active"

# Key name for device serial, port, and pid in the Scratch entry
SERIAL_KEY = "serials"
PORT_KEY = "port"
PID_KEY = "pid"


class ScratchError(Exception):
    """Error class for servo scratch utility."""


class Scratch:
    """Class to manage servod instance breadcrumbs used to query and control.

    Attributes:
      _logger: logger
      _scratch: directory to leave information in.
    """

    _NO_FOUND_WARNING = "No servod scratch entry found under id: %r."

    def __init__(self, scratch=SERVO_SCRATCH_DIR):
        """Initialize utility by creating |scratch| if necessary.

        Args:
          scratch: directory to write servod info into.

        Note:
          Unless for good reason (test, special setup) scratch should be left as
          its default.
        """
        self._dir = scratch
        self._logger = logging.getLogger(type(self).__name__)
        os.makedirs(self._dir, exist_ok=True)
        self._sanitize()

    def _entry_f(self, entry):
        """Generate a filename for |entry|."""
        return os.path.join(self._dir, str(entry[PORT_KEY]))

    def add_entry(self, port, serials, pid):
        """Register information about servod instance.

        Args:
          port: port servod is being served
          serials: list of serialnames for devices being served through instance
          pid: pid of the main servod process

        Raises:
          ScratchError: if port or pid aren't int convertible or serials isn't
          list convertible, if port or any serial in serials already has an entry
        """
        # TODO(coconutruben): add cmdline support
        # To make sure that the strings are the default 'string type' in py2 and py3
        # cast them through str() again. This will ensure that no encoding
        # identifier is printed
        try:
            serials = [str(s) for s in serials]
            entry = {
                PORT_KEY: int(port),
                SERIAL_KEY: list(serials),
                PID_KEY: int(pid),
                ACTIVE_ENTRY_KEY: False,
            }
        except (ValueError, TypeError) as e:
            raise ScratchError(
                "Entry arguments malformed. %s: %s" % (type(e).__name__, str(e))
            ) from e
        entryf = self._entry_f(entry)
        if os.path.exists(entryf):
            msg = "Adding entry for port already in use. Port: %d." % int(port)
            self._logger.error(msg)
            raise ScratchError(msg)
        serialfs = []
        for serial in entry[SERIAL_KEY]:
            serialf = os.path.join(self._dir, str(serial))
            if os.path.exists(serialf):
                # Add a symlink for each serial pointing back at the original file
                msg = "Adding entry in %s for serial already in use. Serial: %s." % (
                    serialf,
                    serial,
                )
                self._logger.error(msg)
                raise ScratchError(msg)
            serialfs.append(serialf)

        self._write_entry(entry)

        # Add the symlinks as well.
        for serialf in serialfs:
            os.symlink(os.path.basename(entryf), serialf)

    def remove_entry(self, identifier):
        """Remove information about servod instance.

        Args:
          identifier: either port where servod is being served, or a serial number
                      of one of the servod devices being served by instance
        """
        entryf = os.path.realpath(os.path.join(self._dir, str(identifier)))
        if not os.path.exists(entryf):
            self._logger.info("No entry available for id: %s. Ignoring.", identifier)
            return
        for f in os.listdir(self._dir):
            fullf = os.path.join(self._dir, f)
            if os.path.islink(fullf) and os.path.realpath(fullf) == entryf:
                os.remove(fullf)
        os.remove(entryf)

    def mark_active(self, identifier):
        """Mark entry at |identifier| as active."""
        entry = self.find_by_id(identifier)
        if entry[ACTIVE_ENTRY_KEY]:
            self._logger.info("Entry at %r already marked active.")
        else:
            entry[ACTIVE_ENTRY_KEY] = True
            self._write_entry(entry)

    def _write_entry(self, entry):
        """Write entry to file."""
        entryf = self._entry_f(entry)
        with open(entryf, "w", encoding="utf-8") as f:
            json.dump(entry, f)

    def get_all_entries(self):
        """Find and load servod instance info for all registered servod instances.

        Returns:
          List of dictionaries containing 'port', 'serials', and 'pid' of instance
        """
        entries = []
        for f in os.listdir(self._dir):
            entryf = os.path.join(self._dir, f)
            if os.path.islink(entryf) or os.path.isdir(entryf):
                continue
            with open(entryf, "r", encoding="utf-8") as f:
                try:
                    entries.append(json.load(f))
                except ValueError:
                    self._logger.warning(
                        "Removing file %r as it contains invalid JSON.", entryf
                    )
                    # Invalid json file
                    os.remove(entryf)
        return entries

    def generate_entry_from_port(self, port):
        """Given a port number, try to generate an entry from it.

        Tries to ask servod instance for information to retroactively
        add an entry.

        Args:
          port: port where the alleged servod instance is listening

        Returns:
          True if entry successfully rebuilt, False otherwise
        """
        # pylint: disable=protected-access
        # pylint: disable=import-outside-toplevel
        import servo.core.client as client

        msg = "nonsense"
        expected_output = "ECH0ING: %s" % msg
        try:
            sclient = client.ServoClient(port=port)
            if sclient._server.echo(msg) == expected_output:
                self._logger.warning(
                    "Port %r not registered but has a servod "
                    "instance bound to it. Retroactively adding the "
                    "instance.",
                    port,
                )
                serials = sclient._server.get_servo_serials()
                # The serials have to be unique. Enforce this here by creating a set
                serials = list(set(serials.values()))
                pid = sclient.get("servod_pid")
                self.add_entry(port=port, serials=serials, pid=pid)
                return True
        except socket.error:
            # expected to fail as no servod instance should be running on an
            # untracked port.
            return False
        except ScratchError:
            # Don't rebuild an entry if the entry already exists.
            return False

    def find_by_id(self, identifier):
        """Find and load servod instance info for identifier.

        Args:
          identifier: either port where servod is being served, or a serial number
                      of one of the servod devices being served by instance

        Returns:
          dictionary containing 'port', 'serials', and 'pid' of instance

        Raises:
          ScratchError: if no entry found under |identifier| or if entry found
                        is invalid json
        """
        entryf = os.path.join(self._dir, str(identifier))
        if not os.path.exists(entryf):
            raise ScratchError(self._NO_FOUND_WARNING % identifier)
        with open(entryf, "r", encoding="utf-8") as f:
            try:
                entry = json.load(f)
            except ValueError as e:
                # Invalid json file
                os.remove(entryf)
                raise ScratchError(
                    "id: %s had invalid json formatting. Removed." % identifier
                ) from e
        return entry

    def _sanitize(self):
        """Verify that all known servod ports are still in use, delete otherwise."""
        for entry in self.get_all_entries():
            testsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            port = entry[PORT_KEY]
            try:
                testsock.bind(("localhost", port))
                self._logger.warning(
                    "Port %r still registered but not bound to a "
                    "servod instance. Removing entry.",
                    str(port),
                )
                self.remove_entry(port)
            except socket.error:
                # Expected to fail when binding to a valid servod instance socket.
                pass
            finally:
                testsock.close()


class ConcurrencyGuard:
    """Context manager to limit concurrent servod startups or other noisy tasks.

    This uses a set of lock files to ensure that no more than |max_concurrency|
    servod instances are performing a specific noisy task at once.
    """

    def __init__(
        self,
        scratch_dir=SERVO_SCRATCH_DIR,
        max_concurrency=3,
        timeout=600,
        name="startup",
    ):
        """Initialize guard.

        Args:
          scratch_dir: directory to store lock files.
          max_concurrency: maximum number of simultaneous tasks.
          timeout: maximum time in seconds to wait for a slot.
          name: name of the lock file (e.g. "startup" or "imaging").
        """
        self._lock_dir = os.path.join(scratch_dir, "concurrency")
        self._max_concurrency = max_concurrency
        self._timeout = timeout
        self._name = name
        self._logger = logging.getLogger(type(self).__name__)
        self._fds = []
        os.makedirs(self._lock_dir, exist_ok=True)

    def __enter__(self):
        """Try to acquire one of the concurrency slots."""
        start_time = time.time()
        self._logger.info(
            "Waiting for %s concurrency slot (max %d)...",
            self._name,
            self._max_concurrency,
        )
        while time.time() - start_time < self._timeout:
            for i in range(self._max_concurrency):
                lock_file = os.path.join(self._lock_dir, "%s.%d.lock" % (self._name, i))
                try:
                    fd = os.open(lock_file, os.O_RDWR | os.O_CREAT)
                except OSError:
                    continue
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    # Success! Write our PID for visibility.
                    os.ftruncate(fd, 0)
                    os.lseek(fd, 0, os.SEEK_SET)
                    os.write(fd, str(os.getpid()).encode())
                    self._fds.append((fd, i))
                    self._logger.info("Acquired %s concurrency slot %d", self._name, i)
                    return self
                except OSError:
                    os.close(fd)
            time.sleep(2)
        raise ScratchError(
            "Timed out waiting for %s concurrency slot after %d seconds"
            % (self._name, self._timeout)
        )

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Release the acquired slot."""
        for fd, i in self._fds:
            try:
                # We don't delete the file, just unlock it.
                fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)
                self._logger.info("Released %s concurrency slot %d", self._name, i)
            except OSError:
                pass
