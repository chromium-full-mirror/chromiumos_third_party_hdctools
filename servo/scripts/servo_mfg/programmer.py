# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Base programmer outlining the interface to program."""

import logging
import traceback

from servo_mfg import device_util


# pylint: disable=g-bad-exception-name
class ProgrammerError(Exception):
    """Programmer error class."""


# The default timeout to wait for a parent hub to show up.
# This is very small, as it is the responsibility of the outer loop
# to ensure that the hub is present. This cannot be overwritten through
# and argument.
PARENT_HUB_TIMEOUT_S = 0.1


# The default timeout to wait for a device to show up. This is larger, to allow
# for devices to enumerate if their hub as just been reset for example, or
# plugged in. See _find() on how this can be overwritten for specific scenarios.
DEV_TIMEOUT_S = 3


class Programmer(object):
    """Class to program one device for the servo manufacturing.

    In this context, a device is one one of the chips on the board e.g.
    - main servo MCU
    - ethernet dongle
    - usb hub
    - atmega keyboard emulator
    """

    NAME = "Generic"

    LOGGER_SUFFIX = "Programmer"

    def __init__(self, force=False):
        """Initialize the logger, and all usb device data.

        Note: |force| in this context means to perform the taks without checking the
        chip is already programmed. This can mean different things for different
        chips but the base implementation means that we do not run |_verify| before
        programming if |force| = True. This has two main implications:
        - subclasses should ensure that a programmed chip will be programmed again
          if only |_program| runs
        - subclass should ensure that reprogramming the same chip does not cause
          unexpected failures

        Args:
          force: whether to force programming if chip already appears programmed
        """
        self._logger = logging.getLogger("%s %s" % (self.NAME, self.LOGGER_SUFFIX))
        # Subclasses can fill these out to leverage the built in functions
        # to find the usb device.
        self._parent_hub_vid = None
        self._parent_hub_pid = None
        self._parent_hub_pid3 = None
        self._vid = None
        self._pid = None
        self._force = force
        # Set this flag in the subclass if you want to avoid pre-checking
        # if the device is already flashed. This can be used for devices where
        # checking externally cannot be done well, and the flashing call itself
        # has to be relied upon to report success or failure.
        self._no_precheck = False

    def program(self, **kwargs):
        """Main function to program the chip.

        Args:
          **kwargs: arguments to pass onto |_program()| and |_verify()|

        Returns:
          result of self._verify()
        """
        self.info("running")
        # This is merely to double check. This can fail, however it is the
        # responsibility of the manufacturer to actually check and wait for the usb
        # device to be available.
        self._find()
        # This is called here, and not called and cached to allow a user without
        # the programming environment to validate it, if necessary. Should the
        # programming environment also be required for validation, please overwrite
        # |validate()| in the subclass as needed.
        self._verify_programming_env()
        if self._force:
            self.info("--force is set, not checking, will program regardless.")
            pass
        else:
            if not self._no_precheck and self._verify(**kwargs):
                # See __init__ for the |self._no_precheck| flag.
                self.info("Chip already programmed, nothing to do")
                return True
        try:
            self._program(**kwargs)
            self.info("Success programming.")
        # We need a broad exception here to make sure the manager can proceed
        # and report issues to the user.
        except Exception as e:
            for line in traceback.format_exc().splitlines():
                self._logger.debug(line)
            self.error("failed: %r", str(e))
            return False
        outcome = self._verify(**kwargs)
        self.info("finished")
        return outcome

    def validate(self, **kwargs):
        """Validate that the chip is programmed as expected.

        Args:
          **kwargs: arguments to pass onto |_program()| and |_verify()|

        Returns:
          result of self._verify()
        """
        self.info("validating")
        self._find()
        outcome = self._verify(**kwargs)
        self.info("finished")
        return outcome

    def _find(self, pid=None, timeout=DEV_TIMEOUT_S):
        """Helper to ensure that the chip is present.

        Note: this is just a default implementation, because it's the most common
        flow. If a new programmer requires a different way to find the device
        or more information, please ovewrite, or extend this implementation.

        If the vid/pid are stored in their self._ members, this method will find
        the /sys/bus/usb/devices folder of the device and return it, or raise
        an error if not found.

        If the parent hub vid/pid are stored in their self._ members, this method
        will also ensure that self._vid/pid are a child device of
        self._parent_hub_vid/pid

        Args:
          pid: the pid of the device to find
          timeout: time in seconds to wait for the device to enumerate

        Returns:
          /sys/bus/usb/devices path to self._vid/pid device if identifiers
          provided, and device found, None otherwise

        Raises:
          ProgrammerError: if self._vid/pid provided and device not found
          ProgrammerError: if self._parent_hub_vid/pid provided and hub not found
          ProgrammerError: if self._vid/pid and self._parent_hub_vid/pid provided
                                the device is not a child node of the parent hub
        """
        if pid is None:
            # Some devices depending on the mode enumerate with different PIDs.
            # This allows for a mechanism for those devices to report that.
            pid = self._pid
        p_path = path = p3_path = None
        parent_candidates = []
        if self._parent_hub_vid and self._parent_hub_pid:
            try:
                p_path = device_util.wait_for_usb_device(
                    vid=self._parent_hub_vid,
                    pid=self._parent_hub_pid,
                    timeout=PARENT_HUB_TIMEOUT_S,
                )
                parent_candidates.append(p_path)
                self.debug(
                    "Found usb hub with %04x:%04x at %s",
                    self._parent_hub_vid,
                    self._parent_hub_pid,
                    p_path,
                )
            except device_util.DeviceUtilError:
                # Especially if there are two possible parents (usb3 and usb2),
                # this is not an issue.
                self.debug(
                    "usb hub with %04x:%04x not found.",
                    self._parent_hub_vid,
                    self._parent_hub_pid,
                )
                pass
        # |wait_for_usb_device| supports finding a device with either pid or pid3.
        # However, it only returns one sysfs path - the first one it finds. We need
        # both paths (if they exist) as we don't know if the device enumerates as
        # usb2 or usb3 device, and therefore need to check both. This is to note
        # why this logic is here twice, rather than using the API with its pid3
        # support.
        if self._parent_hub_vid and self._parent_hub_pid3:
            try:
                p3_path = device_util.wait_for_usb_device(
                    vid=self._parent_hub_vid,
                    pid=self._parent_hub_pid3,
                    timeout=PARENT_HUB_TIMEOUT_S,
                )
                parent_candidates.append(p3_path)
                self.debug(
                    "Found usb hub with %04x:%04x at %s",
                    self._parent_hub_vid,
                    self._parent_hub_pid3,
                    p3_path,
                )
            except device_util.DeviceUtilError:
                # Especially if there are two possible parents (usb3 and usb2),
                # this is not an issue.
                self.debug(
                    "usb hub with %04x:%04x not found.",
                    self._parent_hub_vid,
                    self._parent_hub_pid3,
                )
                pass
        if self._vid and pid:
            try:
                path = device_util.wait_for_usb_device(
                    vid=self._vid, pid=pid, timeout=timeout
                )
                self.debug(
                    "Found usb device with %04x:%04x at %s", self._vid, pid, path
                )
            except device_util.DeviceUtilError as e:
                # repackage here as ProgrammerError to make catching simpler
                # in higher layers
                raise ProgrammerError("%s: %s" % (self.NAME, str(e)))
        # TODO(coconutruben): add an error if there were parent candidates provided,
        # but none were found
        if parent_candidates and not any(
            [p and path.startswith(p) for p in parent_candidates]
        ):
            # TODO(coconutruben): log what the candidates were here.
            # pylint: disable=bad-string-format-type
            # self._vid is set to non-None in the subclasses.
            raise ProgrammerError(
                "Required device %04x:%04x not hanging on expected"
                " parent hub." % (self._vid, pid)
            )
        return path

    def _program(self, **kwargs):
        """Helper to perform actual programming."""
        raise NotImplementedError()

    def _verify(self, **kwargs):
        """Helper to verify that programming succeeded."""
        raise NotImplementedError()

    def _verify_programming_env(self):
        """Helper to validate that programming tools are available."""
        raise NotImplementedError()

    def verify_programming_env(self):
        """True/False wrapper around |_verify_programming_env|."""
        try:
            self._verify_programming_env()
            return True
        except ProgrammerError:
            return False

    # The helpers below are to raise common errors, and have standardized
    # reporting on them.

    def exec_missing(self, exec_name):
        """Helper error when an executable binary is missing.

        Args:
          exec_name: binary name missing on the host environment

        Raises:
          ProgrammerError: always, as it's a wrapper to raise the error
        """
        raise ProgrammerError(
            "%r executable needs to be available, not found in PATH." % exec_name
        )

    def bin_file_missing(self, binfile):
        """Helper error when a binary is missing required for programming.

        Args:
          binfile: binary name missing in the servo mfg's binary folder

        Raises:
          ProgrammerError: always, as it's a wrapper to raise the error
        """
        raise ProgrammerError("%r needs to be available in the binfiles." % binfile)

    # These are convenience log functions to make sure that the name is always
    # printed as well.

    def _log_line(self, line):
        """Helper to log.

        Args:
          line: line to log

        Returns:
          formatted |line| with the device's |self.NAME| to log more precisely
        """
        return "%s: %s" % (self.NAME, line)

    def debug(self, line, *args):
        """Helper to log formatted |line| with |*args| fed to logging.debug.

        Args:
          line: line to log
          *args: args to forward to logging string formatting
        """
        self._logger.debug(self._log_line(line), *args)

    def info(self, line, *args):
        """Helper to log formatted |line| with |*args| fed to logging.info.

        Args:
          line: line to log
          *args: args to forward to logging string formatting
        """
        self._logger.info(self._log_line(line), *args)

    def error(self, line, *args):
        """Helper to log formatted |line| with |*args| fed to logging.error.

        Args:
          line: line to log
          *args: args to forward to logging string formatting
        """
        self._logger.error(self._log_line(line), *args)

    def throw_error(self, line, *args):
        """Throw error and log formatted |line| with |*args| fed to logging.error.

        Args:
          line: line to log
          *args: args to forward to logging string formatting

        Raises:
          ProgrammerError: always, as it's a wrapper to raise it
        """
        self.error(line, *args)
        raise ProgrammerError()
