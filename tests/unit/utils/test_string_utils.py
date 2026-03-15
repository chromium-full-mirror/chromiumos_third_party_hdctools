# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from servo.common.utils import string_utils


def test_snake_to_camel():
    assert string_utils.snake_to_camel("hello_world") == "helloWorld"
    assert string_utils.snake_to_camel("hello_world_test") == "helloWorldTest"
    assert string_utils.snake_to_camel("alreadyCamel") == "alreadyCamel"
    assert string_utils.snake_to_camel("single") == "single"
    assert string_utils.snake_to_camel("_leading_underscore") == "leadingUnderscore"
    assert string_utils.snake_to_camel("trailing_underscore_") == "trailingUnderscore"
    assert string_utils.snake_to_camel("") == ""
