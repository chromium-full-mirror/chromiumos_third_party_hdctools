# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Base test defining the interface for tests."""

import logging


class TestError(Exception):
    """Test error class."""


class Test(object):
    """Class to encapsulate one test to run on the servo device."""

    def __init__(self, name):
        """Initialize the test.

        Args:
          name: the name of the test
        """
        self._logger = logging.getLogger(type(self).__name__)
        self.name = name
        # The client is set to None initially as servod is not ready/nor has a
        # client by the time the test is created. This gets populated on successful
        # servod startup. Note in tester.py that no Test objects are run if servod
        # does not come up successfully.
        self.client = None
        # Populate this if you wish to indicate some debug help for the user.
        # This will be called after the test is done and has failed. You can
        # also dynamically change this to reflect what went wrong in the test.
        self.base_debug_line = None

    @property
    def debug_line(self):
        """Helper string to print on test failure."""
        # The base implementation simply returns the base debug line.
        # Note: feel free to overwrite this for more complex tests.
        return self.base_debug_line

    def prompt(self):
        """This will be called if the user needs to do anything for this test.

        Leverage this space to prompt the user for things. Do not ask for
        confirmation yet (enter to confirm etc). Rather, the system issues
        all prompts at once, and then asks for confirmation that everything is setup
        *once*.
        """

    def prep(self, client):
        """This is the phase to do any prep.

        It's also the phase where we store the servod client. If you expand
        prep because your test requires more prep, make sure to call this
        method still to store the client.

        Args:
          client: servod client object
        """
        self.client = client

    def run(self):
        """Implement the core test logic here.

        Returns: list of tuples (name, result) where
          name: is the name of the subtest
          result: is the outcome

        Note: tests that only test one thing should just return a one member list.
        """
        raise NotImplementedError("Please implement test logic.")
