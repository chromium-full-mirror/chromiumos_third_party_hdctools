# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Access to Microchip PAC1954.

Quad-Channel, High-Side Measurement, Shunt and Bus Voltage Monitor
with i2c Interface.
"""

from servo.drv import bit_util
from servo.drv import ina2xx
from servo.drv import pac1934


class Pac1954Error(ina2xx.Ina2xxError):
    """Pac1954 error class."""


class pac1954(pac1934.pac1934):
    """Object to access drv=pac1954 controls."""

    BUSV_MV_OFFSET = 0
    # In millivolts.
    BUSV_MAX = 32000.0

    # These are the values used to determine whether values are signed
    # and whether the resolution is fsr/2.
    NEG_PWR_FSR_UNI = 0x0
    NEG_PWR_FSR_BIP = 0x1
    NEG_PWR_FSR_BIP_FSR2 = 0x2

    # Exponent for power denominator is 30 rather than 28 as before.
    PWR_DEN_EXP = 30

    # maximum value of power output register. The register is a 4 byte register
    # with 2 unused bits.
    PWR_MAX = 0xFFFFFFFF >> 2
    # 2 lsb on the power register are not real data.
    PWR_MW_OFFSET = 2
    # power is a 30 bit 'signed' number, so we can check the 30th bit to check
    # the sign.
    PWR_SIGN = 1 << 29

    # accumulator power is a 56 bit 'signed' number potentially
    PWR_ACCUM_SIGN = 1 << 55

    # How many bits to shift to the right to get the sample rate bits from reg.
    SAMPLING_SHIFT = 12
    # Mask that only has 1s on the sampling bit positions. Note: we only
    # use adaptive mode on this pac and ignore the bits always for non-adaptive
    # mode.
    SAMPLING_MASK = 0x3000

    def busv_fsr(self):
        """Retrieve the bus voltage full scale range (fsr)."""
        _unused, v_signed, _unused, v_fsr2 = self._signed_and_fsr()
        fsr = self._busv_fsr
        if v_signed and not v_fsr2:
            fsr = self._busv_fsr / 2.0
        return fsr, v_signed

    def pwr_fsr(self):
        """Retrieve pwr full scale range (fsr)."""
        c_signed, v_signed, c_fsr2, v_fsr2 = self._signed_and_fsr()
        fsr = self._pwr_fsr
        if c_signed or v_signed and not (c_fsr2 or v_fsr2):
            fsr = self._pwr_fsr / 2.0
        return fsr, c_signed or v_signed

    def fsc(self):
        """Retrieve full scale current (fsc)."""
        c_signed, _unused, c_fsr2, _unused = self._signed_and_fsr()
        fsr = self._fsc
        if c_signed and not c_fsr2:
            fsr = self._fsc / 2.0
        return fsr, c_signed

    # Define these masks as properties.
    @property
    def _neg_pwr_fsr_current_offset(self):
        """Returns of offset for the channel's CFG_VSn bank."""
        return 14 - 2 * self._channel

    @property
    def _neg_pwr_fsr_voltage_offset(self):
        """Returns of offset for the channel's CFG_VBn bank."""
        return 6 - 2 * self._channel

    def _signed_and_fsr(self):
        """Whether current and voltage readings are signed and use fsr/2."""
        cv = self._read_reg("neg_pwr_fsr_act")
        # 0x3 is used as the information is spread across 2 bits.
        v_mode = bit_util.extract_bitfield(cv, 0x3, self._neg_pwr_fsr_voltage_offset)
        c_mode = bit_util.extract_bitfield(cv, 0x3, self._neg_pwr_fsr_current_offset)
        v_signed = v_mode != self.NEG_PWR_FSR_UNI
        c_signed = c_mode != self.NEG_PWR_FSR_UNI
        v_fsr2 = v_mode == self.NEG_PWR_FSR_BIP_FSR2
        c_fsr2 = c_mode == self.NEG_PWR_FSR_BIP_FSR2
        return c_signed, v_signed, c_fsr2, v_fsr2

    def _Get_signed(self):
        """Whether the PAC is report signed values for current, voltage, power.

        Note: while this can be controlled individually, in servod we simplify this
        by saying that either both are signed, or neither. Since we keep signed
        and fsr/2 in sync, we just delegate this to resolution.

        Returns:
          0 if unsigned, or 1 if signed values are used
        """
        return self._Get_resolution()

    def _Set_signed(self, val):
        """Set signed to be |val| (true or false).

        Note: Since we keep signed and fsr/2 in sync, we just delegate this to
        resolution.
        """
        self._Set_resolution(val)

    def _Get_resolution(self):
        """Whether current and voltage are using fsr/2.

        Note: while this can be controlled individually, in servod we simplify this
        by saying either both are high res, or both are regular resolution.

        Returns:
          0 if regular resolution and 1 if high resolution

        Raises:
          Pac1954Error: when failing to set current and voltage both to fsr/2
        """
        _unused, _unused, c_fsr2, v_fsr2 = self._signed_and_fsr()
        # If they are not the same, make them the same. Bias towards high
        # resolution.
        if c_fsr2 != v_fsr2:
            cs = "using" if c_fsr2 else "not using"
            vs = "using" if v_fsr2 else "not using"
            self._logger.warning(
                "current %s fsr2 while bus voltage is %s fsr2. Setting "
                "both to use fsr2.",
                cs,
                vs,
            )
            self._Set_resolution(self.HIGH_RESOLUTION)
            _unused, _unused, c_fsr2, v_fsr2 = self._signed_and_fsr()
        if c_fsr2 != v_fsr2:
            raise Pac1954Error("Failed to synchronize current and voltage fsr2.")
        return int(c_fsr2)

    def _Set_resolution(self, val):
        """Set resolution to be |val| (high res or low res)."""
        # To turn on high res i.e. fsr2, we need to toggle the fsr2 bit and turn
        # off the signed bit i.e. it needs to be 10
        reg = "neg_pwr_fsr"
        cv = self._read_reg(reg)
        if val == self.HIGH_RESOLUTION:
            mode = self.NEG_PWR_FSR_BIP_FSR2
        else:
            mode = self.NEG_PWR_FSR_UNI
        # Write to both voltage & current here.
        rv = bit_util.set_bitfield(cv, 0x3, self._neg_pwr_fsr_current_offset, mode)
        rv = bit_util.set_bitfield(rv, 0x3, self._neg_pwr_fsr_voltage_offset, mode)
        # Lastly, check if we even need to write.
        if cv != rv:
            self._logger.debug("Writing 0x%x to %r", rv, reg)
            self._write_reg(reg, rv)
