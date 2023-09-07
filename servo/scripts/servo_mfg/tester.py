# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Base tester, doing common work and providing interface."""

import logging
import traceback

from servo_mfg import exec_util
from servo_mfg import user_input

import servo.client as client
import servo.utils.scratch as scratch


class TesterError(Exception):
    """Tester error class."""


class Tester(object):
    """Class to start servod and run registered tests.

    Each device should specific their own tester (subclass) and register
    the applicable tests for it. The base test that every device goes through is
    servod starting up.
    """

    PHASE = 1

    # By default wait at most 30s for servod to start up.
    SERVOD_STARTUP_S = 30

    def __init__(self, report, serialno):
        """Initialize the tester.

        Args:
          report: report for the current device to add the test results to
          serialno: device serial number to start servod with
        """
        self._logger = logging.getLogger(type(self).__name__)
        self._tests = []
        self._register()
        self._serial = serialno
        # This is the servod client to pass for all tests to use.
        self._client = None
        self._servod_process = None
        self._report = report

    @property
    def wait_for_setup(self):
        """Whether the tester has steps that require the user to setup the test."""
        # Some devices can test without hooking up anything extra. Those devices
        # should overwrite this to be False to avoid unnecessary wait times for user
        # confirmation.
        return True

    def _register_test(self, test):
        """Internal interface for subclass to register a test.

        Note: tests are run sequentially. If a specific test should run before
        another test, register it in the desired order in the subclass.

        Args:
          test: a Test object to run.
        """
        self._tests.append(test)

    def _register(self):
        """Internal interface required in subclass to register _all_ tests."""
        raise NotImplementedError("Provide implementation for tests in subclass.")

    def start_servod(self):
        """Start servod as a subprocess."""
        ret, _, _ = exec_util.exec_blocking(
            ["servodtool", "device", "-s", self._serial, "usb-path"]
        )
        if ret:
            self._logger.error("No servo device with serial %r found", self._serial)
            return None
        servodp = exec_util.exec_nonblocking(["servod", "-s", self._serial])
        ret, _, _ = exec_util.exec_blocking(
            [
                "servodtool",
                "instance",
                "wait-for-active",
                "-s",
                self._serial,
                "--timeout",
                str(self.SERVOD_STARTUP_S),
            ]
        )
        if ret:
            if servodp.poll() is None:
                # This means that servod somehow got stuck coming up otherwise it would
                # have been found. Bail out here.
                servodp.kill()
            self._logger.error(
                "Servod started but never came up for serial %r", self._serial
            )
            return None
        # Now we need to find the servod port, to prepare the client.
        s = scratch.Scratch()
        # This can raise an error, but it's a valid error, so just let it go through
        # as it indicates that servod failed to come up somehow in the scratch.
        entry = s.FindById(self._serial)
        port = entry["port"]
        self._logger.info("Servod came up and is running on port %r", port)
        self._client = client.ServoClient(port=port)
        return servodp

    def stop_servod(self):
        """Stop the servod process."""
        if self._servod_process and self._servod_process.poll() is None:
            try:
                # If the process existed, and is still alive is what this means.
                self._servod_process.terminate()
            # pylint: disable=broad-except
            # The testing should not fail for any reason related to stoppin servod.
            except Exception as e:
                for line in traceback.format_exc().splitlines():
                    self._logger.debug(line)
                # This is super broad but necessary. stop_servod is called when things
                # have gone bad and potentially from inside an error handler or when
                # code is already cleaning up. Do not raise an exception.
                self._logger.debug("Turning down servod got %r. Ignoring", str(e))

    def _setup(self):
        """Setup testing: instruct user on how to prepare, and start servod.

        Returns:
          True if the setup was successful (user confirmed if required, servod
          started up as expected). False otherwise
        """
        for test in self._tests:
            test.prompt()
        result = True
        if self.wait_for_setup:
            # At the end, ask the user to confirm that everything is plugged in,
            # if required.
            result = user_input.instruct_user("", enter_to_confirm=True)
        if not result:
            self._logger.info("User did not confirm. Testing cancelled.")
            return False
        self._servod_process = self.start_servod()
        # Servod startup can be considered a base test. Report it accordingly.
        self._report.report_task("Servod startup", bool(self._servod_process))
        # Without servod, this doesn't make sense. Just skip.
        if not self._servod_process:
            return False
        for test in self._tests:
            test.prep(self._client)
        return True

    def run(self):
        """Wrapper around setup and subsequently testing if setup is successful.

        Returns:
          the combined outcome of |_setup()| & |_run()|
        """
        if self._setup():
            outcome = self._run()
        else:
            self._logger.info("Testing start-up failed. Not testing.")
            outcome = False
        return outcome

    def _run(self):
        """Test runner.

        Run and log outcomes of each test in order.

        Returns:
          True if all tests succeeded, False otherwise
        """
        outcomes = []
        for test in self._tests:
            results = test.run()
            for name, outcome in results:
                outcomes.append(outcome)
                self._report.report_task(name, outcome)
                if not outcome and test.debug_line:
                    # The test failed, and there is a debug line. Report it.
                    self._report.add_comment(test.debug_line)
        self.stop_servod()
        # Result will only be positive if all tests have passed.
        return all(outcomes)
