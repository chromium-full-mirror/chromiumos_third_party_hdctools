# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Use the generated sversion.py info to provide version strings."""

import re


UNKNOWN_VALUE = "unknown"

try:
    # The sversion file might not exist if something goes wrong in the Makefile
    # This just ensures that the system does not break if for some reason
    # version information is missing.
    from servo import sversion

    vdict = sversion.VER_DICT
except ImportError:
    # This means that the version dictionary was somehow not generated.
    # This should not break things, rather make a fake dictionary that
    # indicates this issue.
    vdict = {k: UNKNOWN_VALUE for k in ["vbase", "ghash", "builder", "date", "branch"]}
    vdict["dirty"] = True


def setuptools_version():
    """Generate a version string given the vdict above."""
    # for setuptools, convert the marker into a '.dev' so that it gets converted
    # properly
    vbase = vdict["vbase"]
    if "9999" in vbase:
        # To recognize when the package is being built by cros_workon.
        return "%s.dev" % vbase
    return vbase


def extended_version():
    """More informative version string to use in command-line tools."""
    # The general format here is
    # [vbase][ghash]
    # [date]
    # [builder]
    vbase = setuptools_version()
    return "%s%s\nDate: %s\nBuilder: %s\nHash: %s\nBranch: %s" % (
        vbase,
        vdict["ghash"],
        vdict["date"],
        vdict["builder"],
        vdict["ghash"],
        vdict["branch"],
    )


def normalize_version(fwversion: str) -> str:
    """Simplify firmware version string

    Takes a full firmware version string and return out the
    major.minor.build triplet for consumption by python-packaging.

    Args:
        fwversion: A firmware version string of the form
                   "{device_name}_v{major.minor.build}±{githash}".
                   {device_name} may contain an arbitrary number of
                   underscores (notable user of that quirk:
                   servo_v4p1)

    Returns:
        string containing "v{major.minor.build}"

    """
    matches = re.findall(r"^[-0-9a-z_]+_v([0-9.]+)[-+][0-9a-f]+$", fwversion)
    if len(matches) != 1:
        raise ValueError(f"firmware version {fwversion} unsupported")
    return matches[0]
