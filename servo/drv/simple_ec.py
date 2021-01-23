# Copyright 2021 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""A simple driver to set/retrieve simple data from a cros ec interface."""

from servo.drv import ec


# pylint: disable=invalid-name
# naming convention needed for servod driver query.
class simpleEc(ec.ec):
  """Object to access drv=simple_ec controls."""

  # This drv requires the
  # - the command to run |uart_cmd|
  # - the regex to match against |regex|
  # - the group within the regex to retrieve |group| or 0 to retrieve
  # the entire match
  REQUIRED_GET_PARAMS = ['uart_cmd', 'regex', 'group']

  def __init__(self, interface, params):
    """Constructor.

    Args:
      interface: cros ec based console interface
      params: dictionary containing data to run the command and get output
    """
    super(simpleEc, self).__init__(interface, params)
    self._uart_cmd = self._params['uart_cmd']
    self._regex = self._params['regex']
    self._group = int(self._params['group'])

  def _process_output(self, pre_result):
    """Helper to perform extra formatting out the output of |_Get_output|.

    Formatting is defined in the param 'formatting' and comma separated. It
    is performed in sequence. Supported formatting operations are.
    - strip: strips white-space and new-lines as the end
    - splitlines: split the output by lines and leave as list
    - splitlines_str: split the output by lines and concat as str with
      whitespace
    - int: cast |pre_result| into int for each member, if splitlines was
      previously used

    Args:
      pre_result: str, the output to format

    Returns:
      result, str, after processing from |pre_result|

    """
    if 'formatting' in self._params:
      requests = self._params['formatting'].split(',')
      for request in requests:
        if request == 'strip':
          pre_result = pre_result.strip()
        elif request == 'splitlines':
          pre_result = pre_result.splitlines()
        elif request == 'splitlines_str':
          pre_result = ' '.join(pre_result.splitlines())
        elif request == 'int':
          if isinstance(pre_result, list):
            pre_result = [int(m) for m in pre_result]
          else:
            int(pre_result)
        else:
          self._logger.debug('ec output formatting %r unknown. Ignoring.',
                             request)
    return pre_result

  def _get_safe_output(self, cmd, regex):
    """Safely retrieve the output of |cmd| from the |self._interface|.

    Args:
      cmd: command to run
      regex: regex to match.

    Returns:
      output of running |cmd| and matching with |regex| on |self._interface|

    Raises:
      ecError: if the output from the |self._uart_cmd| matched with the
               |self._regex| is None
    """
    self._limit_channel()
    result = self._issue_cmd_get_results(self._uart_cmd, [self._regex])
    self._restore_channel()
    if result is None:
      raise ec.ecError('Failed to retrieve output for %r matching regex %r' %
                       (cmd, regex))
    # Extract the requested group. This control does not support a list of regex
    # but rather just expects one regex. Therefore we access the 1st element of
    # the result (result[0]) always.
    return result[0][self._group]

  def get(self):
    """Generic get from EC console, using |self._params| for cmd and regex.

    Runs |self._uart_cmd| on |self._interface| (has to be a uart interface)
    and matches the output with |self._regex| before returning the result.

    Returns:
      result of |self._uart_cmd| after matching with |self._regex| and
      processing
    """
    result = self._get_safe_output(self._uart_cmd, self._regex)
    return self._process_output(result)
