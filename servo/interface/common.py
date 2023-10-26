# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Common utilities for interface."""

import logging


class InterfaceError(Exception):
    """Base error class for interfaces."""


build_logger = logging.getLogger("Interface.Build")
