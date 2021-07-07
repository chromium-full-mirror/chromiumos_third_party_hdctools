# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import time

DEFAULT_POLLING_INTERVAL = 0.0
DEFAULT_POLLING_TIMEOUT = None # meaning no timeout

class PollingControl(object):
  """Object to poll a control on a servo until it reaches an expected result"""

  def _found_expected_result(self, servod, control, expected_result):
    """
    Get a control from a servod and compare it to the expected result

    Args:
      servod: a servod object with a get method
      control: the control to get
      expected_result: the expected value for the control
    """
    value = servod.get(control)
    return value == expected_result

  def _start_polling_timer(self):
    """Get the start time of polling to be able to know when to timeout"""
    self.start_polling_time = time.time()

  def _get_polling_timer(self):
    """Return the time since the beginning of the polling"""
    return time.time() - self.start_polling_time

  def _polling_timeout(self, polling_timeout):
    """Return whether or not we have timeout while polling"""
    return self._get_polling_timer() > polling_timeout if polling_timeout is not None else False

  def poll(self, servod, control, expected_result,
           polling_interval = DEFAULT_POLLING_INTERVAL,
           polling_timeout = DEFAULT_POLLING_TIMEOUT):
    """
    Poll a control until either the control is at the expected value or it timeouts

    Args:
      servod: a servod object with a get method
      control: the control to get
      expected_result: the expected output for the control
      polling_interval: the time to wait between 2 polling (default: 0s)
      polling_timeout: the time after which to timeout (default: do not timeout)

    Returns:
      True when the expected result is found
      False when timeout
    """
    self._start_polling_timer()
    while True:
      if self._found_expected_result(servod, control, expected_result):
        return True
      if self._polling_timeout(polling_timeout):
        return False
      time.sleep(polling_interval)

