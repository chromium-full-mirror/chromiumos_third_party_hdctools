# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Base class to provide access to Texas Instruments INA-based ADCs."""

from servo.drv import hw_driver


class BasePWRADCError(hw_driver.HwDriverError):
    """Error occurred accessing INA219."""


# pylint: disable=invalid-name
# servod drv identification follows this naming convention.
class basePWRADC(hw_driver.HwDriver):
    """Base ADC implementation for power measurements.

    Subclasses need to define the required properties at least or overwrite
    any functions if the actual ADC does not fit into this framework.
    Subclasses are free to add additional features the ADC might support e.g.
    INAs and reading shunt voltage values directly.

    """

    # NOTE: the following list of class defaults are used throughout the base
    # implementation. Each ADC has to define the values marked as None below.

    # sign bit of current output register
    CUR_SIGN = None
    # maximum value of current output register.
    CUR_MAX = None
    # maximum number of re-reads of current register to do before raising
    # exception because current reading is still saturated
    CUR_READ_RETRY = 10

    # maximum value of power output register.
    PWR_MAX = None

    # sign bit of the power output register.
    PWR_SIGN = None

    # offset of the power reading, in case some bits are unused.
    PWR_MW_OFFSET = 0

    # offset of the bus voltage reading, in case some bits are unused.
    BUSV_MV_OFFSET = 0

    def _drv_init(self):
        """Driver specific initializer.

        Required params:
          base_name: the symbolic name for this INA e.g. pp3300_wlan_dx
          subtype: string, used by get/set method of base class to decide
            how to dispatch request.  Examples are: millivolts, milliamps,
            milliwatts

        Optional params:
          rsense: float, sense resistor size for adc in ohms.  Needed to properly
                  compute current and power measurements. Mandatory on
                  `milliwatts` and `milliamps` subtype

        Raises:
          BasePWRADCError: if needed params are absent
        """
        super()._drv_init()
        self._base_name = self._params["base_name"]
        # Single channel ADCs can be thought of as running on channel 0.
        # Some ADCs might need this information to find pertinent bits on registers.
        self._channel = int(self._params.get("channel", 0))

        if "subtype" not in self._params:
            raise BasePWRADCError("Unable to find subtype param")
        subtype = self._params["subtype"]
        try:
            self._rsense = float(self._params["rsense"])
        except KeyError:
            if (subtype == "milliamps") or (subtype == "milliwatts"):
                raise BasePWRADCError("No sense resistor in params")
            self._rsense = None
        # base class
        self._reset()

    def _reset(self):
        """Reset object state when device is transitioned to certain modes."""
        # NOTE: overwrite in child class for desired reset behavior.
        pass

    def _reg_control_name(self, reg):
        """Helper to generate register servod control name.

        Args:
          reg: register name

        Returns:
          str, [self._base_name]_[reg]_reg
        """
        reg_control_name = "%s_%s_reg" % (self._base_name, reg)
        # TODO(b/275723447): remove this prefix string manipulation from driver
        if "." not in reg_control_name and self._params["interface_prefix"]:
            return self._params["interface_prefix"] + "." + reg_control_name
        return reg_control_name

    def _has_reg(self, reg):
        """Determine whether |reg| has a servod control associated with it.

        Args:
          reg: register name

        Returns:
          True, if this ADC control (identified by |self._base_name| has
          a register control for |reg|, False otherwise
        """
        return self._servod_has_control(self._reg_control_name(reg))

    def _read_reg(self, reg):
        """Retrieve output for |reg|.

        Note: function expects a hex formatted str output when calling
              the register control

        Args:
          reg: register name

        Returns:
          register output, cast to an int

        Raises:
          BasePWRADCError: if |reg| for this ADC control is unknown to servod
        """
        ctrl_name = self._reg_control_name(reg)
        if not self._has_reg(reg):
            raise BasePWRADCError(
                "Register %s for control %s unknown: %s"
                % (reg, self._base_name, ctrl_name)
            )
        return int(self._servod_get(ctrl_name), 16)

    def _write_reg(self, reg, value):
        """Write |value| to |reg|.

        Args:
          reg: register name
          value: int, value to write to register

        Raises:
          BasePWRADCError: if |reg| for this ADC control is unknown to servod
        """
        if not self._has_reg(reg):
            raise BasePWRADCError(
                "Register %s for control %s unknown" % (reg, self._base_name)
            )
        ctrl_name = self._reg_control_name(reg)
        self._servod_set(ctrl_name, value)

    def _set_ctrl(self, suffix, value):
        """Set the control |suffix| for |self._base_name| to |value|.

        Args:
          suffix: control name suffix e.g. 'res'
          value: servod value to pass to the control

        Raises:
          BasePWRADCError: if |self._base_name|_|suffix| is no servod control
        """
        ctrl_name = "%s_%s" % (self._base_name, suffix)
        if not self._servod_has_control(ctrl_name):
            raise BasePWRADCError("Control %r unknown." % ctrl_name)
        self._servod_set(ctrl_name, value)

    @property
    def millivolts_per_lsb(self):
        """Bus voltage mv per lsb. Required to be implemented in the subclass.

        Returns:
          float of bus voltage per lsb in millivolts
        """
        raise NotImplementedError()

    @property
    def milliamps_per_lsb(self):
        """Calculate milliamps per least significant bit of the current register.

        Returns:
          float of current per lsb value in milliamps.
        """
        raise NotImplementedError()

    @property
    def milliwatts_per_lsb(self):
        """Calculate milliwatts per least significant bit of the power register.

        Returns:
          float of power per lsb value in milliwatts.
        """
        raise NotImplementedError()

    def _Set_ez_config(self, _unused):
        """Go through routine to configure the ADC for common use-case."""
        # NOTE: subclass should implement this if they want to configure anything
        # for common users or dut-power automation

    def _Get_millivolts(self):
        """Retrieve voltage measurement for ADC in millivolts.

        Returns:
          float of potential in millivolts
        """
        busv = self._read_reg("busv") >> self.BUSV_MV_OFFSET
        millivolts = busv * self.millivolts_per_lsb
        if millivolts >= self.BUSV_MAX:
            self._logger.error(
                "bus voltage measurement exceeded maximum %x", millivolts
            )
        return millivolts

    def _Get_milliamps(self):
        """Retrieve current measurement for ADC in milliamps from current register.

        Note: on INA type ADCs may trigger calibration which will increase latency.
        This calibration occurs when math overflow is detected from the OVF bit in
        the BUSV register.  If OVF asserts, software will attempt to adjust the
        calibration register until overflow is gone.

        Returns:
          float of current in milliamps
        """
        milliamps_per_lsb = self.milliamps_per_lsb
        raw_cur = self._read_reg("cur")
        if raw_cur & self.CUR_SIGN:
            self._logger.debug("current may be signed %x" % raw_cur)
            raw_cur -= self.CUR_SIGN << 1
            self._logger.debug("current %x after negation", raw_cur)
        if raw_cur == self.CUR_MAX:
            self._logger.error("current saturated %x", raw_cur)
        return raw_cur * milliamps_per_lsb

    def _Get_milliwatts(self, raw_pwr=None):
        """Retrieve power measurement for ADC in milliamps from power register.

        Note may trigger calibration which will increase latency

        Args:
          raw_pwr: if an ADC supports accumulation, the accumulator/count reading
                   can be fed in here rather than reading the pwr register directly

        Returns:
          float of power in milliwatts

        Raises:
          AssertionError: when power is saturated.
        """

        # call first to force compulsory calibration
        milliwatts_per_lsb = self.milliwatts_per_lsb
        if raw_pwr is None:
            raw_pwr = self._read_reg("pwr") >> self.PWR_MW_OFFSET
            if raw_pwr & self.PWR_SIGN:
                self._logger.debug("power may be signed %x", raw_pwr)
                raw_pwr -= self.PWR_SIGN << 1
                self._logger.debug("power %x after negation", raw_pwr)
        if raw_pwr == self.PWR_MAX:
            self._logger.error("power saturated %x", raw_pwr)
        return raw_pwr * milliwatts_per_lsb
