# Copyright 2012 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import ast
import contextlib
import errno
import os
import re
import time

import pexpect
from pexpect import fdpexpect

import servo.common.terminal_freezer
from servo.drv import hw_driver
from servo.utils.sys_interface import sys_interface


DEFAULT_UART_TIMEOUT = 3  # 3 seconds is plenty even for slow platforms
FLUSH_UART_TIMEOUT = 1


class PtyError(hw_driver.HwDriverError):
    """Exception class for pty errors."""


UART_PARAMS = {
    "uart_cmd": None,
    "uart_flush": True,
    "uart_multicmd": None,
    "uart_regexp": None,
    "uart_timeout": DEFAULT_UART_TIMEOUT,
    "has_chan": True,
}


class ptyDriverError(hw_driver.HwDriverError):
    """Error class for ptyDriver."""


class PtyDriver(hw_driver.HwDriver):
    """."""

    # The default regex to use for set. It simply checks whether the control
    # finished and a new line is printed. This helps servod avoid returning before
    # the control has actually finished executing on the console.
    SET_RE_DEFAULT = ">"

    def _drv_init(self):
        """Driver specific initializer."""
        super()._drv_init()
        self._child = None
        self._fd = None
        self._cmd_iface = False
        self._refresh_pty_path()
        # Store the uart state in an interface variable. Copy uart params, so the
        # uart state dict is a different object for each interface. We don't want
        # setting anything for the ec uart to affect the ap uart state.
        if not hasattr(self._interface, "_uart_state"):
            self._interface._uart_state = UART_PARAMS.copy()

        # Update the interface state if 'has_chan' was passed as a parameter
        # to the driver configuring the PTY (e.g. ec3po_gsc_uart).
        if "has_chan" in self._params:
            self._interface._uart_state["has_chan"] = (
                self._params.get("has_chan").lower() != "no"
            )

    def _refresh_pty_path(self):
        """Refresh the PTY path from the interface."""
        try:
            # We'll probe for a control PTY if this is an ec3po interface.
            self._pty_path = self._interface.get_control_pty()
            self._cmd_iface = True
        except AttributeError:
            if hasattr(self._interface, "get_pty"):
                self._pty_path = self._interface.get_pty()
            else:
                self._logger.warning(
                    "Interface %s has no get_pty method. Is it connected?",
                    self._interface,
                )
                self._pty_path = ""
        except Exception:
            self._pty_path = self._interface.get_pty()

    @contextlib.contextmanager
    def _open(self):
        """Connect to serial device and create pexpect interface.

        Note that this should be called with the 'with-syntax' since it will handle
        freezing and thawing any other terminals that are using this PTY as well as
        closing the connection when finished.
        """
        if not self._pty_path:
            self._refresh_pty_path()

        if not self._pty_path:
            raise ptyDriverError(
                "Cannot open PTY: No PTY path available for this interface."
            )

        max_tries = 3
        for i in range(max_tries):
            try:
                if self._cmd_iface:
                    self._interface.get_command_lock()
                    try:
                        self._fd = sys_interface.open(
                            self._pty_path, os.O_RDWR | os.O_NONBLOCK
                        )
                        self._child = fdpexpect.fdspawn(self._fd, use_poll=True)
                        # pexpect defaults to a 100ms delay before sending characters, to
                        # work around race conditions in ssh. We don't need this feature
                        # so we'll change delaybeforesend from 0.1 to 0.001
                        # to speed things up.
                        self._child.delaybeforesend = 0.001
                        yield
                        return
                    finally:
                        if self._fd is not None:
                            self._close()
                        self._interface.release_command_lock()
                else:
                    # Freeze any terminals that are using this PTY, otherwise when we check
                    # for the regex matches, it will fail with a 'resource temporarily
                    # unavailable' error.
                    with servo.common.terminal_freezer.TerminalFreezer(self._pty_path):
                        self._fd = sys_interface.open(
                            self._pty_path, os.O_RDWR | os.O_NONBLOCK
                        )
                        try:
                            self._child = fdpexpect.fdspawn(self._fd, use_poll=True)
                            # pexpect defaults to a 100ms delay before sending characters, to
                            # work around race conditions in ssh. We don't need this feature
                            # so we'll change delaybeforesend from 0.1 to 0.001
                            # to speed things up.
                            self._child.delaybeforesend = 0.001
                            yield
                            return
                        finally:
                            if self._fd is not None:
                                self._close()
            except (FileNotFoundError, OSError) as e:
                if i == max_tries - 1:
                    raise
                self._logger.warning(
                    "Failed to open PTY %s: %s. Refreshing and retrying (%d/%d)...",
                    self._pty_path,
                    e,
                    i + 1,
                    max_tries,
                )
                time.sleep(1.0)
                self._refresh_pty_path()

    def _close(self):
        """Close serial device connection."""
        sys_interface.close(self._fd)
        self._fd = None
        self._child = None

    def _flush(self):
        """Flush device output to prevent previous messages interfering."""
        if self._child.sendline("") != 1:
            raise PtyError("Failed to send newline.")
        # Have a maximum timeout for the flush operation. We should have cleared
        # all data from the buffer, but if data is regularly being generated, we
        # can't guarantee it will ever stop.
        flush_end_time = time.time() + FLUSH_UART_TIMEOUT
        while time.time() <= flush_end_time:
            try:
                self._child.expect(r".+", timeout=0.01)
            except (pexpect.TIMEOUT, pexpect.EOF):
                break
            except OSError as e:
                # EAGAIN indicates no data available, maybe we didn't wait long enough
                if e.errno != errno.EAGAIN:
                    raise
                self._logger.debug("pty read returned EAGAIN")
                break

    def _get(self):
        """Generic get from MCU console.
         Otherwise, use |self._params| for cmd and regex. Runs |self._uart_cmd|
         on |self._interface| (has to be a uart interface) and matches the output
         with |self._regex| before returning the result.

        Returns:
          result of |self._uart_cmd| after matching with |self._regex| and
          processing
        """
        if "uart_cmd" in self._params:
            if "regex" not in self._params:
                raise PtyError("Required param 'regex' not in params")
            if "group" not in self._params:
                raise PtyError("Required param 'group' not in params")
            self._uart_cmd = self._params["uart_cmd"]
            self._regex = self._params["regex"]
            self._group = int(self._params["group"])
            results = self._issue_cmd_get_results(self._uart_cmd, [self._regex])
            # |results| should always be a list of tuples.
            # TODO(b/180764962) remove this
            if not isinstance(results[0], tuple):
                results[0] = (results[0],)
            # The desired output is inside the self._group member of |results|. However,
            # given how python regex works, this can be None, and we cannot marshall
            # None across the channel, so make sure to cast it into a string first.
            result = results[0][self._group]
            if result is None:
                self._logger.debug(
                    "Requested result group returned None, casting into string."
                )
                result = str(result)
            return result
        raise NotImplementedError("Get method should be implemented in subclass.")

    def _set(self, value):
        """Generic set method.

        Use |self._params| for cmd and regex. Set |self._uart_cmd| + str(|value|)
        with |self._regex| on |self._interface| (has to be a uart interface).
        Note: the control to send to the |self._interface| console is created
        by appending a space and the string cast of |value| to |self._uart_cmd|.

        Args:
          value: the value passed through by servod to set
        """
        # NOTE: This mechanism is limited, but effective for many use-cases.
        # Should the situation arise multiple times where a more complex control
        # generation is required e.g. string formatting so that the value is
        # in the middle of the string somewhere, please file a feature request bug.
        if "uart_cmd" in self._params:
            self._uart_cmd = self._params["uart_cmd"]
            self._regex = self._params.get("regex", self.SET_RE_DEFAULT)
            self._group = int(self._params.get("group", "0"))
            full_cmd = "%s %s" % (self._uart_cmd, value)
            self._logger.debug("About to issue %r", full_cmd)
            # Ignore the return type as we only want to send the |cmd|
            self._issue_cmd_get_results(full_cmd, [self._regex])
            return None
        raise NotImplementedError("Set is not implemented.")

    def _make_xml_friendly(self, result, error=True):
        """
        Args:
          result: result output from regex match. Either None, or tuple, or a single
                  member

        Returns:
          tuple, same tuple as |result| but with all characters < 31 and > 127
          removed (other than tab, newline, and carriage return)
        """
        if result is None:
            return None

        # TODO(coconutruben): the code to retrieve the regex has a bug in that
        # |result| can be a string, even though it should be a one member tuple.
        # This is a bigger thing to refactor, and so I'm leaving the TODO here for
        # now to tackle that once we have the time to do so. The implications is
        # that we simply here convert into a tuple the string first so that it
        # can use the same parsing logic, before splitting it out again for proper
        # return types.
        # Check against tuple instead of string, as this
        # has to work on py2 and py3
        return_as_string = not isinstance(result, tuple)
        if return_as_string:
            # Turn it into a tuple, so that the processing code below can run without
            # special casing.
            result = (result,)

        output = []
        for member in result:
            if member is None:
                # An optional match group might be None in the middle of other match
                # groups.
                output.append(member)
            else:
                # Now, we want to make sure that each character can go through XMLRPC.
                # To do this we 1. exempt \t, \r, and \n per spec, and 2. check
                # the rest for having a numerical value between 31 and and 127.
                # This is because none of our MCU send meaningful non-ascii range data.
                # NOTE: should an MCU start sending non-ascii range data, this needs
                # to be modified accordingly
                # NOTE: the code below guards according to the the xml and xmlrpc
                # (python) spec. Should this still cause issues, consider replacing the
                # numerical checks with a check against
                # xml.parsers.expat.ParserCreate().Parse()
                # While this might be marginally more resource intensive, it will be
                # both safer and more permissive as only characters that genuinely
                # cannot be sent will be stripped.
                member = member.decode(encoding="utf-8", errors="replace")
                clean = []
                for c in member:
                    if ord(c) > 31 and ord(c) < 128:
                        clean.append(c)
                    elif c in ("\n", "\t", "\r"):
                        clean.append(c)
                    else:
                        # Any non-ascii probably shouldn't be there. But we don't want to
                        # hide this. So print the repr of it.
                        # NOTE: you might be tempted to unify this with the above. Do not.
                        # This is designed to allow for easy modification of what to do with
                        # 'unexpected' characters.
                        clean.append(repr(c))
                output.append("".join(clean))

        # If originally the output is only an iterable because of |return_as_string|
        # then convert back and return the 0th member.
        # The convention is to have each result be a tuple (as it would come out
        # of re.match()). Cast list to a tuple.
        return output[0] if return_as_string else tuple(output)

    def _send(self, cmds, rate=0.01, flush=True):
        """Send command to EC or AP.

        This function always flushes serial device before sending, and is used as
        a wrapper function to make sure the channel is always flushed before
        sending commands.

        Args:
          cmds:   The commands to send to the device, either a list or a string.
          rate:   The rate in seconds at which to send the cmds.
                  Real rate will be max(0.01, rate)
          flush:  Flag to decide to flush console (send newline) before cmd.

        Raises:
          PtyError: Raised when writing to the device fails.
        """
        if flush:
            self._flush()
        if not isinstance(cmds, list):
            cmds = [cmds]
        for cmd in cmds:
            if self._child.sendline(cmd) != len(cmd) + 1:
                raise PtyError("Failed to send command.")
            # Multiple commands sent together choke the console queue.
            time.sleep(max(rate, 0.01))

    def _issue_cmd(self, cmds):
        """Send command to the device and do not wait for response.

        Args:
          cmds: The commands to send to the device, either a list or a string.
        """
        self._issue_cmd_get_results(cmds, [])

    def _issue_cmd_get_results(
        self, cmds, regex_list, flush=None, timeout=DEFAULT_UART_TIMEOUT
    ):
        r"""Send command to the device and wait for response.

        This function waits for response message matching a regular
        expressions.

        Args:
          cmds: The commands issued, either a list or a string.
          regex_list: List of Regular expressions used to match response message.
            Note1, list must be ordered.
            Note2, empty list sends and returns.
          flush:  Flag to decide to flush console (send newline) before cmd. Use
                  the uart setting if flush isn't given.
          timeout: Timeout value in second.

        Returns:
          List of tuples, each of which contains the entire matched string and
          all the subgroups of the match. None if not matched.
          For example:
            response of the given command:
              High temp: 37.2
              Low temp: 36.4
            regex_list:
              ['High temp: (\d+)\.(\d+)', 'Low temp: (\d+)\.(\d+)']
            returns:
              [('High temp: 37.2', '37', '2'), ('Low temp: 36.4', '36', '4')]

        Raises:
          PtyError: If timed out waiting for a response
        """
        result_list = []
        flush = flush if flush is not None else self._Get_uart_flush()

        with self._open():
            # If there is no command interface, make sure console capture isn't active
            # while trying to read command output. If it was it might read the output
            # the command expects and then the command would timeout.
            if not self._cmd_iface:
                self._interface.pause_capture()
            try:
                self._send(cmds, flush=flush)
                self._logger.debug("Sent cmds: %s" % cmds)
                if regex_list:
                    for regex in regex_list:
                        self._child.expect(regex, timeout)
                        match = self._child.match
                        lastindex = match.lastindex if match and match.lastindex else 0
                        # Create a tuple which contains the entire matched string and all
                        # the subgroups of the match.
                        result = match.group(*range(lastindex + 1)) if match else None
                        result = self._make_xml_friendly(result)
                        result_list.append(result)
                        self._logger.debug("Result: %s" % str(result))
            except pexpect.TIMEOUT:
                self._logger.debug("Before: ^%s^", self._child.before)
                self._logger.debug("After: ^%s^", self._child.after)
                if self._child.before:
                    # TODO(crbug.com/1043408): this needs more granular error detection
                    # to distinguish whether the console is read-only, or if the control
                    # itself had an error on the EC console.
                    output = self._child.before
                    # Reformat output a bit so that the logs don't get messed up.
                    # Specifically
                    # - remove \r
                    # - place newlines with a comma and a space
                    output = output.replace(b"\n", b", ").replace(b"\r", b"")
                    # ASCIIfy the characters in the string so that the server does not
                    # struggle marshaling the data across.
                    output = self._make_xml_friendly(output, error=False)
                    # Print it here again to see what garbage was in the output if any.
                    self._logger.debug("Before (cleaned): ^%s^", output)
                    msg = "Timeout waiting for response. There was output: %s" % output
                else:
                    msg = "No data was sent from the pty."
                if hasattr(self._interface, "_source"):
                    msg = "%s: %s" % (self._interface._source, msg)
                raise PtyError(msg)
            finally:
                # Reenable capturing the console output
                self._interface.resume_capture()
        return result_list

    def _issue_cmd_get_multi_results(
        self, cmd, regex, flush=None, timeout=DEFAULT_UART_TIMEOUT
    ):
        """Send command to the device and wait for multiple response.

        This function waits for arbitrary number of response message
        matching a regular expression.

        Args:
          cmd: The command issued.
          regex: Regular expression used to match response message.

        Returns:
          List of tuples, each of which contains the entire matched string and
          all the subgroups of the match. None if not matched.
        """
        result_list = []
        with self._open():
            self._send(cmd, flush=flush)
            self._logger.debug("Sending cmd: %s" % cmd)
            if regex:
                while True:
                    try:
                        self._child.expect(regex, timeout)
                        match = self._child.match
                        lastindex = match.lastindex if match and match.lastindex else 0
                        # Create a tuple which contains the entire matched string and all
                        # the subgroups of the match.
                        result = match.group(*range(lastindex + 1)) if match else None
                        result = self._make_xml_friendly(result)
                        result_list.append(result)
                        self._logger.debug("Got result: %s" % str(result))
                    except pexpect.TIMEOUT:
                        break
        return result_list

    def _Set_uart_flush(self, value):
        """Set the flag to enable flushing before sending a command.

        Args:
          value: 0=off, 1=on.
        """
        self._interface._uart_state["uart_flush"] = bool(value)

    def _Get_uart_flush(self):
        """Get the flag if enabling flush before sending a command.

        Returns:
          1 if enable; otherwise 0.
        """
        return 1 if self._interface._uart_state["uart_flush"] else 0

    def _Set_uart_timeout(self, timeout):
        """Set timeout value for waiting for the device response.

        Args:
          timeout: Timeout value in second.
        """
        self._interface._uart_state["uart_timeout"] = timeout

    def _Get_uart_timeout(self):
        """Get timeout value for waiting for the device response.

        Returns:
          Timeout value in second.
        """
        return self._interface._uart_state["uart_timeout"]

    def _Set_uart_regexp(self, regexp):
        r"""Set the list of regular expressions which matches the command response.

        Example usage:
        dut-control cr50_uart_regexp:'[r"Chip:\s+(\S+)\s"]'
        dut-control cr50_uart_cmd:'version'
        dut-control cr50_uart_cmd

        Args:
          regexp: A string which contains a list of regular expressions. It can be None.
        """
        err_msg = (
            "%s is not a string that contains a list of regular expressions."
            % str(regexp)
        )
        sample_usage = (
            r'\nExample valid input: \'[r"Chip:\s+(\S+)\s", r"Board:\s+(\S+)\s"]\''
        )
        if not isinstance(regexp, str):
            raise PtyError(err_msg + sample_usage)

        regex_list = ast.literal_eval(regexp)
        # If regex_list is not None, do type check
        if regex_list is not None:
            if not isinstance(regex_list, list):
                raise PtyError(err_msg + sample_usage)
            for regex in regex_list:
                try:
                    re.compile(regex)
                except:
                    raise PtyError(
                        err_msg + "\n%s is not a valid regex." % regex + sample_usage
                    )
        self._interface._uart_state["uart_regexp"] = regex_list

    def _Get_uart_regexp(self):
        """Get the list of regular expressions which matches the command response.

        Returns:
          A string which contains a list of regular expressions.
        """
        return str(self._interface._uart_state["uart_regexp"])

    def _Set_uart_cmd(self, cmd):
        """Set the UART command and send it to the device.

        If ec_uart_regexp is 'None', the command is just sent and it doesn't care
        about its response.

        If ec_uart_regexp is not 'None', the command is send and its response,
        which matches the regular expression of ec_uart_regexp, will be kept.
        Use its getter to obtain this result. If no match after ec_uart_timeout
        seconds, a timeout error will be raised.

        Args:
          cmd: A string of UART command.
        """
        if self._interface._uart_state["uart_regexp"]:
            self._interface._uart_state["uart_cmd"] = self._issue_cmd_get_results(
                cmd,
                self._interface._uart_state["uart_regexp"],
                self._interface._uart_state["uart_flush"],
                self._interface._uart_state["uart_timeout"],
            )
        else:
            self._interface._uart_state["uart_cmd"] = None
            self._issue_cmd(cmd)

    def _Set_uart_multicmd(self, cmds):
        """Set multiple UART commands and send them to the device.

        Note that ec_uart_regexp is not supported to match the results.

        Args:
          cmds: A semicolon-separated string of UART commands.
        """
        self._issue_cmd(cmds.split(";"))

    def _Get_uart_cmd(self):
        """Get the result of the latest UART command.

        Returns:
          A string which contains a list of tuples, each of which contains the
          entire matched string and all the subgroups of the match. 'None' if
          the ec_uart_regexp is 'None'.
        """
        return str(self._interface._uart_state["uart_cmd"])

    def _Set_uart_capture(self, cmd):
        """Set UART capture mode (on or off).

        Once capture is enabled, UART output could be collected periodically by
        invoking _Get_uart_stream() below.

        Args:
          cmd: an int, 1 of on, 0 for off
        """
        if hasattr(self._interface, "set_capture_active"):
            self._interface.set_capture_active(cmd)
        else:
            self._logger.warning("Interface %s does not support UART capture.",
                                 self._interface)

    def _Get_uart_capture(self):
        """Get the UART capture mode (on or off)."""
        if hasattr(self._interface, "get_capture_active"):
            return self._interface.get_capture_active()
        return 0

    def _Get_uart_stream(self):
        """Get uart stream generated since last time."""
        if hasattr(self._interface, "get_stream"):
            return self._interface.get_stream()
        return ""
