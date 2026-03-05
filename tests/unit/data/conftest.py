# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import pytest

from servo.common import servo_dev_templates as templates
from servo.common.config import system_config


class SystemConfigTestError(Exception):
    """Error to raise during system config building."""


@pytest.fixture(scope="class")
def sys_config_gen():
    """System config factory generator.

    The |known| dict is used to cache the SystemConfig objects to make
    sure they are not unnecessarily recreated.
    """
    known = {}

    def make_sys_config(cfile, setup):
        """SystemConfig generation function.

        Args:
          cfile: str, the servod data config file to use
          setup: str, the servo hardware setup underneath
        """
        tag = (cfile, setup)
        if tag not in known:
            known[tag] = build_system_config(cfile, setup)
        return known[tag]

    yield make_sys_config


# List of setups that are supported.
SUPPORTED_SETUPS = {"servo_micro"}


def build_system_config(cfile, setup):
    """Helper to make a SystemConfig object.

    The testing tests at most *one* cfile, against an underlying hardware setup.
    Depending on the setup, the correct overlays for the hardware setup are
    pulled into the SystemConfig.

    Since this is meant for unit testing, this functionality should be enough.
    Should you find yourself in the position of needing to test how more than
    one configuration file works with underlying hardware, create one
    configuration file that includes all the ones you need to test, and write
    a test against that file.

    Args:
      cfile: str, the servod data config file to use
      setup: str, the servo hardware setup underneath

    Returns:
      syscfg: SystemConfig instance for the |setup| with |cfile|
    """
    # NOTE(coconutruben): while servod is not modular,
    # we have all these cases. once it is modular, this
    # needs to be simplified to making one SystemConfig object
    # per cfile/setup combo, and then returning a collection
    # of them.
    files = []
    if setup is not None:
        if setup not in SUPPORTED_SETUPS:
            raise SystemConfigTestError("Unsupported setup %r" % setup)
        sdev_template = templates.get_template_class_by_name(setup)
        files.append(sdev_template.DEFAULT_CONFIG)
    if cfile is not None:
        files.append(cfile)
    if not files:
        raise SystemConfigTestError("Cannot test an empty config.")
    scfg = system_config.SystemConfig()
    for f in files:
        scfg.add_cfg_file(setup, f)
    return scfg
