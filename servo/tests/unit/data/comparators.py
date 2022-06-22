# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Collection of helpers functions to check against system config."""

def is_map(config, smap):
  """Ensure that in |config| there is a map called |smap|."""
  return config.is_map(smap)

def map_key_to_val(config, smap, key, val):
  """Ensure that in |config| the |smap| has |key| mapping to |val|."""
  mparams = config.lookup_map_params(smap)
  if key not in mparams:
    return False
  return mparams[key] == val
