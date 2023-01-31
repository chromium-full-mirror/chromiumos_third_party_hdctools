# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import unittest
import unittest.mock

from servo import recovery
from servo import servo_dev
from servo import servo_dev_templates
from servo import servo_server
from servo.utils import diagnose

class TestServod(unittest.TestCase):
  """Test Servod."""

  def test_add_device(self):
    """Test add_device()."""
    servod = servo_server.Servod()
    servod.add_serial_number = unittest.mock.MagicMock()
    dev = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    dev.get_id = unittest.mock.MagicMock(return_value="id")
    dev.add_prefix = unittest.mock.MagicMock()
    dev._serial = "serial"

    servod.add_device(dev, "main")

    self.assertEqual(servod._unique_devices["id"], dev)
    self.assertEqual(servod._devices["main"], dev)
    self.assertEqual(servod._devices[""], dev)
    servod.add_serial_number.assert_any_call("main", "serial")
    servod.add_serial_number.assert_any_call("", "serial")

  def test_add_device_error(self):
    """Test add_device()."""
    servod = servo_server.Servod()
    dev = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    dev2 = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    servod._devices["main"] = dev

    with self.assertRaisesRegex(servo_server.ServodError,
      'ServoDevice prefix main alredy represents device'):
      servod.add_device(dev2, "main")

  def test_add_device_duplicate_device(self):
    """Test add_device()."""
    servod = servo_server.Servod()
    servod._logger.debug = unittest.mock.MagicMock()
    dev = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    servod._devices["main"] = dev

    servod.add_device(dev, "main")

    servod._logger.debug.assert_any_call('ServoDevice prefix %s is already added as %s.',
      'main', dev)

  def test_reinitialize(self):
    """Test reinitialize()."""
    servod = servo_server.Servod()
    dev = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    dev2 = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    dev.reinitialize = unittest.mock.MagicMock()
    dev2.reinitialize = unittest.mock.MagicMock()
    servod._unique_devices = {"dev" : dev, "dev2" : dev2}

    servod.reinitialize()

    dev.reinitialize.assert_called_once()
    dev2.reinitialize.assert_called_once()

  def test_close(self):
    """Test close()."""
    servod = servo_server.Servod()
    dev = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    dev2 = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    dev.close = unittest.mock.MagicMock()
    dev2.close = unittest.mock.MagicMock()
    servod._unique_devices = {"dev" : dev, "dev2" : dev2}

    servod.close()

    dev.close.assert_called_once()
    dev2.close.assert_called_once()

  def test_get_devices(self):
    """Test get_devices()."""
    servod = servo_server.Servod()
    dev = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    dev2 = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    servod._unique_devices = {"dev" : dev, "dev2" : dev2}

    self.assertEqual(servod.get_devices(), [dev, dev2])

  def test_get_control_prefix_and_name(self):
    """Test _get_control_prefix_and_name()."""
    self.assertEqual(servo_server.Servod._get_control_prefix_and_name('cold_reset'), ('', 'cold_reset'))
    self.assertEqual(servo_server.Servod._get_control_prefix_and_name('ccd_cr50.cold_reset'), ('ccd_cr50', 'cold_reset'))
    with self.assertRaisesRegex(servo_server.ServodError, "Name 'ccd.cr50.cold_reset' is malformed: at most one '.' is allowed."):
      servo_server.Servod._get_control_prefix_and_name('ccd.cr50.cold_reset')

  def test_is_main_dev_prefix(self):
    """Test _is_main_dev_prefix()."""
    servod = servo_server.Servod()
    self.assertTrue(servod._is_main_dev_prefix(''))
    self.assertTrue(servod._is_main_dev_prefix('main'))
    self.assertFalse(servod._is_main_dev_prefix('dummy'))

  @unittest.mock.patch('servo.servo_server.Servod._get_control_prefix_and_name', unittest.mock.MagicMock(return_value=('', 'cold_reset')))
  def test_get_dev_and_name(self):
    """Test _get_dev_and_name()."""
    servod = servo_server.Servod()
    dev = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    dev2 = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    servod._devices = {"dev" : dev, "dev2" : dev2, '' : dev, 'main': dev, 'root' : dev2}
    dev.syscfg = unittest.mock.MagicMock()
    dev2.syscfg = unittest.mock.MagicMock()
    dev.syscfg.is_control = unittest.mock.MagicMock(return_value=False)
    dev2.syscfg.is_control = unittest.mock.MagicMock(return_value=True)

    self.assertEqual(servod._get_dev_and_name("cold_reset"), (dev2, "cold_reset"))

  @unittest.mock.patch('servo.servo_server.Servod._get_control_prefix_and_name', unittest.mock.MagicMock(return_value=('dummy', 'cold_reset')))
  def test_get_dev_and_name_invalid_prefix(self):
    """Test _get_dev_and_name() in case the prefix is invalid."""
    servod = servo_server.Servod()
    with self.assertRaisesRegex(servo_server.ServodError, 'No servo device registered for prefix dummy'):
      servod._get_dev_and_name('ccd_cr50.cold_reset')

  @unittest.mock.patch('servo.servo_server.Servod._get_control_prefix_and_name', unittest.mock.MagicMock(return_value=('', 'cold_reset')))
  def test_get_dev_and_name_error(self):
    """Test _get_dev_and_name() in case the control does not exist."""
    servod = servo_server.Servod()
    dev = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    dev2 = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    servod._devices = {"dev" : dev, "dev2" : dev2, '' : dev, 'main': dev, 'root' : dev2}
    dev.syscfg = unittest.mock.MagicMock()
    dev2.syscfg = unittest.mock.MagicMock()
    dev.syscfg.is_control = unittest.mock.MagicMock(return_value=False)
    dev2.syscfg.is_control = unittest.mock.MagicMock(return_value=False)
    servod._controls = ['main.cold_reset', 'root.cold_reset', 'ccd_cr50.cold_reset']

    with self.assertRaisesRegex(servo_server.ServodError, "No control named 'cold_reset' registerd with any connected servo device."):
      servod._get_dev_and_name("cold_reset")

  def test_get(self):
    """Test get()."""
    servod = servo_server.Servod()
    dev = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    servod._get_dev_and_name = unittest.mock.MagicMock(return_value=(dev, "cold_reset"))
    dev.get = unittest.mock.MagicMock(return_value="on")

    self.assertEqual(servod.get("cold_reset"), "on")

  def test_get_serial(self):
    """Test get()."""
    servod = servo_server.Servod()
    servod.get_legacy_serial_number = unittest.mock.MagicMock(return_value="12345")

    self.assertEqual(servod.get("ccd_serialname"), "12345")

  def test_get_legacy_serial_number(self):
    """Test get_legacy_serial_number()."""
    servod = servo_server.Servod()
    dev = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    dev2 = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    dev3 = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    dev.template = servo_dev_templates.GetTemplateClassByName('servo_v4p1')
    dev2.template = servo_dev_templates.GetTemplateClassByName('ccd_cr50')
    dev3.template = servo_dev_templates.GetTemplateClassByName('c2d2')
    servod._unique_devices = {"dev" : dev, "dev2" : dev2, "dev3" : dev3}
    dev._serial = "dev_serial"
    dev2._serial = "dev2_serial"
    dev3._serial = "dev3_serial"
    servod.get_main_device = unittest.mock.MagicMock(return_value=dev)
    self.assertEqual(servod.get("_serialname"), "dev_serial")
    self.assertEqual(servod.get("111._serialname"), "dev_serial")
    self.assertEqual(servod.get("ccd_serialname"), "dev2_serial")
    self.assertEqual(servod.get("c_serialname"), "unknown")
    self.assertEqual(servod.get("servo_micro_serialname"), "unknown")

  def test_set(self):
    """Test set()."""
    servod = servo_server.Servod()
    dev = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    servod._get_dev_and_name = unittest.mock.MagicMock(return_value=(dev, "cold_reset"))
    dev.set = unittest.mock.MagicMock()

    servod.set("cold_reset", "on")
    dev.set.assert_called_once_with("cold_reset", "on")

  def test_update_known_ctrls(self):
    """Test update_known_ctrls()."""
    servod = servo_server.Servod()
    dev = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    dev2 = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    servod._devices = {"dev" : dev, "dev2" : dev2, "" : dev, "root" : dev2}
    dev.syscfg = unittest.mock.MagicMock()
    dev2.syscfg = unittest.mock.MagicMock()
    dev.syscfg.get_all_controls = unittest.mock.MagicMock(return_value=set(['ctrl1', 'ctrl2']))
    dev2.syscfg.get_all_controls = unittest.mock.MagicMock(return_value=set(['ctrl1', 'ctrl2']))

    servod.update_known_ctrls()
    self.assertEqual(servod._controls, ['ctrl1', 'ctrl2', 'dev.ctrl1', 'dev.ctrl2', 'dev2.ctrl1',
      'dev2.ctrl2', 'root.ctrl1', 'root.ctrl2'])

  def test_has_control(self):
    """Test has_control()."""
    servod = servo_server.Servod()
    servod._controls = ['cold_reset', 'main.cold_reset', 'root.cold_reset', 'ccd_cr50.cold_reset']

    self.assertTrue(servod.has_control('root.cold_reset'))
    self.assertFalse(servod.has_control('warm_reset'))

  def test_doc_all(self):
    """Test doc_all()."""
    servod = servo_server.Servod()
    servod.update_known_ctrls = unittest.mock.MagicMock()
    servod._controls = ['cold_reset', 'main.cold_reset', 'root.cold_reset', 'ccd_cr50.cold_reset']
    dev = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    servod._get_dev_and_name = unittest.mock.MagicMock(return_value=(dev, 'cold_reset'))
    dev.syscfg = unittest.mock.MagicMock()
    dev.syscfg.get_control_str = unittest.mock.MagicMock(return_value='ctrl_str')

    self.assertEqual(servod.doc_all(), 'ctrl_str\nctrl_str\nctrl_str\nctrl_str')

  def test_doc(self):
    """Test doc()."""
    servod = servo_server.Servod()
    dev = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    servod._get_dev_and_name = unittest.mock.MagicMock(return_value=(dev, 'cold_reset'))
    dev.doc = unittest.mock.MagicMock(return_value='doc_res')

    self.assertEqual(servod.doc('cold_reset'), 'doc_res')

  def test_set_get_all(self):
    """Test set_get_all()."""
    servod = servo_server.Servod()
    servod.set = unittest.mock.MagicMock(return_value='set_res')
    servod.get = unittest.mock.MagicMock(return_value='get_res')

    self.assertEqual(servod.set_get_all(["cold_reset", "cold_reset:on", "warm_reset"]), ['get_res', 'set_res', 'get_res'])

  def test_get_all(self):
    """Test get_all()."""
    servod = servo_server.Servod()
    servod.update_known_ctrls = unittest.mock.MagicMock()
    servod._controls = ['cold_reset', 'main.cold_reset', 'root.cold_reset', 'ccd_cr50.cold_reset']
    servod.get = unittest.mock.MagicMock(side_effect=['on', ValueError('valueerr')])

    self.assertEqual(servod.get_all(False), 'ccd_cr50.cold_reset:ERR\ncold_reset:on')

  def test_get_all_verbose(self):
    """Test get_all()."""
    servod = servo_server.Servod()
    servod.update_known_ctrls = unittest.mock.MagicMock()
    servod._controls = ['cold_reset', 'main.cold_reset', 'root.cold_reset', 'ccd_cr50.cold_reset']
    servod.get = unittest.mock.MagicMock(side_effect=['on', ValueError('valueerr')])
    servod.doc = unittest.mock.MagicMock(return_value='doc')

    self.assertEqual(servod.get_all(True), 'GET ccd_cr50.cold_reset = ERR :: doc\nGET cold_reset = on :: doc')

  def test_echo(self):
    """Test echo()."""
    servod = servo_server.Servod()
    self.assertEqual(servod.echo('cold_reset'), 'ECH0ING: cold_reset')

  def test_get_board(self):
    """Test get_board()."""
    servod = servo_server.Servod()
    dev = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    dev.board = 'atlas'
    servod.get_main_device = unittest.mock.MagicMock(return_value=dev)
    self.assertEqual(servod.get_board(), 'atlas')

  def test_get_base_board(self):
    """Test get_base_board()."""
    servod = servo_server.Servod()
    dev = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    dev.base_board = 'atlas'
    servod.get_main_device = unittest.mock.MagicMock(return_value=dev)
    self.assertEqual(servod.get_base_board(), 'atlas')

  def test_get_servo_serials(self):
    """Test get_servo_serials()."""
    servod = servo_server.Servod()
    servod.add_serial_number('dev', 'serial')
    self.assertEqual(servod.get_servo_serials(), {'dev' : 'serial'})

  def test_add_serial_number(self):
    """Test add_serial_number()."""
    servod = servo_server.Servod()
    servod.add_serial_number('dev', 'serial')
    self.assertEqual(servod._serialnames['dev'], 'serial')

  def test_get_main_device(self):
    """Test get_main_device()."""
    servod = servo_server.Servod()
    dev = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    dev2 = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    servod._devices = {"dev" : dev, "dev2" : dev2, "main" : dev}
    self.assertEqual(servod.get_main_device(), dev)

  def test_get_root_device(self):
    """Test get_root_device()."""
    servod = servo_server.Servod()
    dev = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    dev2 = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    servod._devices = {"dev" : dev, "dev2" : dev2, "" : dev}
    self.assertIsNone(servod.get_root_device())

    servod._devices[servo_dev_templates.ROOT_DEV_PREFIX] = dev2
    self.assertEqual(servod.get_root_device(), dev2)

  def test_get_controls_for_tag(self):
    """Test get_controls_for_tag()."""
    servod = servo_server.Servod()
    dev = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    dev2 = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    servod._devices = {"dev" : dev, "dev2" : dev2, "" : dev}
    servod.get_main_device = unittest.mock.MagicMock(return_value=dev)
    servod.get_root_device = unittest.mock.MagicMock(return_value=dev2)
    dev.syscfg = unittest.mock.MagicMock()
    dev2.syscfg = unittest.mock.MagicMock()
    dev.syscfg.get_controls_for_tag = unittest.mock.MagicMock(return_value=['ctrl1', 'ctrl2'])
    dev2.syscfg.get_controls_for_tag = unittest.mock.MagicMock(return_value=['ctrl1', 'ctrl2'])

    self.assertEqual(servod.get_controls_for_tag('tag'),
      ['ctrl1', 'ctrl2'])

  def test_get_config_files(self):
    """Test get_config_files()."""
    servod = servo_server.Servod()
    dev = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    dev2 = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    dev.__str__ = unittest.mock.MagicMock(return_value='dev-p')
    dev2.__str__ = unittest.mock.MagicMock(return_value='dev2-p')
    dev.syscfg = unittest.mock.MagicMock()
    dev2.syscfg = unittest.mock.MagicMock()
    dev.syscfg._loaded_xml_files = [('file1', 'file-data'), ('file2', 'file-data')]
    dev2.syscfg._loaded_xml_files = [('file3', 'file-data')]
    servod._unique_devices = {"dev" : dev, "dev2" : dev2}

    self.assertEqual(servod.get_config_files(), {'dev-p' : ['file1', 'file2'], 'dev2-p' : ['file3']})

  def test_get_interface_list(self):
    """Test get_interface_list()."""
    servod = servo_server.Servod()
    dev = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    dev2 = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    dev.__str__ = unittest.mock.MagicMock(return_value='dev-p')
    dev2.__str__ = unittest.mock.MagicMock(return_value='dev2-p')
    dev.get_interface_list = unittest.mock.MagicMock(return_value=['interface1', 'interface2'])
    dev2.get_interface_list = unittest.mock.MagicMock(return_value=['interface3'])
    servod._unique_devices = {"dev" : dev, "dev2" : dev2}

    self.assertEqual(servod.get_interface_list(),
      [('dev-p', 'interface1'), ('dev-p', 'interface2'), ('dev2-p', 'interface3')])

  def test_validate_dut_controller(self):
    """Test validate_dut_controller()."""
    servod = servo_server.Servod()
    dev = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    dev2 = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    dev.template = servo_dev_templates.GetTemplateClassByName("servo_v4")
    dev.template = servo_dev_templates.GetTemplateClassByName("ccd_cr50")
    servod._unique_devices = {"dev" : dev, "dev2" : dev2}
    servod.validate_dut_controller()

  def test_validate_dut_controller_no_board(self):
    """Test validate_dut_controller() in case no board is specified."""
    servod = servo_server.Servod()
    dev = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    servod._unique_devices = {"dev" : dev}
    dev.template = servo_dev_templates.GetTemplateClassByName("servo_v4")
    servod.get_board = unittest.mock.MagicMock(return_value=None)
    servod.validate_dut_controller()

  def test_validate_dut_controller_recovery(self):
    """Test validate_dut_controller() under recovery mode."""
    servod = servo_server.Servod()
    servod._logger.error = unittest.mock.MagicMock()
    servod._logger.info = unittest.mock.MagicMock()
    dev = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    servod._unique_devices = {"dev" : dev}
    dev.template = servo_dev_templates.GetTemplateClassByName("servo_v4")
    servod.get_board = unittest.mock.MagicMock(return_value='atlas')
    servod.get = unittest.mock.MagicMock(return_value='type-c')
    servod.set = unittest.mock.MagicMock()
    servod.get_main_device = unittest.mock.MagicMock(return_value=dev)
    diagnose.diagnose_ccd = unittest.mock.MagicMock(return_value=[diagnose.SBU_VOLTAGE_FLOAT])
    recovery.is_recovery_active = unittest.mock.MagicMock(return_value=True)

    servod.validate_dut_controller()

    servod.set.assert_has_calls([
      unittest.mock.call('dut_sbu_voltage_float_fault', 'on'),
      unittest.mock.call('dut_controller_missing_fault', 'on')
    ])
    servod._logger.error.assert_has_calls([
      unittest.mock.call('No Servo Micro, C2D2, or CCD detected for board %s', 'atlas'),
      unittest.mock.call('Try flipping the USB type C cable if you were using servo v4 type C.'),
      unittest.mock.call('If flipping the cable allows CCD, please file a bug '
                         'against the DUT platform with reproducing details.')
    ])
    servod._logger.info.assert_called_once_with('Will continue startup as recovery mode has been requested')

  def test_validate_dut_controller_erro(self):
    """Test validate_dut_controller() in case of error not under recovery mode."""
    servod = servo_server.Servod()
    servod._logger.error = unittest.mock.MagicMock()
    servod._logger.fatal = unittest.mock.MagicMock()
    dev = unittest.mock.MagicMock(spec=servo_dev.ServoDevice)
    servod._unique_devices = {"dev" : dev}
    dev.template = servo_dev_templates.GetTemplateClassByName("servo_v4")
    servod.get_board = unittest.mock.MagicMock(return_value='atlas')
    servod.get = unittest.mock.MagicMock(return_value='type-c')
    servod.set = unittest.mock.MagicMock()
    servod.get_main_device = unittest.mock.MagicMock(return_value=dev)
    diagnose.diagnose_ccd = unittest.mock.MagicMock(return_value=[diagnose.SBU_VOLTAGE_FLOAT])
    recovery.is_recovery_active = unittest.mock.MagicMock(return_value=False)

    with self.assertRaises(SystemExit) as cm:
      servod.validate_dut_controller()

    self.assertEqual(cm.exception.code, -1)
    servod.set.assert_has_calls([
      unittest.mock.call('dut_sbu_voltage_float_fault', 'on'),
      unittest.mock.call('dut_controller_missing_fault', 'on')
    ])
    servod._logger.error.assert_has_calls([
      unittest.mock.call('No Servo Micro, C2D2, or CCD detected for board %s', 'atlas'),
      unittest.mock.call('Try flipping the USB type C cable if you were using servo v4 type C.'),
      unittest.mock.call('If flipping the cable allows CCD, please file a bug '
                         'against the DUT platform with reproducing details.')
    ])
    servod._logger.fatal.assert_called_once_with('No device interface (Servo Micro, C2D2, or CCD) connected.')

  @unittest.mock.patch('servo.servod.ServodStarter.__init__', unittest.mock.MagicMock(return_value=None))
  def test_hwinit(self):
    """Test _hwinit()."""
    servod = servo_server.Servod()
    dev1 = unittest.mock.MagicMock()
    dev2 = unittest.mock.MagicMock()
    dev1.get_child_devices = unittest.mock.MagicMock(return_value=[])
    dev2.get_child_devices = unittest.mock.MagicMock(return_value=[dev1])
    dev1.syscfg = unittest.mock.MagicMock()
    dev1.syscfg.hwinit = [("ctr1", "dummy"), ("ctr2", "dummy")]
    dev1.hwinit = unittest.mock.MagicMock()
    dev2.hwinit = unittest.mock.MagicMock()
    servod.get_devices = unittest.mock.MagicMock(return_value=[dev1, dev2])

    servod.hwinit(verbose=True)

    dev1.hwinit.assert_called_once_with(verbose=True, skip_controls=set())
    dev2.hwinit.assert_called_once_with(verbose=True, skip_controls=set(["ctr1", "ctr2"]))

if __name__ == '__main__':
  unittest.main()
