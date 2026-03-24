# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""A simple driver to set/retrieve simple data from a cros ec interface."""

from servo.drv import ec
from servo.drv import hw_driver


# pylint: disable=invalid-name
# naming convention needed for servod driver query.
class simpleEc(ec.ec):
    """Object to access drv=simple_ec controls."""

    # This drv requires the
    # - the command to run |uart_cmd|
    # - the regex to match against |regex|
    # - the group within the regex to retrieve |group| or 0 to retrieve
    # the entire match
    REQUIRED_GET_PARAMS = ["uart_cmd", "regex", "group"]

    # This drv for setting a control requires
    # - the command template to run
    REQUIRED_SET_PARAMS = ["uart_cmd"]

    # The default regex to use for set. It simply checks whether the control
    # finished and a new line is printed. This helps servod avoid returning before
    # the control has actually finished executing on the ec console.
    SET_RE_DEFAULT = ">"

    def _drv_init(self):
        """Driver specific initializer."""
        super()._drv_init()
        self._uart_cmd = self._params["uart_cmd"]
        if self._is_get():
            # These controls are required for |get| but not for |set|.
            self._regex = self._params["regex"]
            self._group = int(self._params["group"])
        else:
            # guaranteed to be in 'set'.
            self._regex = self._params.get("regex", self.SET_RE_DEFAULT)
            self._group = int(self._params.get("group", "0"))
        # User can optionally provide a |debug_info| string to log
        # when this control fails.
        self._debug_info = self._params.get("debug_info", "")

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
        if "formatting" in self._params:
            requests = self._params["formatting"].split(",")
            for request in requests:
                if request == "strip":
                    pre_result = pre_result.strip()
                elif request == "splitlines":
                    pre_result = pre_result.splitlines()
                elif request == "splitlines_str":
                    pre_result = " ".join(pre_result.splitlines())
                elif request == "int":
                    if isinstance(pre_result, list):
                        pre_result = [int(m) for m in pre_result]
                    else:
                        pre_result = int(pre_result, 0)
                elif request == "float":
                    pre_result = float(pre_result)
                elif request == "bool":
                    pre_result = bool(pre_result)
                elif request == "negative":
                    pre_result = pre_result * -1
                elif request == "gpio":
                    pre_result = (
                        "\n" + pre_result.replace("gpioget", "").replace("\r", "")[:-1]
                    )
                elif request == "map_open":
                    pre_result = 1 if pre_result == "open" else 0
                else:
                    self._logger.debug(
                        "ec output formatting %r unknown. Ignoring.", request
                    )
        return pre_result

    def _error(self, cmd, regex, e=None):
        """Helper to raise errors in a standardized way.

        Args:
          cmd: command that was run
          regex: regex that was used
          e: error object, or string to provide extra information

        Raises:
          ec.ecError: always, with |errmsg|
        """
        errmsg = "Failed to retrieve output for %r matching regex %r" % (cmd, regex)
        if e:
            self._logger.error(e)
        if self._debug_info:
            self._logger.error(self._debug_info)
        raise ec.ecError("%s. %s" % (errmsg, e))

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
        retries = int(self._params["retries"]) if "retries" in self._params else 1
        while retries > 0:
            retries -= 1
            try:
                self._limit_channel()
                results = self._issue_cmd_get_results(cmd, [regex])
                break
            except hw_driver.HwDriverError as e:
                if retries <= 0:
                    # Any known error is coming through as a HwDriverError derivative.
                    self._error(cmd, regex, e)
                self._logger.warning(
                    "Retry retrieving output for %r matching regex %r" % (cmd, regex)
                )
            finally:
                self._restore_channel()
        # |results| should always be a list of tuples.
        # TODO(b/180764962) remove this
        if not isinstance(results[0], tuple):
            results[0] = (results[0],)
        if results is None:
            self._error(cmd, regex)
        # Extract the requested group. This control does not support a list of regex
        # but rather just expects one regex. Therefore we access the 1st element of
        # the results (results[0]) always.
        return results[0]

    def _get(self):
        """Generic get from MCU console, using |self._params| for cmd and regex.

        Runs |self._uart_cmd| on |self._interface| (has to be a uart interface)
        and matches the output with |self._regex| before returning the result.

        Returns:
          result of |self._uart_cmd| after matching with |self._regex| and
          processing
        """
        results = self._get_safe_output(self._uart_cmd, self._regex)
        # The desired output is inside the self._group member of |results|. However,
        # given how python regex works, this can be None, and we cannot marshall
        # None across the channel, so make sure to cast it into a string first.
        result = results[self._group]
        if result is None:
            self._logger.debug(
                "Requested result group returned None, casting into string."
            )
            result = str(result)
        return self._process_output(result)

    def _set(self, value):
        """Generic set method to set |self._uart_cmd| + str(|value|) to the console.

        Note: the control to send to the |self._interface| console is created
        by appending a space and the string cast of |value| to |self._uart_cmd|.

        Args:
          value: the value passed through by servod to set
        """
        # NOTE: This mechanism is limited, but effective for many use-cases.
        # Should the situation arise multiple times where a more complex control
        # generation is required e.g. string formatting so that the value is
        # in the middle of the string somewhere, please file a feature request bug.
        full_cmd = "%s %s" % (self._uart_cmd, value)
        self._logger.debug("About to issue %r", full_cmd)
        # Ignore the return type as we only want to send the |cmd|
        self._get_safe_output(full_cmd, self._regex)
