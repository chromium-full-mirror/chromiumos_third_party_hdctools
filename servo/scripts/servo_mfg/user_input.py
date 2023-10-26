# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Helper functions to get and validate user input."""

import logging
import re
import signal

from servo_mfg import color_mode as cm


class UserInputError(Exception):
    """Error class for util functions."""


# Number of attempts the user gets to provide valid input.
# After this number, we assume that something is wrong, and cancel.
INPUT_ATTEMPTS = 10

# Number of seconds the user has to provide input.
INPUT_TIMEOUT_S = 180

# Regex to validate mac address input.
# Note: the mac address regex lives here since it's universal. The regex for
# serial numbers lives inside each manager, as they change per device.
MACADDR_RE = re.compile("^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")


def data_is_valid(name, data, data_re):
    """Helper to return whether |data_re| matches |data|.

    Args:
      name: name of the data (for debugging log string)
      data: the data to validate
      data_re: the regex to validate |data| against

    Returns:
      True if |data_re| matches |data|, False otherwise
    """
    if data_re.match(data):
        return True
    logging.info(
        "Value %r for %r does not match expected regex %r.", data, name, data_re.pattern
    )
    return False


def serial_is_valid(serial, serial_re):
    """Return whether |serial| is valid.

    Args:
      serial: str, serial to check
      serial_re: re, regex to validate |serial| against

    Returns:
      True if |serial_re| matches |serial|, False otherwise
    """
    return data_is_valid("serial", serial, serial_re)


def mac_is_valid(mac):
    """Return whether |mac| is valid.

    Args:
      mac: str, mac to check

    Returns:
      True if |MACADDR_RE| matches |mac|, False otherwise
    """
    return data_is_valid("macaddr", mac, MACADDR_RE)


def prompt_for_serial(serial_re):
    """Prompt the user to provide a serial.

    Args:
      serial_re: re, regex to validate user provided serial against

    Returns:
      str, user provided serial
    """
    return _prompt_and_validate("serial", serial_re)


def prompt_for_mac():
    """Prompt the user to provide a mac number.

    Returns:
      str, user provided mac
    """
    return _prompt_and_validate("macaddr", MACADDR_RE)


def _timeout_handler(_sig, _unused):
    """Helper to log a timeout and raise the error. Installed as sig handler."""
    logging.error("Timeout waiting for input. Timeout is %ds", INPUT_TIMEOUT_S)
    raise UserInputError("Timeout on input.")


# Install a signal handler to make sure that user input
# does not go beyond the timeout specified.
signal.signal(signal.SIGALRM, _timeout_handler)


def _raw_input_timeout(prompt):
    """Perform user input query.

    Set an alarm for |INPUT_TIMEOUT_S| and wait for user to provide input before
    the alarm fires.

    Args:
      prompt: prompt to display to user

    Returns:
      user input, or None on timeout
    """
    signal.alarm(INPUT_TIMEOUT_S)
    try:
        # pylint: disable=undefined-variable
        # raw_input is standard library
        try:
            uinput = raw_input("%s: " % prompt)
        except NameError:
            # we're in python3
            uinput = input("%s: " % prompt)
        return uinput.strip()
    except UserInputError:
        # This means the timeout was hit.
        return None
    finally:
        signal.alarm(0)


def _prompt_and_validate(name, data_re=None):
    """Helper to prompt and validate.

    use |_raw_input_timeout| to do timeout'd input and use |data_re| to validate
    and retry if necessary up to |INPUT_ATTEMPTS| time to get valid input.

    Args:
      name: the data being asked from the user
      data_re: the regex to use to validate the input

    Returns:
      validated input or None (on timeout, or too many faulty attempts)
    """
    instruct_user("Please type or scan the desired %r." % name)
    attempts_left = INPUT_ATTEMPTS
    while attempts_left > 0:
        attempts_left -= 1
        # Cast here with |%r| to ensure quotes.
        data = _raw_input_timeout("%r" % name)
        logging.debug("Input %r: %r", name, data)
        if data is None:
            # This means a timeout occurred. Simply return the None to the caller.
            return None
        if (data_re is None and data) or data_is_valid(name, data, data_re):
            # Ensure that empty input does not get passed through.
            if instruct_user(
                "Registered valid input for %r: %r" % (name, data),
                enter_to_confirm=True,
            ):
                return data
            logging.info("Very well, try again.")
        else:
            logging.info("Try again!")
    logging.error(
        "Ran out of attempts to scan %r. Attempts are %d. Please start again.",
        name,
        INPUT_ATTEMPTS,
    )
    return None


# This module flag enables the user_input to system-wide turn off requiring user
# confirmation.
confirmations_enabled = True


def turn_off_user_confirmation():
    """Turn off |instruct_user| from seeking user confirmation for actions."""
    global confirmations_enabled
    logging.info("All user prompts will be automatically answered affirmatively.")
    confirmations_enabled = False


def instruct_user(message, enter_to_confirm=False):
    """Helper to instruct user and wait for confirmation.

    Args:
      message: message to display to user
      enter_to_confirm: if |True| the script will ask the user to confirm by
                        pressing enter or disagree by pressing anything else

    Returns:
      True if the user confirmed, False if they disagreed

    Note: The return value is always True if |enter_to_confirm| is False as no
          confirmation was sought.
    """
    # This is the user prompt signal.
    up = cm.red_bg(">>>")
    chunks = ["%s %s" % (up, c) for c in message.split("\n")]
    for c in chunks:
        logging.info(c)
    if confirmations_enabled and enter_to_confirm:
        result = _raw_input_timeout(
            cm.red_bg("Type only [enter] to confirm, anything else to cancel")
        )
        # Only enter will yield a '', which we want to return as True.
        return not bool(result)
    # If no confirmation was requested, then assume confirmation is given.
    return True
