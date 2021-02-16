# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""c2d2 specific mfg tests."""

from servo_mfg import control_test
from servo_mfg import tester


class C2D2Tester(tester.Tester):
  """Class to handle one manufacteuring round for one device type."""

  PHASE = 1

  # c2d2 spends a lot of time trying to talk to consoles that are not available
  # during testing. Expand the boot-up time to 1.5 minutes (90s).
  SERVOD_STARTUP_S = 120

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
