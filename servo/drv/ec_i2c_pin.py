# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Driver to talk to the i2c channels through the DUT EC console."""

import re

from servo.drv import ec


# pylint: disable=invalid-name
# This conforms to the servod error naming pattern.
class ecI2cPinError(ec.ecError):
    """Exception class for ec i2c pin."""


# TODO(b/180671248): delete this code (better yet, revert the CL as
# soon as that change lands.
# A list of all cros ec error regex strings.
# source: src/platform/ec/common/console.c
CROS_EC_ERROR_STRING_RX = [
    r"Unknown error",
    r"Unimplemented",
    r"Overflow",
    r"Timeout",
    r"Invalid argument",
    r"Busy",
    r"Access Denied",
    r"Not Powered",
    r"Not Calibrated",
    r"Parameter \d+ invalid",
    r"Wrong number of params",
    r"Command returned error \d+",
    r"Command '\w+' not found or ambiguous.",
]

CROS_EC_ERROR_RX = "(" + "|".join(CROS_EC_ERROR_STRING_RX) + ")"


# pylint: disable=invalid-name
# This conforms to the servod drv naming convention.
class ecI2cPin(ec.ec):
    """Class to handle communication with the EC console."""

    # 'i2cxfer %s[w|r] %d[bus] 0x%x[addr] 0x%x'[offset]
    BASE_CMD = "i2cxfer %s %d 0x%x 0x%x"

    REGEX = r"(0x[0-9a-f]+) \[\d+\][\n\r]"

    REQUIRED_GET_PARAMS = ["bus", "addr", "offset", "mask"]
    REQUIRED_SET_PARAMS = REQUIRED_GET_PARAMS

    def _drv_init(self):
        """Driver specific initializer."""
        super()._drv_init()
        # Set the valid input choices for this driver.
        # _choices needs to be a compiled regex
        self._choices = re.compile("^(0|1)$")
        self._mask = int(self._params["mask"], 0)
        self._logger.debug("Mask %d" % self._mask)
        if bin(self._mask).count("1") != 1:
            # We want a binary mask.
            raise ecI2cPinError(
                "Mask 0x%x covers does not mask only one bit" % self._mask
            )
        bus = int(self._params["bus"])
        addr = int(self._params["addr"], 0)
        offset = int(self._params["offset"], 0)
        self._read = self.BASE_CMD % ("r", bus, addr, offset)
        self._write_base = self.BASE_CMD % ("w", bus, addr, offset)
        # TODO(b/180671248): delete this code
        # expand the regexes to also look for errors.

    def _get_cmd_results(self, cmd, regex):
        """Overwrite to also catch ec console errors.

        Args:
          cmd: command to send to the EC console
          regex: regex to look for

        Returns:
          result of the command

        Raises:
          ecI2cPinError: if a known issue issue is found.
        """
        # TODO(b/180671248): delete this method.
        # modified regex to also catch errors.
        mregex = CROS_EC_ERROR_RX + "|" + regex
        r = ec.ec._issue_cmd_get_results(self, cmd, [mregex])
        if r is None:
            raise ecI2cPinError("Failed to read out the i2c register value")
        # we know that |r| is a list of list/tuple to match regex. So we need
        # to check whether it matched an error string.
        if re.search(CROS_EC_ERROR_RX, r[0][0]):
            raise ecI2cPinError("Ran into cros ec error: %r" % r[0][0])
        # We only ever pass in one regex in this drv/so there is only ever
        # one member in the highest level.
        return r[0]

    def _set(self, value):
        """Set the bit to tbe |value|."""
        # register value
        rv = self._raw_read()
        if value:
            rv |= self._mask
        else:
            rv &= ~self._mask
        # actually need to write the value.
        write_cmd = "%s 0x%x" % (self._write_base, rv)
        # Simply wait until the writing is finished.
        self._get_cmd_results(write_cmd, "(>)")

    def _raw_read(self):
        """Read the raw hex value out for the whole offset."""
        # TODO(coconutruben): unify this with |_Get_output| in the ec.
        self._limit_channel()
        result = self._get_cmd_results(self._read, self.REGEX)
        self._restore_channel()
        # The regex has None as its first group (because nothing in the error group
        # matched). Need to get to the second group.
        val_str = result[2]
        val = int(val_str, 16)
        return val

    def _get(self):
        """Read out the value."""
        # Cast through bool to make it binary (it's set or it's not), and then
        # through int to return a proper int as required by the servod code.
        return int(bool(self._raw_read() & self._mask))
