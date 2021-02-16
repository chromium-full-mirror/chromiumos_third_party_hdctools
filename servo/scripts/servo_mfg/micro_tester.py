# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Base programmer outlining the interface to program."""

from servo_mfg import control_test
from servo_mfg import tester


class MicroTester(tester.Tester):
  """Class to handle one manufacteuring round for one device type."""

  PHASE = 1

  def _register(self):
    """Register all tests for servo micro."""
    # This is broken out to allow for clean readability and maintainability
    # Check the serialnumber to validate communication to the MCU works.
    test = control_test.ControlTest(name='serialname', regex='.+')
    # Indicate test is to check basic communication.
    test.base_debug_line = 'Basic communication with servo EC failed.'
    self._register_test(test)
    # TODO(b/169900864): expand to test all communications on the gpio
    # expander(s).
