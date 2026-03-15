# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from google.protobuf import struct_pb2
import pytest

from servo.common.utils import json_utils


class TestServoJSONEncoder:
    def test_encode_set(self):
        data = {"myset": {1, 2, 3}}
        result = json_utils.dumps(data)
        # Sets are unordered, so we check if the list contains the elements
        assert '"myset": [' in result
        assert "1" in result
        assert "2" in result
        assert "3" in result

    def test_encode_standard_types(self):
        data = {"string": "val", "int": 5, "bool": True}
        result = json_utils.dumps(data)
        assert '"string": "val"' in result
        assert '"int": 5' in result
        assert '"bool": true' in result

    def test_encode_unsupported_type(self):
        class CustomObj:
            pass

        data = {"obj": CustomObj()}
        with pytest.raises(TypeError):
            json_utils.dumps(data)


def test_wrap_value():
    data = {"key": "value", "number": 10, "set_data": {1, 2}}
    val_pb = json_utils.wrap_value(data)
    assert isinstance(val_pb, struct_pb2.Value)
    # The dictionary should be converted into a Struct
    struct_val = val_pb.struct_value
    assert struct_val.fields["key"].string_value == "value"
    assert struct_val.fields["number"].number_value == 10.0
    # Set should have been converted to a list
    list_val = struct_val.fields["set_data"].list_value
    values = [v.number_value for v in list_val.values]
    assert 1.0 in values
    assert 2.0 in values


def test_ensure_int():
    assert json_utils.ensure_int(5.0) == 5
    assert isinstance(json_utils.ensure_int(5.0), int)

    assert json_utils.ensure_int(5.5) == 5.5
    assert isinstance(json_utils.ensure_int(5.5), float)

    assert json_utils.ensure_int("5") == "5"
    assert json_utils.ensure_int(5) == 5
