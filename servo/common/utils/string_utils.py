# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""String utils."""


def snake_to_camel(string):
    """
    Convert a string from snake case to camel case.
    """
    output = ""
    for s in string.split("_"):
        if output:
            output += s.capitalize()
        else:
            output = s
    return output
