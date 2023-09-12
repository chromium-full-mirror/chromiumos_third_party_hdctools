# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Programmer for the ethernet dongle found on v4, v4p1."""

import glob
import os
import shutil
import tempfile
import time

from servo_mfg import device_util
from servo_mfg import exec_util
from servo_mfg import programmer
from servo_mfg import util

import servo.utils.usb_hierarchy as usb_hierarchy


class RTKEthProgrammerError(programmer.ProgrammerError):
    """RTK eth programmer error class."""


class RTKEthProgrammer(programmer.Programmer):
    """Class to program the rtk eth dongle."""

    NAME = "Ethernet Adapter (RTL8153)"

    # The VID/PID of the ethernet dongle showing up as a USB device.
    DONGLE_VID = 0x0BDA
    DONGLE_PID = 0x8153

    PROGRAMMER_BIN = "rtunicpg"

    # These are the programmer parts to erase and write with the tool
    BASE_CMD = [PROGRAMMER_BIN, "/eeprom", "/93c46"]

    ERASE_CMD = BASE_CMD + ["/erase"]

    WRITE_CMD = BASE_CMD + ["/w"]

    # These are config files to run the programming with the |PROGRAMMER_BIN|.
    # These need to contain (a) the right information (especially macaddr), and
    # be in the working directory when executing the programmer.
    CONFIG_TEMPLATE = "EE8153BvB.cfg"
    SECONDARY_CONFIG = "EF8153BvB.cfg"

    # These are the fields to write the desired macaddr into.
    MACADDR_FIELDS = ["NODEID", "STARTID", "ENDID"]

    # .cfg files have ; as a comment delim
    COMMENT_DELIM = ";"
    # .cfg files have ' = ' as a separator betweeen keys and values
    KEY_VALUE_SEP = " = "

    # This is a wildcard path to pass to glob to find the device file
    # to read the current mac address out of.
    # Note: feed into this the dev hub path of the ethernet dongle i.e.
    # 1-3.4.2 or so if the dongle is at that location in /sys/bus/usb/devices
    DEV_GLOB = "/sys/bus/usb/devices/{0}/{0}:*/net/*/address"

    # Timeout for the networking path to be created after usb enumeration
    GLOB_TIMEOUT_S = 10

    # Rate at which to poll for the path to exist
    GLOB_POLL_RATE_S = 0.1

    def __init__(
        self, force, parent_hub_vid=None, parent_hub_pid3=None, parent_hub_pid=None
    ):
        """Initialize the logger.

        If the parent information is not provided, then only dongle presence is
        is checked, and not whether the dongle is hanging on the right hub.
        For the double detection _both_ vid and pid need to be provided.

        Args:
          force: whether to force programming if chip already appears programmed
          parent_hub_vid: vid for the hub the dongle is hanging on
          parent_hub_pid3: pid for the same hub but as usb3 that the dongle is
                           hanging on
          parent_hub_pid: pid for the hub the dongle is hanging on

        """
        programmer.Programmer.__init__(self, force=force)
        self._parent_hub_vid = parent_hub_vid
        self._parent_hub_pid = parent_hub_pid
        self._parent_hub_pid3 = parent_hub_pid3
        self._vid = self.DONGLE_VID
        self._pid = self.DONGLE_PID
        self._template_path = None

    def _standardize_macaddr(self, macaddr):
        """Standardize on : as a separator and upper-case.

        Args:
          macaddr: macaddr in any case with - or : as delimited

        Returns:
          macaddr: all upper case with exclusively : as delimiter
        """
        return macaddr.upper().replace("-", ":")

    def _macaddr_for_cfg(self, macaddr):
        """The .cfg format requires spaces rather than : as separators.

        Args:
          macaddr: macaddr (after it has been passed through |_standardize_macaddr|

        Returns:
          macaddr: with all delimiters (:) replaced with spaces
        """
        return self._standardize_macaddr(macaddr).replace(":", " ")

    def _move_config(self, dst, macaddr):
        """Move and prepare the config files to |dst|.

        Since the original config files serve as a template, they need to be copied
        to a directory and modified to have the unique macaddr for a device before
        programming. This method does not clean up |dst| but merely populates it.

        Args:
          dst: directory to move the config files to
          macaddr: macaddr to program onto the chip
        """
        # We know this works based on having check the environment before.
        shutil.copy(util.find_binfile(self.SECONDARY_CONFIG), dst)
        # The primary config needs to be rewritten so that the macaddr
        # is properly programmed.
        src = util.find_binfile(self.CONFIG_TEMPLATE)
        dst = os.path.join(dst, os.path.basename(src))
        macaddr_out = self._macaddr_for_cfg(macaddr)
        output = []
        with open(src, "r", encoding="utf-8") as s:
            for line in s:
                # Goal of this loop is to copy all lines that have
                # nothing to do with macaddr, and modify the macaddr ones so that
                # the resulting .cfg file can be used to program for a specific
                # macaddr.
                if line.startswith(self.COMMENT_DELIM):
                    output.append(line)
                elif self.KEY_VALUE_SEP not in line:
                    output.append(line)
                else:
                    # The value does not matter as there are only two cases:
                    # - the line is not a macaddr line: transcribe the whole line again
                    # - the line is a macaddr line: we need to write |macaddr| as the
                    # value anyways
                    k, _unused = line.split(self.KEY_VALUE_SEP)
                    if k not in self.MACADDR_FIELDS:
                        # This is a different field. Just write it over as is.
                        output.append(line)
                    else:
                        # This is one of the lines that requires us to rewrite it to the
                        # macaddr. Do so here.
                        output.append("%s%s%s\n" % (k, self.KEY_VALUE_SEP, macaddr_out))
        with open(dst, "w", encoding="utf-8") as d:
            for line in output:
                d.write(line)

    def _program(self, macaddr, tiny_servod, **_):
        """Helper to perform actual programming.

        Prepare the config files and program the ethernet chip using the
        binary, config files, and |macaddr|.

        Args:
          macaddr: macaddr to program onto the chip
          tiny_servod: TinyServod instance to talk to the servo EC
        """
        # Create temp file and write the config into it. This needs to be
        # deleted at the end again.
        wd = os.getcwd()
        program_dir = tempfile.mkdtemp()
        try:
            # Need to be in that directory to program.
            os.chdir(program_dir)
            self._move_config(program_dir, macaddr)
            ret, _unused, _unused = exec_util.exec_blocking(
                self.ERASE_CMD, hint="erasing"
            )
            if ret:
                self.throw_error("Failed to erase.")
            ret, _unused, _unused = exec_util.exec_blocking(
                self.WRITE_CMD, hint="writing"
            )
            if ret:
                self.throw_error("Failed to write.")
            # If everything went well so far, then we can write the macaddr
            # into the servo eeprom as well.
            cmd = "macaddr set %s" % self._standardize_macaddr(macaddr)
            # pylint: disable=protected-access
            # private function access pattern required by API
            tiny_servod.pty._issue_cmd(cmd)
        finally:
            shutil.rmtree(program_dir)
            os.chdir(wd)
        try:
            # After the mac addr is written, we need to reenumerate the device
            # on usb so that |_verify()| can read the new mac addr.
            usb_hierarchy.Hierarchy.ResetDeviceSysfs(self._find())
        except usb_hierarchy.HierarchyError as e:
            self.debug(e)
            # The device sometimes drops off even before issuing the reset. Skip
            # for now, if it's a real issue _verify() will fails.
            # TODO(coconutruben): figure out why the device sometimes drops off
            # even before we issue the reset.
        # Wait for the device to come back.
        device_util.wait_for_usb_device(vid=self._vid, pid=self._pid)

    def _verify(self, macaddr, **_):
        """Helper to verify that programming succeeded.

        Args:
          macaddr: expected macaddr

        Returns:
          whether the macaddr found in sysfs for this chip is the same as |macaddr|
        """
        return macaddr.upper() == self._retrieve()

    def _retrieve(self):
        """Helper to read out the macaddr from sysfs (as programmed on the chip).

        Returns:
          macaddr: the mac address contained in the sysfs node, standardized

        Raises:
          RTKEthProgrammerError: if the device was not found after
          |self.GLOB_TIMEOUT_S|
        """
        path = self._find()
        # We need to find the address on this device. This is the path to do so.
        dev_path = os.path.basename(path)
        wildcard = self.DEV_GLOB.format(dev_path)
        address_paths = glob.glob(wildcard)
        end = time.time() + self.GLOB_TIMEOUT_S
        while len(address_paths) != 1:
            time.sleep(self.GLOB_POLL_RATE_S)
            if time.time() > end:
                raise RTKEthProgrammerError(
                    "Could not find /address file through "
                    "sysfs. Tried for %d seconds. "
                    "Got these candidates %s from this "
                    "wildcard %r" % (self.GLOB_TIMEOUT_S, address_paths, wildcard)
                )
            address_paths = glob.glob(wildcard)
        candidate = address_paths[0]
        with open(candidate, "r", encoding="utf-8") as f:
            addr = self._standardize_macaddr(f.read().strip())
            self.debug("Retrieved %r from %r", addr, candidate)
            return addr

    def _verify_programming_env(self):
        """Helper to validate that programming tools are available."""
        # find the programming tool
        if not util.validate_exec_available(self.PROGRAMMER_BIN):
            self.exec_missing(self.PROGRAMMER_BIN)
        # find the template text file in binary
        if not util.find_binfile(self.SECONDARY_CONFIG):
            self.bin_file_missing(self.SECONDARY_CONFIG)
        if not util.find_binfile(self.CONFIG_TEMPLATE):
            self.bin_file_missing(self.CONFIG_TEMPLATE)
