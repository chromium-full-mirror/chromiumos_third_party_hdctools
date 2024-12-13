# Copyright 2015 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Access to Texas Instruments INA3221.

Triple-Channel, High-Side Measurement, Shunt and Bus Voltage Monitor
with i2c Interface.
"""
from servo.drv import ina2xx


# pylint: disable=invalid-name
# servod drv identification follows this naming convention.
class ina3221(ina2xx.ina2xx):
    """Object to access drv=ina3221 controls."""

    MSKEN_CNVR = 0x1

    BUSV_MV_PER_LSB = 8.0
    BUSV_MV_OFFSET = 3
    BUSV_MAX = 26000

    SHV_UV_PER_LSB = 40.0
    SHV_OFFSET = 3
    SHV_MASK = 0x7FF8

    def _read_cnvr_ovf(self):
        """Read mask/enable register and return needed values.

        Returns:
          tuple (is_cnvr, is_ovf, voltage) where:
            is_cnvr: boolean True if conversion ready else False
            is_ovf: boolean True if math overflow occurred else False
        """
        msken_reg = self._read_reg(self.REG_MSKEN)
        is_cnvr = (self.MSKEN_CNVR & msken_reg) != 0
        return (is_cnvr, 0)

    def _Get_milliamps(self):
        """Retrieve current measurement for ADC in milliamps by calculation.

        Calculation is I = Vshunt / Rsense

        Returns:
          float of current in milliamps
        """
        # overwrite because INA3221 has no current and power registers.

        vshunt_mv = self._get_shunt_millivolts()
        self._logger.debug("vshunt_mv = %2.2f", vshunt_mv)
        return vshunt_mv / self._rsense

    def _Get_milliwatts(self):
        """Retrieve power measurement for ADC in milliwatts from calculation.

        Returns:
          float of power in milliwatts
        """
        # overwrite because INA3221 has no current and power registers.
        volts = self._Get_millivolts() / 1000.0
        milliamps = self._Get_milliamps()
        return volts * milliamps
