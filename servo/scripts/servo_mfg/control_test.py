# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""A servod test issuing a control and checking the output."""

import re

from servo_mfg import test

import servo.client as client


class ControlTestError(test.TestError):
    """ControlTest error class."""


class ControlTest(test.Test):
    """A control test to check if a control can be issued and output matches."""

    def __init__(self, name, regex, ctrl=None):
        """Initialize the test.

        Args:
          name: name of the test
          regex: the regex that the control output should match
          ctrl: optional, if the control name is different from the test name
                if not provided, it is assumed that the control is called |name|
        """
        test.Test.__init__(self, name)
        # Expand the name to show it's a servod control test.
        self.name = "%s [servod control test]" % self.name
        # Allow for the name to be different from the control.
        self._ctrl = ctrl if ctrl else name
        self._regex = re.compile(regex)
        # The generic line should be improved if the test is more specific.
        self.base_debug_line = "Issue getting servod control %r" % self._ctrl

    def run(self):
        """Run the control and check against the regex.

        Returns:
          list of one tuple (name, result) where
            name: is the name of the test (or control if both are the same)
            result: is whether the control succeeded and matched the output
        """
        try:
            self._logger.debug("Running %s", self._ctrl)
            # This always casts to string to compare. If your control
            # has a different output file format, you need to either adjust
            # the regex, or write a different test class for it.
            output = str(self.client.get(self._ctrl))
            self._logger.debug("%r output: %r", self._ctrl, output)
            match = re.match(self._regex, output)
            result = True
            if match is None:
                self._logger.debug(
                    "Output %r did not match regex %r", output, self._regex.pattern
                )
                result = False
        except client.ServoClientError as e:
            # We only log the details to debug here, as the upper layers will take
            # care of reporting the failure to the user.
            self._logger.debug("Failed with %r", str(e))
            result = False
        return [(self.name, result)]
