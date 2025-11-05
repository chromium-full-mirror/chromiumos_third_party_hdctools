# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Manage color formatting for console output."""

# By default, this package is inactive. The user has to request it.
ACTIVE = False


def activate():
    """Activate color mode to produce colorful output."""
    global ACTIVE
    ACTIVE = True


BASE = "\033"
RST = BASE + "[0m"
RED = BASE + "[31m"
GREEN = BASE + "[32m"
YELLOW = BASE + "[33m"
# Technically cyan
BLUE = BASE + "[36m"
MAGENTA = BASE + "[35m"


RED_BG = BASE + "[41;1m"
GREEN_BG = BASE + "[42;1m"


def _fmt(msg, mode):
    """Return |msg| wrapped by |mode| if |ACTIVE| otherwise just |msg|."""
    if ACTIVE:
        # msg might end in '\n'. This is usually used to split the string
        # later, and thus the '\n' should not be part of the formatting (otherwise
        # it will be split out.
        suffix = ""
        if msg[-1] == "\n":
            suffix = msg[-1]
            msg = msg[:-1]
        msg = mode + msg + RST + suffix
    return msg


def red(msg):
    """Return |msg| in red."""
    return _fmt(msg, RED)


def green(msg):
    """Return |msg| in green."""
    return _fmt(msg, GREEN)


def yellow(msg):
    """Return |msg| in yellow."""
    return _fmt(msg, YELLOW)


def magenta(msg):
    """Return |msg| in magenta."""
    return _fmt(msg, MAGENTA)


def blue(msg):
    """Return |msg| in blue."""
    return _fmt(msg, BLUE)


def red_bg(msg):
    """Return |msg| in red_bg."""
    return _fmt(msg, RED_BG)


def green_bg(msg):
    """Return |msg| in green_bg."""
    return _fmt(msg, GREEN_BG)
