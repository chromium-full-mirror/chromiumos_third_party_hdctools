# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import unittest

from google.protobuf.empty_pb2 import Empty

from servo.common import servo_dev_templates as tmpl
from servo.common.proto import driver_pb2
from servo.common.utils.interface_utils import InterfaceUtils
from servo.data import servo_interfaces
from servo.data.impl.driver_impl import _drv_dict_all
from servo.data.impl.driver_impl import DriverImpl
from servo.data.impl.system_config_service import get_system_config
from servo.drv import na


class TestDriverImpl(unittest.TestCase):
    @unittest.mock.patch(
        "servo.common.interface.build", unittest.mock.MagicMock(return_value=None)
    )
    def setUp(self):
        self.servo_v4_vid = tmpl.get_id("servo_v4")[0]
        self.servo_v4_pid = tmpl.get_id("servo_v4")[1]
        self.servo_v4_serial = "servo_v4_serial"
        servo_v4_interfaces = servo_interfaces.INTERFACE_DEFAULTS[self.servo_v4_vid][
            self.servo_v4_pid
        ]
        InterfaceUtils.sync_interface_lists(
            interfaces=servo_v4_interfaces,
            vid=self.servo_v4_vid,
            pid=self.servo_v4_pid,
            serial=self.servo_v4_serial,
        )
        InterfaceUtils.init_servo_interfaces(
            interfaces=servo_v4_interfaces,
            vid=self.servo_v4_vid,
            pid=self.servo_v4_pid,
            serial=self.servo_v4_serial,
        )

    @unittest.mock.patch(
        "servo.drv.cr50.cr50.__init__", unittest.mock.MagicMock(return_value=None)
    )
    @unittest.mock.patch(
        "servo.drv.cr50.cr50.set_complement", unittest.mock.MagicMock()
    )
    def test_get_param_drv_get_no_cache(self):
        """Test _get_param_drv()."""
        get_params = {
            "cmd": "get",
            "uart_cmd": "ecrst",
            "regex": "EC_RST_L is (asserted|deasserted)",
            "group": "1",
            "interface": "9",
            "drv": "cr50",
            "map": "asserted_re",
            "clobber_ok": "",
        }
        set_params = {
            "cmd": "set",
            "subtype": "cold_reset",
            "interface": "9",
            "drv": "cr50",
            "map": "onoff_i",
            "clobber_ok": "",
        }
        map_params = {"deasserted", "asserted"}
        driver_impl = DriverImpl("test_core_addr", "test_data_addr")
        syscfg = get_system_config(
            vid=self.servo_v4_vid, pid=self.servo_v4_pid, serial=self.servo_v4_serial
        )
        syscfg.lookup_control_params = unittest.mock.MagicMock(
            return_value=(set_params, get_params)
        )
        syscfg.lookup_map_params = unittest.mock.MagicMock(return_value=map_params)
        interface_key = InterfaceUtils.get_interface_key(
            self.servo_v4_vid, self.servo_v4_pid, self.servo_v4_serial
        )
        params = driver_impl._get_param_drv(
            control_name="cold_reset",
            device_type="servo_v4p1",
            syscfg=syscfg,
            interface_key=interface_key,
            is_get=True,
        )[0]
        self.assertEqual(params, get_params)

    @unittest.mock.patch(
        "servo.drv.cr50.cr50.__init__", unittest.mock.MagicMock(return_value=None)
    )
    @unittest.mock.patch(
        "servo.drv.cr50.cr50.set_complement", unittest.mock.MagicMock()
    )
    def test_get_param_drv_set_no_cache(self):
        """Test _get_param_drv()."""
        get_params = {
            "cmd": "get",
            "uart_cmd": "ecrst",
            "regex": "EC_RST_L is (asserted|deasserted)",
            "group": "1",
            "interface": "9",
            "drv": "cr50",
            "map": "asserted_re",
            "clobber_ok": "",
        }
        set_params = {
            "cmd": "set",
            "subtype": "test_reset",
            "interface": "9",
            "drv": "cr50",
            "map": "onoff_i",
            "clobber_ok": "",
        }
        map_params = {"0", "1"}
        driver_impl = DriverImpl("test_core_addr", "test_data_addr")
        syscfg = get_system_config(
            vid=self.servo_v4_vid, pid=self.servo_v4_pid, serial=self.servo_v4_serial
        )
        syscfg.lookup_control_params = unittest.mock.MagicMock(
            return_value=(set_params, get_params)
        )
        syscfg.lookup_map_params = unittest.mock.MagicMock(return_value=map_params)
        interface_key = InterfaceUtils.get_interface_key(
            self.servo_v4_vid, self.servo_v4_pid, self.servo_v4_serial
        )
        params = driver_impl._get_param_drv(
            control_name="test_reset",
            device_type="servo_v4p1",
            syscfg=syscfg,
            interface_key=interface_key,
            is_get=False,
        )[0]
        self.assertEqual(params, set_params)

    def test_get_param_drv_get_cache(self):
        """Test _get_param_drv()."""
        interface_key = InterfaceUtils.get_interface_key(
            self.servo_v4_vid, self.servo_v4_pid, self.servo_v4_serial
        )
        _drv_dict_all[interface_key] = {"test_get": {"get": ["testing"]}}
        driver_impl = DriverImpl("test_core_addr", "test_data_addr")
        syscfg = get_system_config(
            vid=self.servo_v4_vid, pid=self.servo_v4_pid, serial=self.servo_v4_serial
        )
        drv = driver_impl._get_param_drv(
            control_name="test_get",
            device_type="servo_v4p1",
            syscfg=syscfg,
            interface_key=interface_key,
            is_get=True,
        )[0]
        self.assertEqual(drv, "testing")

    def test_get_param_drv_set_cache(self):
        """Test _get_param_drv()."""
        interface_key = InterfaceUtils.get_interface_key(
            self.servo_v4_vid, self.servo_v4_pid, self.servo_v4_serial
        )
        _drv_dict_all[interface_key] = {"test_set": {"set": ["testing"]}}
        driver_impl = DriverImpl("test_core_addr", "test_data_addr")
        syscfg = get_system_config(
            vid=self.servo_v4_vid, pid=self.servo_v4_pid, serial=self.servo_v4_serial
        )
        drv = driver_impl._get_param_drv(
            control_name="test_set",
            device_type="servo_v4p1",
            syscfg=syscfg,
            interface_key=interface_key,
            is_get=False,
        )
        self.assertEqual(drv, ["testing"])

    def test_get(self):
        """Test get()."""
        na_drv = unittest.mock.MagicMock(spec=na.na)
        driver_impl = DriverImpl("test_core_addr", "test_data_addr")
        driver_impl._get_param_drv = unittest.mock.MagicMock(
            return_value=({}, na_drv, None)
        )
        na_drv.get = unittest.mock.MagicMock(return_value="return_value")

        request = driver_pb2.DriverRequest(
            control_name="cold_reset",
            vid=self.servo_v4_vid,
            pid=self.servo_v4_pid,
            serial=self.servo_v4_serial,
            device_type="servo_v4p1",
            set_empty_value=Empty(),
        )
        driver_impl.CallDriver(request, None)
        na_drv.get.assert_called_once()

    def test_set(self):
        """Test set()."""
        na_drv = unittest.mock.MagicMock(spec=na.na)
        driver_impl = DriverImpl("test_core_addr", "test_data_addr")
        driver_impl._get_param_drv = unittest.mock.MagicMock(
            return_value=({}, na_drv, None)
        )
        na_drv.set = unittest.mock.MagicMock()
        request = driver_pb2.DriverRequest(
            control_name="cold_reset",
            vid=self.servo_v4_vid,
            pid=self.servo_v4_pid,
            serial=self.servo_v4_serial,
            device_type="servo_v4p1",
        )
        request.value.string_value = "1"

        driver_impl.CallDriver(request, None)
        na_drv.set.assert_called_once_with(1)
