# Copyright 2023 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import os
import pathlib

from servo.common.config.system_config import SystemConfig
from servo.data.config.servo_file_discover import get_default_config_by_vid_pid


_scfg_dict = {}


def get_system_config(pid, vid, serial):
    """
    init system config controls from data xml files

    Args:
        pid (string): Product ID
        vid (string): Vendor ID

    return:
        SystemConfig object
    """
    sys_key = "{}_{}_{}".format(vid, pid, serial)
    if sys_key in _scfg_dict:
        return _scfg_dict[sys_key]
    else:
        # Get the default configuration file path based on VID and PID.
        file_path = get_default_config_by_vid_pid(vid=vid, pid=pid)

        # Create an empty SystemConfig object.
        _scfg = SystemConfig()

        # Add the configuration file to the SystemConfig object.
        _scfg.add_cfg_file(
            "", os.path.join(pathlib.Path(__file__).parent.parent.resolve(), file_path)
        )

        # Return the SystemConfig object with the configuration file added.
        _scfg_dict[sys_key] = _scfg
        return _scfg_dict[sys_key]
