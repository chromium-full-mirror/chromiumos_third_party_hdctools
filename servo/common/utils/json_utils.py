# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json

from google.protobuf import json_format
from google.protobuf import struct_pb2


class ServoJSONEncoder(json.JSONEncoder):
    """JSON encoder that handles sets by converting them to lists."""

    def default(self, o):
        if isinstance(o, set):
            return list(o)
        return super().default(o)


def dumps(obj, **kwargs):
    """Shortcut for json.dumps using ServoJSONEncoder."""
    return json.dumps(obj, cls=ServoJSONEncoder, **kwargs)


def wrap_value(obj):
    """Wrap any JSON-serializable python object into a google.protobuf.Value."""
    val_pb = struct_pb2.Value()
    json_format.Parse(dumps(obj), val_pb)
    return val_pb


def ensure_int(val):
    """Handle float-represented integers from gRPC/JSON."""
    if isinstance(val, float) and val == int(val):
        return int(val)
    return val
