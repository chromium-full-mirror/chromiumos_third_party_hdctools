# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# These imports are necessary for pytest dependency injection.
# pylint: disable=unused-import

import sys
import unittest.mock

import pytest

from servo.core import recovery
from servo.utils import diagnose
from tests.fixtures.mock_pyusb import mock_endpoint
from tests.fixtures.mock_pyusb import mock_interface
from tests.fixtures.mock_pyusb import mock_pyusb
from tests.fixtures.mock_servo_host import (
    mock_host_with_4p1_servo_and_c2d2_and_ccd,
)
from tests.fixtures.mock_servo_host import (
    mock_host_with_4p1_servo_and_servo_micro,
)
from tests.fixtures.mock_servo_host import (
    mock_host_with_4p1_servo_and_servo_micro_and_ccd,
)
from tests.fixtures.mock_servo_host import (
    mock_host_with_4p1_servo_and_servo_micro_and_gsc_ccd,
)
from tests.fixtures.mock_servo_host import (
    mock_host_with_4p1_servo_and_servo_micro_and_gsc_ccd_nt,
)
from tests.fixtures.mock_servo_host import mock_host_with_4p1_servo_and_c2d2
from tests.fixtures.mock_servo_host import mock_host_with_4p1_servo_and_ccd
from tests.fixtures.mock_servo_host import mock_servo_host
from tests.fixtures.mock_sys_interface import mock_sys_interface
from tests.fixtures.mock_usb_devices import mock_c2d2_configuration
from tests.fixtures.mock_usb_devices import mock_c2d2_usb_device
from tests.fixtures.mock_usb_devices import mock_ccd_gsc_configuration
from tests.fixtures.mock_usb_devices import mock_ccd_gsc_nt_configuration
from tests.fixtures.mock_usb_devices import mock_ccd_gsc_nt_usb_device
from tests.fixtures.mock_usb_devices import mock_ccd_gsc_usb_device
from tests.fixtures.mock_usb_devices import mock_cr50_configuration
from tests.fixtures.mock_usb_devices import mock_cr50_usb_device
from tests.fixtures.mock_usb_devices import mock_servo_micro_configuration
from tests.fixtures.mock_usb_devices import mock_servo_micro_usb_device
from tests.fixtures.mock_usb_devices import mock_usb_device
from tests.fixtures.mock_usb_devices import mock_v4p1_configuration
from tests.fixtures.mock_usb_devices import mock_v4p1_usb_device


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
