# Copyright 2020 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Driver class for reading properties of a Servod I2C pseudo controller."""

import json

from servo.drv import hw_driver


class i2cPseudo(hw_driver.HwDriver):
    """Class to access drv=i2c_pseudo controls."""

    def _Get_is_started(self):
        """Check if the I2C pseudo adapter has been started.

        Returns: bool
        """
        return self._interface.pseudo_adap is not None

    def _Get_is_running(self):
        """Check if the I2C pseudo adapter I/O thread is running.

        Returns: bool
        """
        pseudo_adap = self._interface.pseudo_adap
        return pseudo_adap is not None and pseudo_adap.is_running

    def _Get_i2c_adapter_num(self):
        """Get the I2C adapter number of this I2C pseudo adapter.

        Returns: None or int
        """
        pseudo_adap = self._interface.pseudo_adap
        return None if pseudo_adap is None else pseudo_adap.i2c_adapter_num

    def _Get_i2c_pseudo_id(self):
        """Get the I2C pseudo ID of this I2C pseudo adapter.

        Returns: None or int
        """
        pseudo_adap = self._interface.pseudo_adap
        return None if pseudo_adap is None else pseudo_adap.i2c_pseudo_id

    def _Get_servo_i2c_bus_type(self):
        """Get the Servo I2C bus type of this I2C pseudo adapter.

        Returns: None or bytes or str
        """
        pseudo_adap = self._interface.pseudo_adap
        return (
            None
            if pseudo_adap is None or pseudo_adap.servo_i2c_bus is None
            else pseudo_adap.servo_i2c_bus.__class__.__name__
        )

    def _Get_pseudo_device_path(self):
        """Get the i2c-pseudo device file path this I2C pseudo adapter is using.

        Returns: None or bytes or str
        """
        pseudo_adap = self._interface.pseudo_adap
        return None if pseudo_adap is None else pseudo_adap.pseudo_device_path

    def _Get_xfer_counters(self):
        """Get the I2C pseudo controller transfer counters.

        Returns:
            None or str - JSON mapping of counter names to counts
        """
        pseudo_adap = self._interface.pseudo_adap
        return (
            None
            if pseudo_adap is None
            else json.dumps(pseudo_adap.get_xfer_counters(), sort_keys=True, indent=4)
        )
