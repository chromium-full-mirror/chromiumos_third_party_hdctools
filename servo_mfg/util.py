# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Helper functions to find required files on the system."""

import os


class UtilError(Exception):
    """Error class for util functions."""


BIN_DIR = "binfiles"


def get_bindir():
    """Get the directory with the mfg binary files.

    Returns:
      |BIN_DIR| full path
    """
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), BIN_DIR)


def find_binfile(binfile):
    """Find the full path for |binfile| if available.

    Args:
      binfile: name of the binfile to find

    Returns:
      full path to |binfile| if found in |BIN_DIR| or 'False' if not found
    """
    path = os.path.join(get_bindir(), binfile)
    return not os.path.exists(path) or path


def validate_exec_available(binary_name):
    """Validate whether |binary_name| exists as a binary on the system.

    Args:
      binary_name: name of binary to check

    Returns:
      True if |binary_name| is an executable binary on the system False otherwise
    """
    # TODO(py3): replace with shutil.which
    return any(
        os.access(os.path.join(path, binary_name), os.X_OK)
        for path in os.environ["PATH"].split(os.pathsep)
    )
