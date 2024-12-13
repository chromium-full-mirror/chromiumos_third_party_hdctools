# Copyright 2011 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Base class to provide access to Texas Instruments INA-based ADCs.

Presently tested for:
  INA219
  INA231
  INA3221
"""

import logging

from servo.drv import base_pwr_adc


# pylint: disable=invalid-name
# servod drv identification follows this naming convention.
class Ina2xxError(base_pwr_adc.BasePWRADCError):
    """Error occurred accessing INA219."""


class ina2xx(base_pwr_adc.basePWRADC):
    """class definition.

    Note, instances of this object get dispatched via base class,
    HwDriver's get/set method.  That method ultimately calls:
      "_[GS]et_%s" % params['subtype'] below.

    For example, a control to read the millivolts of an ADC would be
    dispatched to call _Get_millivolts.
    """

    # maximum number of re-reads of bus voltage to do before raising
    # exception for failing to see a data conversion.  Note the CNVR bit
    # is affected by averaging and multiplication as well. I decided on
    # 100 by sampling the number average retries during calibration and
    # multiplying by 2x to be on the safe side
    BUSV_READ_RETRY = 100

    # sign bit of current output register
    CUR_SIGN = 0x8000
    # maximum value of current output register.
    CUR_MAX = 0x7FFF

    # maximum value of power output register.
    PWR_MAX = 0xFFFF
    # sign bit of the power output register.
    PWR_SIGN = 0

    # mask ( 3-bits ) for ina219 configuration modes
    CFG_MODE_MASK = 0x7
    # continuous mode
    CFG_MODE_CONT = 0x7
    # sleep mode
    CFG_MODE_SLEEP = 0

    @property
    def millivolts_per_lsb(self):
        """Bus voltage mv per lsb.

        Value is defined in the subclasses.

        Returns:
          float of bus voltage per lsb in millivolts
        """
        return self.BUSV_MV_PER_LSB

    @property
    def milliamps_per_lsb(self):
        """Calculate milliamps per least significant bit of the current register.

        Returns:
          float of current per lsb value in milliamps.
        """

        self._calibrate()
        lsb = self.CUR_LSB_COEFFICIENT / (self._calib_reg * self._rsense)
        self._logger.debug("lsb = %f" % lsb)
        return lsb

    @property
    def milliwatts_per_lsb(self):
        """Calculate milliwatts per least significant bit of the power register.

        Returns:
          float of power per lsb value in milliwatts.
        """

        lsb = self.PWR_LSB_COEFFICIENT * self.milliamps_per_lsb
        self._logger.debug("lsb = %f" % lsb)
        return lsb

    def _read_cnvr_ovf(self):
        raise NotImplementedError("Must be defined by child class")

    def _read_cnvr(self):
        (is_cnvr, _unused) = self._read_cnvr_ovf()
        return is_cnvr

    def _read_ovf(self):
        (_, is_ovf) = self._read_cnvr_ovf()
        return is_ovf

    def _reset(self):
        """Reset object state when device is transitioned to certain modes."""
        # TODO(tbroch) Not clear from data sheet what power-down makes IC forget
        # so I'm whacking everything stateful
        self._calib_reg = None
        self._reg_cache = None

    def _get_next_ovf(self):
        """Watch conversion ready bit assertion then return overflow status.

        Note datasheet doesn't spell this out but it seems logical.

        Returns:
          is_ovf: Boolean of whether overflow has occurred

        Raises:
          Ina2xxError: if conversion didn't assert after self.BUSV_READ_RETRY times
        """
        for _unused in range(self.BUSV_READ_RETRY):
            is_cnvr = self._read_cnvr()
            if is_cnvr:
                break

        # if we didn't _break_ from for loop
        if not is_cnvr:
            raise Ina2xxError("Failed to see conversion (CNVR) while calibrating")
        return self._read_ovf()

    def _calibrate(self):
        """Calibrate the INA219.

        Proper calibration of adc is paramount in successful sampling of the current
        and power measurements.

        As such, if overflow occurs re-calibration is done.  The calibration
        register is inversely proportional to precision of the adc's lsb for current
        and power conversion.

        For example, for a 50mOhm sense resistor with the calibration register set
        to its maximum (MAX_CALIB), the adc is capable of 800mA range @ ~12.5uA/lsb.
        Dividing the calibration by two would provide 1600mA range @ 25uA/lsb.

        Raises:
          Ina2xxError: If calibration failed or doesn't have register.
        """

        if not self._has_reg("cal"):
            raise Ina2xxError("ADC does NOT have calibration register")

        # TODO(tbroch): remove read of calibration below once instantiation of INA
        # controls resolves that there is only one device for many controls.
        # Currently it is possible to overflow and adjust calibration say for the
        # milliwatts but be  unaware of the change for the milliamps calculations as
        # each control has a separate instance of ina219 object and therefore a
        # private copy of the calibration register.
        self._read_reg("cal")

        # (b/199008947) INA231 may have the CVRF (Conversion Ready Flag) bit set
        # somewhere prior to this point, and we cannot be sure whether the
        # calculation was overflowed if the bit is not consumed before we rewrite
        # the calib register. Adding a CNVR read to ensure the bit is cleared.
        self._read_cnvr()

        # None value means this is the first calibration after the reset, so we
        # attempt the highest resolution (maximum calibration value).
        # Otherwise, we just use the cached value.
        # TODO(b/206879189): implement the bounce-back mechanism so the calibration
        # value can gradually climb up when it's safe to.
        if self._calib_reg is None:
            self._calib_reg = self.MAX_CALIB

        self._write_reg("cal", self._calib_reg)
        is_ovf = self._get_next_ovf()

        while is_ovf:
            if self._calib_reg == self.MIN_CALIB:
                raise Ina2xxError("Failed to calibrate for lowest precision")
            self._calib_reg = (self._calib_reg >> 1) & self.MAX_CALIB
            self._logger.debug("writing calibrate to 0x%04x" % (self._calib_reg))
            self._write_reg("cal", self._calib_reg)
            is_ovf = self._get_next_ovf()

    def _Set_ez_config(self, _unused):
        """Set the config register to be 'low_power'.

        low_power is a short-hand on the INA chips in servod to say
        - high sample rate
        - high resolution
        - hardware averaging
        """
        self._write_reg("cfg", "low_power")

    def _get_shunt_millivolts(self):
        """Retrieve shunt voltage measurement for ADC.

        Returns:
          float of shunt voltage in millivolts.

        Raises:
          Ina2xxError: if shunt voltage overflowed.
        """
        vshunt_reg = self._read_reg("shv")
        logging.debug("shv = 0x%x", vshunt_reg)

        # its negative ... two's complement
        if vshunt_reg & 0x8000:
            vshunt_reg = ~vshunt_reg & self.SHV_MASK
            vshunt_reg += 1 << self.SHV_OFFSET
            vshunt_reg *= -1
            logging.debug("shv = 0x%04x after negate", vshunt_reg)

        if abs(vshunt_reg) >= self.SHV_MASK:
            raise Ina2xxError("vshunt overflow 0x%04x" % vshunt_reg)

        vshunt_reg = vshunt_reg >> self.SHV_OFFSET
        return vshunt_reg * self.SHV_UV_PER_LSB / 1000.0

    def _Get_shuntmv(self):
        """Retrieve shunt voltage measurement for ADC in millivolts.

        Returns:
          float of shunt voltage in millivolts.
        """
        return self._get_shunt_millivolts()

    def _get_milliamps_calc(self):
        """Retrieve current measurement for ADC in milliamps by calculation.

        Calculation is I = Vshunt / Rsense

        Returns:
          float of current in milliamps
        """

        vshunt_mv = self._get_shunt_millivolts()
        logging.debug("vshunt_mv = %2.2f", vshunt_mv)
        return vshunt_mv / self._rsense

    def _wake(self):
        """Wake up the INA219 adc from sleep."""

        if self._cfg_mode is None or (self._cfg_mode != self.CFG_MODE_CONT):
            self._set_cfg_mode(self.CFG_MODE_CONT)

    def _sleep(self):
        """Place device in low-power ( no measurement state )."""

        if self._cfg_mode is None or (self._cfg_mode != self.CFG_MODE_SLEEP):
            self._reset()
            self._set_cfg_mode(self.CFG_MODE_SLEEP)

    def _set_cfg_mode(self, mode):
        """Set the configuration mode of the INA219.

        Setting the configuration mode allows device to operate in different modes.
        Presently only plan to implemented sleep & continuous.  By default, the
        device powers on in continuous mode.

        Args:
          mode: integer value to write to configuration register to change the mode.
        """

        cfg_reg = self._read_reg("cfg")
        self._write_reg("cfg", (cfg_reg & ~self.CFG_MODE_MASK) | mode)

        self._cfg_mode = mode
