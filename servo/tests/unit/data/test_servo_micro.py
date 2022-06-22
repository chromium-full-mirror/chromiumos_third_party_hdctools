# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import pytest

import comparators as c

class TestServoMicro:

  # NOTE: this is testing the servo_micro config - therefore
  # none of the tests will pass in a config file, and
  # the only valid hardware is servo_micro.
  # You need not pass a config file, as the servo micro hardware will
  # pull in the servo micro config file automatically.

  @pytest.mark.parametrize('servo_hw', ['servo_micro'])
  def test_map_servo_micro_onof_vref_sel(self, servo_hw, sys_config_gen):
    """Test the map |onof_vref_sel| on |servo_micro| hardware."""
    mapname = 'onoff_vref_sel'
    scfg = sys_config_gen(None, servo_hw)
    assert c.is_map(scfg, mapname)
    assert c.map_key_to_val(scfg, mapname, 'off', '0')
    assert c.map_key_to_val(scfg, mapname, 'pp3300', '1')
    assert c.map_key_to_val(scfg, mapname, 'pp1800', '2')
