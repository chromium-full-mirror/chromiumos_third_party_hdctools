# Copyright 2022 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Unit-tests to ensure that servodtool device works as intended."""

import argparse
import os
import subprocess
import time
import unittest
import unittest.mock
import usb

import servo.drv.pty_driver as pty_driver
import servo.interface.stm32uart as stm32uart
from servo.tools import device
from servo.utils import usb_hierarchy

class TestDevice(unittest.TestCase):
  """Test device.py."""

  def test_help(self):
    """Test help()."""
    self.assertEqual(device.Device().help, 'Manage servo device.')

  @unittest.mock.patch('servo.utils.usb_hierarchy.Hierarchy.GetAllUsbDeviceSysfsPaths',
    unittest.mock.MagicMock(return_value=['/path/1/a/b/c', '/path/2/a/b/c']))
  @unittest.mock.patch('servo.utils.usb_hierarchy.Hierarchy.SerialFromSysfs',
    unittest.mock.MagicMock(side_effect=['not_id', 'id']))
  def test__usb_path(self):
    """Test _usb_path()."""
    d = device.Device()
    res = d._usb_path('id')

    usb_hierarchy.Hierarchy.GetAllUsbDeviceSysfsPaths.assert_called_once_with([(device.SERVO_VID, None)])
    usb_hierarchy.Hierarchy.SerialFromSysfs.assert_has_calls([
      unittest.mock.call('/path/1/a/b/c'), unittest.mock.call('/path/2/a/b/c')])
    self.assertEqual(res, '/path/2/a/b/c')

  @unittest.mock.patch('servo.utils.usb_hierarchy.Hierarchy.GetAllUsbDeviceSysfsPaths',
    unittest.mock.MagicMock(return_value=['/path/1/a/b/c', '/path/2/a/b/c']))
  @unittest.mock.patch('servo.utils.usb_hierarchy.Hierarchy.SerialFromSysfs',
    unittest.mock.MagicMock(side_effect=['not_id', 'not_id']))
  def test__usb_path_nonexistent(self):
    """Test _usb_path()."""
    d = device.Device()
    res = d._usb_path('id')

    usb_hierarchy.Hierarchy.GetAllUsbDeviceSysfsPaths.assert_called_once_with([(device.SERVO_VID, None)])
    usb_hierarchy.Hierarchy.SerialFromSysfs.assert_has_calls([
      unittest.mock.call('/path/1/a/b/c'), unittest.mock.call('/path/2/a/b/c')])
    self.assertIsNone(res)

  def test_usb_path(self):
    """Test usb_path()."""
    d = device.Device()
    d._usb_path = unittest.mock.MagicMock(return_value='/path/1/a/b/c')
    d._logger.info = unittest.mock.MagicMock()
    d.error = unittest.mock.MagicMock()
    args = argparse.Namespace()
    args.serial = 'id'
    d.usb_path(args)

    d._usb_path.assert_called_once_with('id')
    d._logger.info.assert_called_once_with('/path/1/a/b/c')
    d.error.assert_not_called()

  def test_usb_path_nonexistent(self):
    """Test usb_path()."""
    d = device.Device()
    d._usb_path = unittest.mock.MagicMock(return_value=None)
    d._logger.info = unittest.mock.MagicMock()
    d.error = unittest.mock.MagicMock()
    args = argparse.Namespace()
    args.serial = 'id'
    d.usb_path(args)

    d._usb_path.assert_called_once_with('id')
    d._logger.info.assert_not_called
    d.error.assert_called_once_with('Device with serial %r not found.', 'id')

  @unittest.mock.patch('servo.utils.usb_hierarchy.Hierarchy.VendorIDFromSysfs',
    unittest.mock.MagicMock(return_value=0x18d1))
  @unittest.mock.patch('servo.utils.usb_hierarchy.Hierarchy.ProductIDFromSysfs',
    unittest.mock.MagicMock(return_value=0x501b))
  @unittest.mock.patch('servo.utils.usb_hierarchy.Hierarchy.DevNumFromSysfs',
    unittest.mock.MagicMock(return_value=1))
  @unittest.mock.patch('servo.drv.pty_driver.ptyDriver.__init__',
    unittest.mock.MagicMock(return_value=None))
  @unittest.mock.patch('servo.drv.pty_driver.ptyDriver._issue_cmd_get_results',
    unittest.mock.MagicMock(side_effect=[None, pty_driver.ptyError('No data was sent from the pty'), None, None, None]))
  @unittest.mock.patch('servo.interface.stm32uart.Suart.__init__',
    unittest.mock.MagicMock(return_value=None))
  @unittest.mock.patch('servo.interface.stm32uart.Suart.run',
    unittest.mock.MagicMock())
  @unittest.mock.patch('servo.interface.stm32uart.Suart.reinitialize',
    unittest.mock.MagicMock(side_effect=[Exception('reinit fail'), Exception('reinit fail'),
    Exception('reinit fail'), None]))
  @unittest.mock.patch('time.sleep', unittest.mock.MagicMock())
  def test_reboot(self):
    """Test reboot()."""
    d = device.Device()
    d._usb_path = unittest.mock.MagicMock(return_value='/path/1/a/b/c')
    d.error = unittest.mock.MagicMock(side_effect=SystemExit(1))
    d._logger.debug = unittest.mock.MagicMock()
    d._check_devnum_reset = unittest.mock.MagicMock()
    args = argparse.Namespace()
    args.serial = 'id'

    d.reboot(args)

    d._usb_path.assert_called_once_with('id')
    usb_hierarchy.Hierarchy.VendorIDFromSysfs.assert_called_once_with('/path/1/a/b/c')
    usb_hierarchy.Hierarchy.ProductIDFromSysfs.assert_called_once_with('/path/1/a/b/c')
    usb_hierarchy.Hierarchy.DevNumFromSysfs.assert_called_once_with('/path/1/a/b/c')
    pty_driver.ptyDriver._issue_cmd_get_results.assert_has_calls([
      unittest.mock.call('chan 0', ['>']),
      unittest.mock.call('reboot', ['>']),
      unittest.mock.call('chan 0', ['>']),
      unittest.mock.call('serialno', [r'Serial number: ([^\r\n]+)[\n\r]+']),
      unittest.mock.call('chan restore', ['>'])])
    d._check_devnum_reset('/path/1/a/b/c', 1, 'reboot')
    d._logger.debug.assert_has_calls([
      unittest.mock.call('Attempt %d to interact with console post reboot', 1),
      unittest.mock.call(unittest.mock.ANY),
      unittest.mock.call('Attempt %d to interact with console post reboot', 2),
      unittest.mock.call(unittest.mock.ANY),
      unittest.mock.call('Attempt %d to interact with console post reboot', 3),
      unittest.mock.call(unittest.mock.ANY),
      unittest.mock.call('Attempt %d to interact with console post reboot', 4)])
    time.sleep.assert_has_calls([
      unittest.mock.call(d.REBOOT_SLEEP_S),
      unittest.mock.call(d.REBOOT_SLEEP_S),
      unittest.mock.call(d.REBOOT_SLEEP_S)])
    d.error.assert_not_called()

  def test_reboot_nonexistent(self):
    """Test reboot()."""
    d = device.Device()
    d._usb_path = unittest.mock.MagicMock(return_value=None)
    d.error = unittest.mock.MagicMock(side_effect=SystemExit(1))
    args = argparse.Namespace()
    args.serial = 'id'

    with self.assertRaises(SystemExit) as cm:
      d.reboot(args)

    self.assertEqual(cm.exception.code, 1)
    d._usb_path.assert_called_once_with('id')
    d.error.assert_called_once_with('Device with serial %r not found.', 'id')

  @unittest.mock.patch('servo.utils.usb_hierarchy.Hierarchy.VendorIDFromSysfs',
    unittest.mock.MagicMock(return_value=0x18d1))
  @unittest.mock.patch('servo.utils.usb_hierarchy.Hierarchy.ProductIDFromSysfs',
    unittest.mock.MagicMock(return_value=0x5042))
  @unittest.mock.patch('servo.utils.usb_hierarchy.Hierarchy.DevNumFromSysfs',
    unittest.mock.MagicMock(return_value=1))
  def test_reboot_cannot_reboot(self):
    """Test reboot()."""
    d = device.Device()
    d._usb_path = unittest.mock.MagicMock(return_value='/path/1/a/b/c')
    d.error = unittest.mock.MagicMock(side_effect=SystemExit(1))
    args = argparse.Namespace()
    args.serial = 'id'

    with self.assertRaises(SystemExit) as cm:
      d.reboot(args)

    self.assertEqual(cm.exception.code, 1)
    d._usb_path.assert_called_once_with('id')
    usb_hierarchy.Hierarchy.VendorIDFromSysfs.assert_called_once_with('/path/1/a/b/c')
    usb_hierarchy.Hierarchy.ProductIDFromSysfs.assert_called_once_with('/path/1/a/b/c')
    usb_hierarchy.Hierarchy.DevNumFromSysfs.assert_called_once_with('/path/1/a/b/c')
    d.error.assert_called_once_with('Device %04x:%04x %s does not support reboot', 0x18d1, 0x5042, 'id')

  @unittest.mock.patch('servo.utils.usb_hierarchy.Hierarchy.VendorIDFromSysfs',
    unittest.mock.MagicMock(return_value=0x18d1))
  @unittest.mock.patch('servo.utils.usb_hierarchy.Hierarchy.ProductIDFromSysfs',
    unittest.mock.MagicMock(return_value=0x501b))
  @unittest.mock.patch('servo.utils.usb_hierarchy.Hierarchy.DevNumFromSysfs',
    unittest.mock.MagicMock(return_value=1))
  @unittest.mock.patch('servo.drv.pty_driver.ptyDriver.__init__',
    unittest.mock.MagicMock(return_value=None))
  @unittest.mock.patch('servo.drv.pty_driver.ptyDriver._issue_cmd_get_results',
    unittest.mock.MagicMock(side_effect=[None, pty_driver.ptyError('No data was sent from the pty')]))
  @unittest.mock.patch('servo.interface.stm32uart.Suart.__init__',
    unittest.mock.MagicMock(return_value=None))
  @unittest.mock.patch('servo.interface.stm32uart.Suart.run',
    unittest.mock.MagicMock())
  @unittest.mock.patch('servo.interface.stm32uart.Suart.reinitialize',
    unittest.mock.MagicMock(side_effect=Exception('reinit fail')))
  @unittest.mock.patch('time.sleep', unittest.mock.MagicMock())
  def test_reboot_exception(self):
    """Test reboot()."""
    d = device.Device()
    d._usb_path = unittest.mock.MagicMock(return_value='/path/1/a/b/c')
    d.error = unittest.mock.MagicMock(side_effect=SystemExit(1))
    d._logger.debug = unittest.mock.MagicMock()
    d._check_devnum_reset = unittest.mock.MagicMock()
    args = argparse.Namespace()
    args.serial = 'id'

    with self.assertRaises(SystemExit) as cm:
      d.reboot(args)

    self.assertEqual(cm.exception.code, 1)
    d._usb_path.assert_called_once_with('id')
    usb_hierarchy.Hierarchy.VendorIDFromSysfs.assert_called_once_with('/path/1/a/b/c')
    usb_hierarchy.Hierarchy.ProductIDFromSysfs.assert_called_once_with('/path/1/a/b/c')
    usb_hierarchy.Hierarchy.DevNumFromSysfs.assert_called_once_with('/path/1/a/b/c')
    pty_driver.ptyDriver._issue_cmd_get_results.assert_has_calls([
      unittest.mock.call('chan 0', ['>']),
      unittest.mock.call('reboot', ['>'])])
    d._check_devnum_reset('/path/1/a/b/c', 1, 'reboot')
    d._logger.debug.assert_has_calls([
      unittest.mock.call('Attempt %d to interact with console post reboot', 1),
      unittest.mock.call(unittest.mock.ANY),
      unittest.mock.call('Attempt %d to interact with console post reboot', 2),
      unittest.mock.call(unittest.mock.ANY),
      unittest.mock.call('Attempt %d to interact with console post reboot', 3),
      unittest.mock.call(unittest.mock.ANY),
      unittest.mock.call('Attempt %d to interact with console post reboot', 4),
      unittest.mock.call(unittest.mock.ANY)])
    time.sleep.assert_has_calls([
      unittest.mock.call(d.REBOOT_SLEEP_S),
      unittest.mock.call(d.REBOOT_SLEEP_S),
      unittest.mock.call(d.REBOOT_SLEEP_S),
      unittest.mock.call(d.REBOOT_SLEEP_S)])
    d.error.assert_called_once_with('Device %04x:%04x %s issue after reboot: %s',
      0x18d1, 0x501b, 'id', unittest.mock.ANY)

  @unittest.mock.patch('servo.utils.usb_hierarchy.Hierarchy.DevNumFromSysfs',
    unittest.mock.MagicMock(return_value=1))
  @unittest.mock.patch('servo.utils.usb_hierarchy.Hierarchy.BusNumFromSysfs',
    unittest.mock.MagicMock(return_value=2))
  @unittest.mock.patch('usb.core.find', unittest.mock.MagicMock())
  @unittest.mock.patch('usb.util.get_string', unittest.mock.MagicMock())
  def test_usb_comms(self):
    """Test usb_comms()."""
    d = device.Device()
    d._usb_path = unittest.mock.MagicMock(return_value='/path/1/a/b/c')
    d.error = unittest.mock.MagicMock(side_effect=SystemExit(1))
    args = argparse.Namespace()
    args.serial = 'id'

    d.usb_comms(args)

    d._usb_path.assert_called_once_with('id')
    usb_hierarchy.Hierarchy.DevNumFromSysfs.assert_called_once_with('/path/1/a/b/c')
    usb_hierarchy.Hierarchy.BusNumFromSysfs.assert_called_once_with('/path/1/a/b/c')
    usb.core.find.assert_called_once_with(address=1, bus=2)
    usb.util.get_string.assert_called_once()
    d.error.assert_not_called()

  def test_usb_comms_nonexistent(self):
    """Test usb_comms()."""
    d = device.Device()
    d._usb_path = unittest.mock.MagicMock(return_value=None)
    d.error = unittest.mock.MagicMock(side_effect=SystemExit(1))
    args = argparse.Namespace()
    args.serial = 'id'

    with self.assertRaises(SystemExit) as cm:
      d.usb_comms(args)

    self.assertEqual(cm.exception.code, 1)
    d._usb_path.assert_called_once_with('id')
    d.error.assert_called_once_with('Device with serial %r not found.', 'id')

  @unittest.mock.patch('servo.utils.usb_hierarchy.Hierarchy.DevNumFromSysfs',
    unittest.mock.MagicMock(return_value=1))
  @unittest.mock.patch('servo.utils.usb_hierarchy.Hierarchy.BusNumFromSysfs',
    unittest.mock.MagicMock(return_value=2))
  @unittest.mock.patch('usb.core.find', unittest.mock.MagicMock(return_value=None))
  def test_usb_comms_no_usb(self):
    """Test usb_comms()."""
    d = device.Device()
    d._usb_path = unittest.mock.MagicMock(return_value='/path/1/a/b/c')
    d.error = unittest.mock.MagicMock(side_effect=SystemExit(1))
    args = argparse.Namespace()
    args.serial = 'id'

    with self.assertRaises(SystemExit) as cm:
      d.usb_comms(args)

    self.assertEqual(cm.exception.code, 1)
    d._usb_path.assert_called_once_with('id')
    usb_hierarchy.Hierarchy.DevNumFromSysfs.assert_called_once_with('/path/1/a/b/c')
    usb_hierarchy.Hierarchy.BusNumFromSysfs.assert_called_once_with('/path/1/a/b/c')
    usb.core.find.assert_called_once_with(address=1, bus=2)
    d.error.assert_called_once_with('Device with serial %r not found on pyusb.', 'id')

  @unittest.mock.patch('servo.utils.usb_hierarchy.Hierarchy.DevNumFromSysfs',
    unittest.mock.MagicMock(return_value=1))
  @unittest.mock.patch('servo.utils.usb_hierarchy.Hierarchy.BusNumFromSysfs',
    unittest.mock.MagicMock(return_value=2))
  @unittest.mock.patch('usb.core.find', unittest.mock.MagicMock())
  @unittest.mock.patch('usb.util.get_string', unittest.mock.MagicMock(side_effect=ValueError('value err')))
  def test_usb_comms_fail_comms(self):
    """Test usb_comms()."""
    d = device.Device()
    d._usb_path = unittest.mock.MagicMock(return_value='/path/1/a/b/c')
    d.error = unittest.mock.MagicMock(side_effect=SystemExit(1))
    args = argparse.Namespace()
    args.serial = 'id'

    with self.assertRaises(SystemExit) as cm:
      d.usb_comms(args)

    self.assertEqual(cm.exception.code, 1)
    d._usb_path.assert_called_once_with('id')
    usb_hierarchy.Hierarchy.DevNumFromSysfs.assert_called_once_with('/path/1/a/b/c')
    usb_hierarchy.Hierarchy.BusNumFromSysfs.assert_called_once_with('/path/1/a/b/c')
    usb.core.find.assert_called_once_with(address=1, bus=2)
    usb.util.get_string.assert_called_once()
    d.error.assert_called_once_with('Device with serial %r has USB comms issues. %s', 'id', unittest.mock.ANY)

  @unittest.mock.patch('subprocess.check_output', unittest.mock.MagicMock())
  def test__run_uhubctl_command(self):
    """Test _run_uhubctl_command()."""
    d = device.Device()
    d.error = unittest.mock.MagicMock(side_effect=SystemExit(1))
    d._build_and_assert_uhubctl = unittest.mock.MagicMock(return_value=['cmd'])

    d._run_uhubctl_command('/path/1/a/b/c', 2, 'reset')

    d._build_and_assert_uhubctl.assert_called_once_with(hub='/path/1/a/b/c', port=2)
    subprocess.check_output.assert_called_once_with(['cmd', '-a', str(d.ACTION_DICT['reset']), '-r', str(d.REPS)],
      stderr=subprocess.STDOUT)
    d.error.assert_not_called()

  def test__run_uhubctl_command_no_action(self):
    """Test _run_uhubctl_command()."""
    d = device.Device()
    d.error = unittest.mock.MagicMock(side_effect=SystemExit(1))
    d._build_and_assert_uhubctl = unittest.mock.MagicMock(return_value=['cmd'])

    with self.assertRaises(SystemExit) as cm:
      d._run_uhubctl_command('/path/1/a/b/c', 2, 'random')

    self.assertEqual(cm.exception.code, 1)
    d._build_and_assert_uhubctl.assert_called_once_with(hub='/path/1/a/b/c', port=2)
    d.error.assert_called_once_with('Action %s unknown', 'random')

  @unittest.mock.patch('subprocess.check_output', unittest.mock.MagicMock(
    side_effect=subprocess.CalledProcessError(1, ['cmd'], 'process err')))
  def test__run_uhubctl_command_error(self):
    """Test _run_uhubctl_command()."""
    d = device.Device()
    d.error = unittest.mock.MagicMock(side_effect=SystemExit(1))
    d._build_and_assert_uhubctl = unittest.mock.MagicMock(return_value=['cmd'])

    with self.assertRaises(SystemExit) as cm:
      d._run_uhubctl_command('/path/1/a/b/c', 2, 'reset')

    self.assertEqual(cm.exception.code, 1)
    d._build_and_assert_uhubctl.assert_called_once_with(hub='/path/1/a/b/c', port=2)
    subprocess.check_output.assert_called_once_with(['cmd', '-a', str(d.ACTION_DICT['reset']), '-r', str(d.REPS)],
      stderr=subprocess.STDOUT)
    d.error.assert_called_once_with('Error performing the uhubctl command. ran: "%s". %s.',
      'cmd -a 2 -r 100', "Command '['cmd']' returned non-zero exit status 1.")

  @unittest.mock.patch('subprocess.check_output', unittest.mock.MagicMock())
  def test__build_and_assert_uhubctl(self):
    """Test _build_and_assert_uhubctl()."""
    d = device.Device()
    d.error = unittest.mock.MagicMock(side_effect=SystemExit(1))

    d._build_and_assert_uhubctl('/path/1/a/b/c', 9990)

    subprocess.check_output.assert_has_calls([
      unittest.mock.call(['sudo', 'uhubctl'], stderr=subprocess.STDOUT),
      unittest.mock.call(['sudo', 'uhubctl', '-l', '/path/1/a/b/c', '-p', '9990'], stderr=subprocess.STDOUT)])
    d.error.assert_not_called()

  @unittest.mock.patch('subprocess.check_output', unittest.mock.MagicMock(
    side_effect=subprocess.CalledProcessError(1, ['cmd'], 'process err')))
  def test__build_and_assert_uhubctl_uhubctl_unavailable(self):
    """Test _build_and_assert_uhubctl()."""
    d = device.Device()
    d.error = unittest.mock.MagicMock(side_effect=SystemExit(1))

    with self.assertRaises(SystemExit) as cm:
      d._build_and_assert_uhubctl()

    self.assertEqual(cm.exception.code, 1)
    subprocess.check_output.assert_called_once_with(['sudo', 'uhubctl'],
      stderr=subprocess.STDOUT)
    d.error.assert_called_once_with('uhubctl not available. Be sure to run as sudo. %s',
      "Command '['cmd']' returned non-zero exit status 1.")

  @unittest.mock.patch('subprocess.check_output', unittest.mock.MagicMock(
    side_effect=[None, subprocess.CalledProcessError(1, ['cmd'], 'process err')]))
  def test__build_and_assert_uhubctl_no_hub_port(self):
    """Test _build_and_assert_uhubctl()."""
    d = device.Device()
    d.error = unittest.mock.MagicMock(side_effect=SystemExit(1))

    with self.assertRaises(SystemExit) as cm:
      d._build_and_assert_uhubctl('/path/1/a/b/c', 9990)

    self.assertEqual(cm.exception.code, 1)
    subprocess.check_output.assert_has_calls([
      unittest.mock.call(['sudo', 'uhubctl'], stderr=subprocess.STDOUT),
      unittest.mock.call(['sudo', 'uhubctl', '-l', '/path/1/a/b/c', '-p', '9990'], stderr=subprocess.STDOUT)])
    d.error.assert_called_once_with('hub %s with port %s unknown to uhubctl. '
      'Be sure the hub is a supported smart hub. %s', '/path/1/a/b/c', 9990,
      "Command '['cmd']' returned non-zero exit status 1.")

  @unittest.mock.patch('servo.utils.usb_hierarchy.Hierarchy.GetSysfsParentHubStub',
    unittest.mock.MagicMock(side_effect=['/path/internal/3-5.6', '/path/internal/3-5']))
  @unittest.mock.patch('servo.utils.usb_hierarchy.Hierarchy.ComplementBusNum',
    unittest.mock.MagicMock(return_value=12))
  @unittest.mock.patch('os.path.exists', unittest.mock.MagicMock(return_value=True))
  def test__get_hub_and_port(self):
    """Test _get_hub_and_port()."""
    d = device.Device()
    d.error = unittest.mock.MagicMock(side_effect=SystemExit(1))

    res = d._get_hub_and_port('/path/1/a/b/c', 0x520d)

    self.assertEqual(res, ('3-5', '6', '12-5'))
    d.error.assert_not_called()

  def test__get_hub_and_port_unimplemented(self):
    """Test _get_hub_and_port()."""
    d = device.Device()
    d.error = unittest.mock.MagicMock(side_effect=SystemExit(1))

    with self.assertRaises(SystemExit) as cm:
      d._get_hub_and_port('/path/1/a/b/c', 0x1011)

    self.assertEqual(cm.exception.code, 1)
    d.error.assert_called_once_with('Unimplemented pid: %04x', 0x1011)

  @unittest.mock.patch('servo.utils.usb_hierarchy.Hierarchy.GetSysfsParentHubStub',
    unittest.mock.MagicMock(side_effect=['/path/internal/hub', None]))
  def test__get_hub_and_port_no_smart_hub(self):
    """Test _get_hub_and_port()."""
    d = device.Device()
    d.error = unittest.mock.MagicMock(side_effect=SystemExit(1))

    with self.assertRaises(SystemExit) as cm:
      d._get_hub_and_port('/path/1/a/b/c', 0x520d)

    self.assertEqual(cm.exception.code, 1)
    d.error.assert_called_once_with('Device does not seem to be hanging on a (smart) hub. %r',
      '/path/1/a/b/c')

  @unittest.mock.patch('servo.utils.usb_hierarchy.Hierarchy.GetSysfsParentHubStub',
    unittest.mock.MagicMock(side_effect=['/path/internal/3-5.6', '/path/internal/3-5']))
  @unittest.mock.patch('servo.utils.usb_hierarchy.Hierarchy.ComplementBusNum',
    unittest.mock.MagicMock(return_value=None))
  def test__get_hub_and_port_no_busnum3(self):
    """Test _get_hub_and_port()."""
    d = device.Device()
    d.error = unittest.mock.MagicMock(side_effect=SystemExit(1))

    res = d._get_hub_and_port('/path/1/a/b/c', 0x520d)

    self.assertEqual(res, ('3-5', '6', None))
    d.error.assert_not_called()

  @unittest.mock.patch('servo.utils.usb_hierarchy.Hierarchy.GetSysfsParentHubStub',
    unittest.mock.MagicMock(side_effect=['/path/internal/3-5.6', '/path/internal/3-5']))
  @unittest.mock.patch('servo.utils.usb_hierarchy.Hierarchy.ComplementBusNum',
    unittest.mock.MagicMock(return_value=12))
  @unittest.mock.patch('os.path.exists', unittest.mock.MagicMock(return_value=False))
  def test__get_hub_and_port_nonexistent_hub3(self):
    """Test _get_hub_and_port()."""
    d = device.Device()
    d.error = unittest.mock.MagicMock(side_effect=SystemExit(1))

    res = d._get_hub_and_port('/path/1/a/b/c', 0x520d)

    self.assertEqual(res, ('3-5', '6', None))
    d.error.assert_not_called()

  @unittest.mock.patch('time.sleep', unittest.mock.MagicMock())
  @unittest.mock.patch('servo.utils.usb_hierarchy.Hierarchy.DevNumFromSysfs',
    unittest.mock.MagicMock(return_value=2))
  def test__check_devnum_reset(self):
    """Test _check_devnum_reset()."""
    d = device.Device()
    d.error = unittest.mock.MagicMock(side_effect=SystemExit(1))
    with unittest.mock.patch('time.time', unittest.mock.MagicMock(side_effect=[
      1, 1, 2, 3, 1 + d.MAX_REINIT_SLEEP_S])):
      d._check_devnum_reset('/path/1/a/b/c', 1, 'reset')

    usb_hierarchy.Hierarchy.DevNumFromSysfs.assert_called_once_with('/path/1/a/b/c')
    d.error.assert_not_called()

  @unittest.mock.patch('time.sleep', unittest.mock.MagicMock())
  @unittest.mock.patch('servo.utils.usb_hierarchy.Hierarchy.DevNumFromSysfs',
    unittest.mock.MagicMock(return_value=1))
  def test__check_devnum_reset_same_devnum(self):
    """Test _check_devnum_reset()."""
    d = device.Device()
    d.error = unittest.mock.MagicMock(side_effect=SystemExit(1))
    with unittest.mock.patch('time.time', unittest.mock.MagicMock(side_effect=[
      1, 1, 2, 3, 1 + d.MAX_REINIT_SLEEP_S])):
      with self.assertRaises(SystemExit) as cm:
        d._check_devnum_reset('/path/1/a/b/c', 1, 'reset')

    self.assertEqual(cm.exception.code, 1)
    usb_hierarchy.Hierarchy.DevNumFromSysfs.assert_called_once_with('/path/1/a/b/c')
    d.error.assert_called_once_with('%r likely unsuccessful. devnum stayed the same.', 'reset')

  @unittest.mock.patch('time.sleep', unittest.mock.MagicMock())
  @unittest.mock.patch('servo.utils.usb_hierarchy.Hierarchy.DevNumFromSysfs',
    unittest.mock.MagicMock(side_effect=usb_hierarchy.HierarchyError()))
  def test__check_devnum_reset_cannot_read_devnum(self):
    """Test _check_devnum_reset()."""
    d = device.Device()
    d.error = unittest.mock.MagicMock(side_effect=SystemExit(1))
    with unittest.mock.patch('time.time', unittest.mock.MagicMock(side_effect=[
      1, 1, 2, 3, 1 + d.MAX_REINIT_SLEEP_S])):
      with self.assertRaises(SystemExit) as cm:
        d._check_devnum_reset('/path/1/a/b/c', 1, 'reset')

    self.assertEqual(cm.exception.code, 1)
    usb_hierarchy.Hierarchy.DevNumFromSysfs.assert_has_calls([
      unittest.mock.call('/path/1/a/b/c'),
      unittest.mock.call('/path/1/a/b/c'),
      unittest.mock.call('/path/1/a/b/c')])
    d.error.assert_called_once_with('unable to read device |devnum| file after %ds. Giving up.',
      d.MAX_REINIT_SLEEP_S)

  def test_power_cycle_force(self):
    """Test power_cycle_force()."""
    d = device.Device()
    d.power_cycle = unittest.mock.MagicMock()
    args = argparse.Namespace()
    d.power_cycle_force(args)

    d.power_cycle.assert_called_once_with(args, force=True)

  def test_power_cycle_no_dev_path(self):
    """Test power_cycle()."""
    d = device.Device()
    d._build_and_assert_uhubctl = unittest.mock.MagicMock()
    d._usb_path = unittest.mock.MagicMock(return_value=None)
    d.error = unittest.mock.MagicMock(side_effect=SystemExit(1))
    args = argparse.Namespace()
    args.serial = 'id'

    with self.assertRaises(SystemExit) as cm:
      d.power_cycle(args)

    self.assertEqual(cm.exception.code, 1)
    d.error.assert_called_once_with('Device with serial %r not found.', 'id')

  @unittest.mock.patch('servo.utils.usb_hierarchy.Hierarchy.ProductIDFromSysfs',
    unittest.mock.MagicMock(return_value=0x501c))
  def test_power_cycle_unsupported_pid(self):
    """Test power_cycle()."""
    d = device.Device()
    d._build_and_assert_uhubctl = unittest.mock.MagicMock()
    d._usb_path = unittest.mock.MagicMock(return_value='/path/1/a/b/c')
    d.error = unittest.mock.MagicMock(side_effect=SystemExit(1))
    args = argparse.Namespace()
    args.serial = 'id'

    with self.assertRaises(SystemExit) as cm:
      d.power_cycle(args)

    self.assertEqual(cm.exception.code, 1)
    d.error.assert_called_once_with('pid: 0x%04x currently not supported for usb power cycling. '
      'Please use one of: %s', 0x501c, '0x520d, 0x501b')

  @unittest.mock.patch('servo.utils.usb_hierarchy.Hierarchy.ProductIDFromSysfs',
    unittest.mock.MagicMock(return_value=0x501b))
  @unittest.mock.patch('servo.utils.usb_hierarchy.Hierarchy.DevNumFromSysfs',
    unittest.mock.MagicMock(return_value=1))
  def test_power_cycle_force_false(self):
    """Test power_cycle()."""
    d = device.Device()
    d._build_and_assert_uhubctl = unittest.mock.MagicMock()
    d._usb_path = unittest.mock.MagicMock(return_value='/path/1/a/b/c')
    d._get_hub_and_port = unittest.mock.MagicMock(return_value=('hub', 'port', 'hub3'))
    d._run_uhubctl_command = unittest.mock.MagicMock()
    d._check_devnum_reset = unittest.mock.MagicMock()
    d._logger.info = unittest.mock.MagicMock()
    d.error = unittest.mock.MagicMock(side_effect=SystemExit(1))
    args = argparse.Namespace()
    args.serial = 'id'

    d.power_cycle(args, False)

    d.error.assert_not_called()
    d._build_and_assert_uhubctl.assert_called_once()
    d._usb_path.assert_called_once_with('id')
    usb_hierarchy.Hierarchy.ProductIDFromSysfs.assert_called_once_with('/path/1/a/b/c')
    usb_hierarchy.Hierarchy.DevNumFromSysfs.assert_called_once_with('/path/1/a/b/c')
    d._get_hub_and_port.assert_called_once_with('/path/1/a/b/c', 0x501b)
    d._run_uhubctl_command.assert_called_once_with(hub='hub', port='port', action='reset')
    d._check_devnum_reset.assert_called_once_with('/path/1/a/b/c', 1, 'power-cycle')
    d._logger.info.assert_called_once_with('Successfully power-cycled device with serial %r. '
      '(At least reasonably confident).', 'id')

  @unittest.mock.patch('servo.utils.usb_hierarchy.Hierarchy.ProductIDFromSysfs',
    unittest.mock.MagicMock(return_value=0x501b))
  @unittest.mock.patch('servo.utils.usb_hierarchy.Hierarchy.DevNumFromSysfs',
    unittest.mock.MagicMock(return_value=1))
  @unittest.mock.patch('time.sleep', unittest.mock.MagicMock())
  def test_power_cycle_force_true(self):
    """Test power_cycle()."""
    d = device.Device()
    d._build_and_assert_uhubctl = unittest.mock.MagicMock()
    d._usb_path = unittest.mock.MagicMock(return_value='/path/1/a/b/c')
    d._get_hub_and_port = unittest.mock.MagicMock(return_value=('hub', 'port', 'hub3'))
    d._run_uhubctl_command = unittest.mock.MagicMock()
    d._check_devnum_reset = unittest.mock.MagicMock()
    d._logger.info = unittest.mock.MagicMock()
    d.error = unittest.mock.MagicMock(side_effect=SystemExit(1))
    args = argparse.Namespace()
    args.serial = 'id'

    d.power_cycle(args, True)

    d.error.assert_not_called()
    d._build_and_assert_uhubctl.assert_called_once()
    d._usb_path.assert_called_once_with('id')
    usb_hierarchy.Hierarchy.ProductIDFromSysfs.assert_called_once_with('/path/1/a/b/c')
    usb_hierarchy.Hierarchy.DevNumFromSysfs.assert_called_once_with('/path/1/a/b/c')
    d._get_hub_and_port.assert_called_once_with('/path/1/a/b/c', 0x501b)
    d._run_uhubctl_command.assert_has_calls([
      unittest.mock.call(hub='hub', port='port', action='off'),
      unittest.mock.call(hub='hub3', port='port', action='off'),
      unittest.mock.call(hub='hub3', port='port', action='on'),
      unittest.mock.call(hub='hub', port='port', action='on')
    ])
    time.sleep.assert_any_call(d.PWR_OFF_SLEEP_S)
    d._check_devnum_reset.assert_called_once_with('/path/1/a/b/c', 1, 'power-cycle')
    d._logger.info.assert_called_once_with('Successfully power-cycled device with serial %r. '
      '(At least reasonably confident).', 'id')

  def test_add_args(self):
    """Test add_args()."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='tool')
    tparser = subparsers.add_parser('device')
    device.Device().add_args(tparser)

    self.assertEqual(parser.parse_args(["device", "-s", "id", "power-cycle-force"]).command, "power-cycle-force")
    self.assertEqual(parser.parse_args(["device", "-s", "id", "power-cycle-force"]).serial, "id")
    self.assertEqual(parser.parse_args(["device", "--serial", "id", "power-cycle-force"]).serial, "id")
    self.assertEqual(parser.parse_args(["device", "-s", "id", "power-cycle"]).command, "power-cycle")
    self.assertEqual(parser.parse_args(["device", "-s", "id", "reboot"]).command, "reboot")
    self.assertEqual(parser.parse_args(["device", "-s", "id", "usb-comms"]).command, "usb-comms")
    self.assertEqual(parser.parse_args(["device", "-s", "id", "usb-path"]).command, "usb-path")

if __name__ == '__main__':
  unittest.main()
