# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Collection of available tools in the system."""

from servo.tools import device
from servo.tools import instance
from servo.tools import logs


REGISTERED_TOOLS = [device.Device, instance.Instance, logs.Logs]
