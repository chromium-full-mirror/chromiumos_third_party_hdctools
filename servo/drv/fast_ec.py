# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""A fast driver to set/retrieve data from a cros ec interface."""

import re

from servo.drv import simple_ec


# pylint: disable=invalid-name
# naming convention needed for servod driver query.
class fastEc(simple_ec.simpleEc):
    """Object to access drv=fast_ec controls."""

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

    CROS_EC_ERROR_RX = "|".join(CROS_EC_ERROR_STRING_RX)

    def _get_safe_output(self, cmd, regex):
        """Expansion to also search for known error strings.

        This expands the implementation of |_get_safe_output| to also search
        for known error strings, and speed up failures if the UART command has
        already failed.

        Args:
          cmd: command to run
          regex: regex to match.

        Returns:
          output of running |cmd| and matching with |regex| on |self._interface|

        Raises:
          ecError: if the output from the |self._uart_cmd| matched with the
                   |self._regex| is None
        """
        # create an extended regex that checks for the known errors or the original
        # regex.
        eregex = self.CROS_EC_ERROR_RX + "|" + regex
        self._logger.debug("Using extended regex %r for error catching", eregex)
        # pylint: disable=protected-access
        # This is a |simpleEc| child class, this is accessing its own
        # protected member.
        results = simple_ec.simpleEc._get_safe_output(self, cmd, eregex)
        # Now, we need to inspect member 0 (the full match), and see whether
        # it matched with any of the known errors.
        if re.search(self.CROS_EC_ERROR_RX, results[0]):
            # a known error occurred, raise an error.
            # |e| is for extra info to log.
            e = "Ran into cros ec error: %r" % results[0]
            # pass |regex| and not |eregex| as that just pollutes the error logs.
            # All the user needs to know is 'which' error triggered.
            self._error(cmd, regex, e)
        # Nothing went wrong, just return the |results|
        return results
