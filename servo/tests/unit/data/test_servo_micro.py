# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import comparators as c
import pytest


class TestServoMicro:
    # NOTE: this is testing the servo_micro config - therefore
    # none of the tests will pass in a config file, and
    # the only valid hardware is servo_micro.
    # You need not pass a config file, as the servo micro hardware will
    # pull in the servo micro config file automatically.

    @pytest.mark.parametrize("servo_hw", ["servo_micro"])
    def test_map_hw1_onoff_vref_sel(self, servo_hw, sys_config_gen):
        """Test map |onoff_vref_sel| on |hw1| setups (see servo_hw param)."""
        mapname = "onoff_vref_sel"
        scfg = sys_config_gen(None, servo_hw)
        assert c.is_map(scfg, mapname)
        assert c.map_key_to_val(scfg, mapname, "off", "0")
        assert c.map_key_to_val(scfg, mapname, "pp3300", "1")
        assert c.map_key_to_val(scfg, mapname, "pp1800", "2")

    @pytest.mark.parametrize("servo_hw", ["servo_micro"])
    def test_ctrl_hw1_uart1_en(self, servo_hw, sys_config_gen):
        """Test control |uart1_en| on |hw1| setups (see servo_hw param)."""
        ctrl = "uart1_en"
        scfg = sys_config_gen(None, servo_hw)
        assert c.is_control(scfg, ctrl)
        assert c.ctrl_drv(scfg, ctrl, "ec3po_gpio")
        assert c.ctrl_interface(scfg, ctrl, 6)
        assert c.ctrl_subtype(scfg, ctrl, "single")
        assert c.ctrl_init(scfg, ctrl, "on")
        # NOTE: this is a generic param helper. Effectively, use this
        # when checking for params that are very control specific,
        # but create new helpers for system params like `subtype` or
        # `interface` (as above)
        assert c.ctrl_param(scfg, ctrl, "name", "UART1_EN_L")
