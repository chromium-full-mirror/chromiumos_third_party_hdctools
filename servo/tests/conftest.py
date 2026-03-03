# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# These imports are necessary for pytest dependency injection.
# pylint: disable=unused-import

import sys
import unittest.mock

import pytest

from servo.core import recovery
from servo.tests.fixtures.mock_pyusb import mock_endpoint
from servo.tests.fixtures.mock_pyusb import mock_interface
from servo.tests.fixtures.mock_pyusb import mock_pyusb
from servo.tests.fixtures.mock_servo_host import (
    mock_host_with_4p1_servo_and_c2d2,
)
from servo.tests.fixtures.mock_servo_host import (
    mock_host_with_4p1_servo_and_c2d2_and_ccd,
)
from servo.tests.fixtures.mock_servo_host import (
    mock_host_with_4p1_servo_and_ccd,
)
from servo.tests.fixtures.mock_servo_host import (
    mock_host_with_4p1_servo_and_servo_micro,
)
from servo.tests.fixtures.mock_servo_host import (
    mock_host_with_4p1_servo_and_servo_micro_and_ccd,
)
from servo.tests.fixtures.mock_servo_host import (
    mock_host_with_4p1_servo_and_servo_micro_and_gsc_ccd,
)
from servo.tests.fixtures.mock_servo_host import (
    mock_host_with_4p1_servo_and_servo_micro_and_gsc_ccd_nt,
)
from servo.tests.fixtures.mock_servo_host import mock_servo_host
from servo.tests.fixtures.mock_sys_interface import mock_sys_interface
from servo.tests.fixtures.mock_usb_devices import mock_c2d2_configuration
from servo.tests.fixtures.mock_usb_devices import mock_c2d2_usb_device
from servo.tests.fixtures.mock_usb_devices import mock_ccd_gsc_configuration
from servo.tests.fixtures.mock_usb_devices import mock_ccd_gsc_nt_configuration
from servo.tests.fixtures.mock_usb_devices import mock_ccd_gsc_nt_usb_device
from servo.tests.fixtures.mock_usb_devices import mock_ccd_gsc_usb_device
from servo.tests.fixtures.mock_usb_devices import mock_cr50_configuration
from servo.tests.fixtures.mock_usb_devices import mock_cr50_usb_device
from servo.tests.fixtures.mock_usb_devices import mock_servo_micro_configuration
from servo.tests.fixtures.mock_usb_devices import mock_servo_micro_usb_device
from servo.tests.fixtures.mock_usb_devices import mock_usb_device
from servo.tests.fixtures.mock_usb_devices import mock_v4p1_configuration
from servo.tests.fixtures.mock_usb_devices import mock_v4p1_usb_device
from servo.utils import diagnose


def pytest_runtest_teardown(item, nextitem):
    """Ensure that critical module functions were not left as mocks."""
    del nextitem  # Unused
    for module, func_name in [
        (diagnose, "diagnose_ccd"),
        (recovery, "is_recovery_active"),
    ]:
        obj = getattr(module, func_name)
        if isinstance(obj, unittest.mock.NonCallableMock):
            pytest.fail(
                f"Leak detected: {module.__name__}.{func_name} is still a mock after "
                f"test {item.nodeid}. Ensure you use unittest.mock.patch or "
                "properly restore it in teardown."
            )
