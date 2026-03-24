# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Access to Microchip PAC1934.

Quad-Channel, High-Side Measurement, Shunt and Bus Voltage Monitor
with i2c Interface.
"""
import time

from servo.drv import bit_util
from servo.drv import ina2xx


class Pac1934Error(ina2xx.Ina2xxError):
    """Pac1934 error class."""


class pac1934(ina2xx.ina2xx):
    """Object to access drv=pac1934 controls."""

    BUSV_MV_OFFSET = 0
    # In millivolts.
    BUSV_MAX = 32000.0

    # These are the values used to determine whether values are signed
    NEG_PWR_UNI = 0x0
    NEG_PWR_BIP = 0x1

    # The exponents of 2 of the different calculation denominators.
    VBUS_DEN_EXP = CUR_DEN_EXP = 16
    PWR_DEN_EXP = 28

    # maximum value of power output register. The register is a 4 byte register
    # with 3 unused bits.
    PWR_MAX = 0xFFFFFFFF >> 3
    # 4 lsb on the power register are not real data.
    PWR_MW_OFFSET = 4
    # power is a 28 bit 'signed' number, so we can check the 28th bit to check
    # the sign.
    PWR_SIGN = 1 << 27

    # accumulator power is a 48 bit 'signed' number potentially
    PWR_ACCUM_SIGN = 1 << 47

    # Time after the refresh command when the signal is stable.
    REFRESH_STABLE_S = 1.0 / 1000  # 1ms.

    # Resolutions of voltage and current conversion. If a chip supports high
    # resolution measurements, implement the _[Set|Get]_resolution in a subclass
    # and use these constants to know which resolution is requested.
    REGULAR_RESOLUTION = 0
    HIGH_RESOLUTION = 1

    # Bit 3 on the register
    CTRL_REG_ALERT_PIN_OFFSET = 3

    # Maps to handle sampling states.
    SAMPLE_BIT_MAP = {8: 0b11, 64: 0b10, 256: 0b01, 1024: 0b00}
    BIT_SAMPLE_MAP = {v: k for k, v in SAMPLE_BIT_MAP.items()}
    SAMPLING_RATES = list(SAMPLE_BIT_MAP.keys())

    # How many bits to shift to the right to get the sample rate bits from reg.
    SAMPLING_SHIFT = 6
    # Mask that only has 1s on the sampling bit positions.
    SAMPLING_MASK = 0xC0

    def _drv_init(self):
        """Driver specific initializer."""
        super()._drv_init()
        # Pre-calculate a few important values.
        # full scale current and power full scale range
        self._fsc = self._pwr_fsr = None
        self._busv_fsr = self.BUSV_MAX
        if self._rsense:
            # in milliamps. Adapted from Equation 4-3 in datasheet.
            self._fsc = 100.0 / self._rsense
            # in milliwatts. Adapted from Equation 4-5 in datasheet.
            self._pwr_fsr = self.BUSV_MAX * self._fsc

    def busv_fsr(self):
        """Retrieve the bus voltage full scale range (fsr) signed."""
        _unused, v_signed = self._signed()
        return self._busv_fsr, v_signed

    def pwr_fsr(self):
        """Retrieve pwr full scale range (fsr) and signed."""
        c_signed, v_signed = self._signed()
        return self._pwr_fsr, c_signed or v_signed

    def fsc(self):
        """Retrieve full scale current (fsc) and signed."""
        c_signed, _unused = self._signed()
        return self._fsc, c_signed

    def _refresh(self, clear=False):
        """Write 0x0 to refresh register to get refreshed values.

        Args:
          clear: bool, whether to clear accum. uses refresh-v reg if not |clear|
                 else refresh

        """
        reg = "refresh" if clear else "refresh_v"
        self._write_reg(reg, 0x0, refresh=None)
        time.sleep(self.REFRESH_STABLE_S)

    def _Set_ez_config(self, _unused):
        """Configure for standard usage on pac family.

        on the PAC family, standard usage means
        - high sample rate
        - high resolution
        - turning off slow-pin
        - resetting the accumulators
        """
        self._set_ctrl("slow_enabled", "no")
        self._set_ctrl("res", "high")
        self._set_ctrl("signed", "yes")
        self._set_ctrl("samples", "highest")
        self._refresh(clear=True)

    def _Set_resolution(self, _unused):
        """The resolution is always the same on pac1934."""
        pass

    def _Get_resolution(self):
        """The resolution is always the same on pac1934."""
        return self.REGULAR_RESOLUTION

    def _Get_samples(self):
        """Return current samples per second setting."""
        cv = self._read_reg("ctrl_act", refresh=None)
        smode = bit_util.extract_bitfield(cv, 0x3, self.SAMPLING_SHIFT)
        return self.BIT_SAMPLE_MAP[smode]

    def _Set_samples(self, value):
        """Set |value| samples per second.

        Args:
          value: one of [8, 64, 256, 1024]

        Raises:
          Pac1934Error: if |value| is not a known sampling rate
        """
        if value not in self.SAMPLING_RATES:
            raise Pac1934Error("Unknown sampling rate %d" % value)
        smode = self.SAMPLE_BIT_MAP[value]
        cv = self._read_reg("ctrl", refresh=None)
        rv = bit_util.set_bitfield(cv, 0x3, self.SAMPLING_SHIFT, smode)
        self._write_reg("ctrl", rv)

    def _Get_slow(self):
        """Whether slow-mode is enabled via pin input on the pac1934."""
        cv = self._read_reg("ctrl_act", refresh=None)
        mode = bit_util.extract_bitfield(cv, 0x1, self.CTRL_REG_ALERT_PIN_OFFSET)
        return int(not bool(mode))

    def _Set_slow(self, value):
        """Configure whether to accept the pin input for slow mode or ignore it.

        This is implemented by reconfiguring the SLOW/ALERT input to ALERT and thus
        ignore SLOW signal.

        Args:
          value: 0 means slow pin will be ignored, anything else means it will
                 be accepted
        """
        cv = self._read_reg("ctrl", refresh=None)
        if value:
            mode = 0
        else:
            mode = 1
        rv = bit_util.set_bitfield(cv, 0x1, self.CTRL_REG_ALERT_PIN_OFFSET, mode)
        self._write_reg("ctrl", rv)

    @property
    def _neg_pwr_current_offset(self):
        """Returns of offset for the channel's CHn_BIDI bank."""
        return 7 - self._channel

    @property
    def _neg_pwr_voltage_offset(self):
        """Returns of offset for the channel's CHn_BIDV bank."""
        return 3 - self._channel

    def _signed(self):
        """Whether current and voltage readings are signed."""
        cv = self._read_reg("neg_pwr_act")
        # 0x1 is used as the information is only in 1 bit.
        v_mode = bit_util.extract_bitfield(cv, 0x1, self._neg_pwr_voltage_offset)
        c_mode = bit_util.extract_bitfield(cv, 0x1, self._neg_pwr_current_offset)
        c_signed = c_mode == self.NEG_PWR_BIP
        v_signed = v_mode == self.NEG_PWR_BIP
        return c_signed, v_signed

    def _Set_signed(self, value):
        """Set the ADC to be signed."""
        # Make sure to reduce |value| to the write write mask
        sbit = self.NEG_PWR_BIP if value else self.NEG_PWR_UNI
        cv = self._read_reg("neg_pwr_act")
        # 0x1 is used as the information is only in 1 bit.
        rv = bit_util.set_bitfield(cv, 0x1, self._neg_pwr_voltage_offset, sbit)
        rv = bit_util.set_bitfield(rv, 0x1, self._neg_pwr_current_offset, sbit)
        self._write_reg("neg_pwr", rv)

    def _Get_signed(self):
        """Report whether the values are signed or unsigned."""
        c_signed, v_signed = self._signed()
        if c_signed != v_signed:
            self._logger.debug(
                "Voltage signed: %r, Current signed: %r, will sync.", v_signed, c_signed
            )
            self._Set_signed(1)
            c_signed, v_signed = self._signed()
            if c_signed != v_signed:
                raise Pac1934Error(
                    "Failed to sync voltage and current to both be signed."
                )
        # It's sufficient to report one, since we made sure it's the same one.
        return int(c_signed)

    def _read_reg(self, name, refresh="v"):
        """Specify whether we need to call refresh (and what kind) before read.

        Args:
          name: register name
          refresh: one of 'v', 'clear' or None

        Returns:
          int, content from the |name| register
        """
        if refresh is not None:
            self._refresh(clear=refresh == "clear")
        return super()._read_reg(name)

    def _write_reg(self, name, value, refresh="v"):
        """Specify whether we need to call refresh (and what kind) after write.

        Args:
          name: register name
          value: int, content to write to register
          refresh: one of 'v', 'clear' or None
        """
        super()._write_reg(name, value)
        if refresh is not None:
            self._refresh(clear=refresh == "clear")

    @property
    def millivolts_per_lsb(self):
        """Bus voltage mv per lsb.

        Returns:
          float of bus voltage per lsb in millivolts
        """
        busv_fsr, signed = self.busv_fsr()
        # We need to divide the max bus voltage by the denominator matching the
        # current mode (signed, or unsigned).
        d = 1 << self.VBUS_DEN_EXP
        # If the voltage is signed, |signed| will return True, and we need to shift
        # back.
        d = d >> int(signed)
        return busv_fsr / float(d)

    @property
    def milliamps_per_lsb(self):
        """Calculate milliamps per least significant bit of the current register.

        Returns:
          float of current per lsb value in milliamps.
        """
        fsc, signed = self.fsc()
        # We need to divide the full scale current by the denominator matching the
        # current mode (signed, or unsigned).
        d = 1 << self.CUR_DEN_EXP
        # If the current is signed, this will return true, and we need to shift
        # back.
        d = d >> int(signed)
        # Adopted from Equation 4-4 in datasheet.
        lsb = fsc / float(d)
        self._logger.debug("lsb = %f" % lsb)
        return lsb

    @property
    def milliwatts_per_lsb(self):
        """Calculate milliwatts per least significant bit of the power register.

        Returns:
          float of power per lsb value in milliwatts.
        """

        pwr_fsr, signed = self.pwr_fsr()
        # We need to divide the full scale power by the denominator matching the
        # power mode (signed, or unsigned).
        d = 1 << self.PWR_DEN_EXP
        # The power is signed if either of the two components are signed.
        # Adopted from Equation 4-6 and 4-7 in datasheet.
        d = d >> int(signed)
        # We also need to further divide the lsb by 1000. This is because
        # we're in ma * mv calculations.
        lsb = pwr_fsr / float(d) / 1000.0
        self._logger.debug("lsb = %f" % lsb)
        return lsb

    def _Get_accum_milliwatts(self):
        """Retrieve power by reading accumulator and accumulator count.

        Note: this does not clear them, but merely reads them out.

        Returns:
          milliwatts, but using accumulator & count i.e. avg since last clear
        """
        acc_pwr = self._read_reg("acc_pwr")
        if acc_pwr & self.PWR_ACCUM_SIGN:
            self._logger.debug("Power accumulator may be signed %x", acc_pwr)
            acc_pwr -= self.PWR_ACCUM_SIGN << 1
            self._logger.debug("power accumulator %x after negation", acc_pwr)
        # Do not refresh again to avoid acc_count being different
        acc_count = self._read_reg("acc_count", refresh=None)
        # Integer division as we want it to mimic the output of a normal pwr
        # register.
        return self._Get_milliwatts(raw_pwr=acc_pwr // acc_count)

    def _Set_acc_clear(self, _unused):
        """Clear the accumulator values (and refresh)."""
        self._refresh(clear=True)
