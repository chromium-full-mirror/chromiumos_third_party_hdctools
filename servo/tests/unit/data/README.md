# Structure

The testing here is supposed to map to one overlay file to one test file.
The naming is `test_[overlay_name].py` skipping the .xml in the name.

For instance, `servo_micro.xml` maps to `test_servo_micro.py`

The test should test every control or map defined in the overlay, and tag it for
every underlying servo hardware it can be run with.

# Samples

Below are a few samples, and notes on how to write tests for this infrastructure

## Control testing

```
class TestServoMicro:

  # NOTE: this is testing the servo_micro config - therefore
  # none of the tests will pass in a config file, and
  # the only valid hardware is servo_micro.
  # You need not pass a config file, as the servo micro hardware will
  # pull in the servo micro config file automatically.

  @pytest.mark.parametrize('servo_hw', ['servo_micro'])
  def test_ctrl_hw1_uart1_en(self, servo_hw, sys_config_gen):
    """Test control |uart1_en| on |hw1| setups (see servo_hw param)."""
    ctrl = 'uart1_en'
    scfg = sys_config_gen(None, servo_hw)
    assert c.is_control(scfg, ctrl)
    assert c.ctrl_drv(scfg, ctrl, 'ec3po_gpio')
    assert c.ctrl_interface(scfg, ctrl, 6)
    assert c.ctrl_subtype(scfg, ctrl, 'single')
    assert c.ctrl_init(scfg, ctrl, 'on')
    # NOTE: this is a generic param helper. Effectively, use this
    # when checking for params that are very control specific,
    # but create new helpers for system params like `subtype` or
    # `interface` (as above)
    assert c.ctrl_param(scfg, ctrl, 'name', 'UART1_EN_L')

```
Notice a few things
1. first, test that the control exists
2. second, test that all configs for the control are what they should be
3. `sys_config_gen` is a fixture that comes from conftest.py - it caches some
   SystemConfig objects. Please look it up, but this is a helpful way of using
   it.
4. In this specific test, there is only one underlying hardware, so the fixture
   only has one value. However, if multiple underlying hardwares behave the same
   way, please expand the fixture and parametrize it, instead of writing
   duplicate tests. However, if an underlying hardware changes the expectation
   of the map, write a new test for that. Do not parametrize the expectation.
5. Do no perform raw checks on scfg internal structures - this will make it
   harder to maintain - instead expand the comparators.py and/or the
   system\_config.py to use those helpers


## Map testing

```
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
```

Notice a few things
1. first, test that the map exists
2. second, test that all keys are what you think they should be
3. `sys_config_gen` is a fixture that comes from conftest.py - it caches some
   SystemConfig objects. Please look it up, but this is a helpful way of using
   it.
4. In this specific test, there is only one underlying hardware, so the fixture
   only has one value. However, if multiple underlying hardwares behave the same
   way, please expand the fixture and parametrize it, instead of writing
   duplicate tests. However, if an underlying hardware changes the expectation
   of the map, write a new test for that. Do not parametrize the expectation.
5. Do no perform raw checks on scfg internal structures - this will make it
   harder to maintain - instead expand the comparators.py and/or the
   system\_config.py to use those helpers
