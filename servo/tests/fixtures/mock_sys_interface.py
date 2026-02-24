# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Fixtures for mocking SysInterface."""

from unittest.mock import patch

import pytest


@pytest.fixture
def mock_sys_interface():
    """Mock the sys_interface singleton."""
    with patch("servo.utils.sys_interface.sys_interface") as mock:
        yield mock
