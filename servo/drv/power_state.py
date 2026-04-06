# Copyright 2014 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import time

import grpc

from servo.common.grpc_client import GrpcClient
from servo.common.proto import driver_grpc
from servo.drv import hw_driver


class PowerStateDriver(hw_driver.HwDriver):
    """Abstract superclass to provide board-specific power operations.

    This driver handles a single control with these settings:
      * 'off' - This must power the DUT off, regardless of its
        current state.  Note:  On some boards, the only way to turn
        the DUT back on is with the 'on' setting, below.
      * 'on' - This powers the DUT on in normal (not recovery) mode.
        The behavior of this setting is undefined if the DUT is not
        currently powered off.
      * 'rec' - Equivalent to 'on', except that the DUT boots in
        recovery mode.
      * 'fastboot' - Equivalent to 'on', except that the DUT boots in
        fastboot mode.
      * 'reset' - Equivalent to 'off' followed by 'on'.
        Additionally, the EC will be reset as by the 'cold_reset'
        signal.
      * 'rec_force_mrc' - Equivalent to 'rec', except that upon bootup,
        the DUT will perform memory training.

    Actual implementation of the required behaviors is delegated to
    the methods `_power_off()` and `_power_on()`, which must be
    implemented in a subclass.

    """

    _STATE_OFF = "off"
    _STATE_ON = "on"
    _STATE_REC_MODE = "rec"
    _STATE_FASTBOOT = "fastboot"
    _STATE_RESET_CYCLE = "reset"
    # TODO(b/232990406): remove cr50_reset once all scripts have been updated.
    _STATE_CR50_RESET = "cr50_reset"
    _STATE_GSC_RESET = "gsc_reset"
    _STATE_REC_FORCE_MRC = "rec_force_mrc"
    _STATE_WARM_RESET = "warm_reset"

    REC_ON = "on"
    REC_OFF = "off"
    REC_ON_FORCE_MRC = "force_mrc"

    def _drv_init(self):
        """Driver specific initializer."""
        super()._drv_init()

        # Create a gRPC channel to the specified host and port
        grpc_data_host, grpc_data_port = self.grpc_data_addr
        channel = GrpcClient.create_grpc_channel(grpc_data_host, grpc_data_port)
        self._logger.debug("Connect to grpc server of data.....")
        self._data_client = driver_grpc.DriverService(channel)
        self._reset_hold_time = float(self._params.get("reset_hold", 0.5))
        self._reset_recovery_time = float(self._params.get("reset_recovery", 5.0))
        # Use ecrst pulse for ccd devices if running `ecrst off` is unreliable
        # with the EC in reset
        self._ccd_pulse_cold_reset = self._params.get(
            "ccd_pulse_cold_reset", ""
        ) == "yes" and "ccd" in self._servod_get("servo_class")

    def _cold_reset_set_to_gsc_reset(self):
        """Returns True if cold_reset will reset the GSC."""
        if not self._servod_has_control("cold_reset_select"):
            return False
        cold_reset = self._servod_get("cold_reset_select")
        if cold_reset == "gsc_reset":
            return True
        # c2d2 setups only have access to the GSC reset signal. The default
        # reset will reset the GSC.
        return (
            "c2d2" in self._servod_get("servo_type")
            and cold_reset == "default_cold_reset"
        )

    def _reinitialize_interfaces(self, reason):
        """Reinitialize interfaces to recover from a USB reset.

        Args:
            reason: String identifying the cause of the reset (e.g. 'cold_reset')
        """
        # Wait long enough for usb to have dropped out
        time.sleep(0.3)
        # Attempt to reinitialize the device in case the device reenumerated quicker
        # than the polling resolution. By now, if the device did not reenumerate,
        # the Watchdog should be attempting to catch & reinitialize it.
        try:
            self._data_client.ReinitializeInterfaces()
        except grpc.RpcError as e:
            self._logger.info(
                "Ignoring expected gRPC error during ReinitializeInterfaces after %s: %s",
                reason,
                e,
            )
        except Exception as e:
            self._logger.info(
                "Ignoring expected error during ReinitializeInterfaces after %s: %s",
                reason,
                e,
            )

    def _cold_reset(self):
        """Apply cold reset to the DUT.

        This asserts, then de-asserts the 'cold_reset' signal.  The
        exact affect on the hardware varies depending on the board type.

        """
        # Use gsc_ecrst_pulse for cold reset if the system requested it or
        # the cold_reset signal resets the GSC.
        if self._ccd_pulse_cold_reset or self._cold_reset_set_to_gsc_reset():
            return self._ccd_cold_reset()
        self._servod_set("cold_reset", "on")
        self._reinitialize_interfaces("cold_reset:on")
        time.sleep(self._reset_hold_time)
        self._servod_set("cold_reset", "off")
        self._reinitialize_interfaces("cold_reset:off")
        # After the reset, give the EC the time it needs to
        # re-initialize.
        time.sleep(self._reset_recovery_time)

    def _ccd_cold_reset(self):
        """Use the ccd cold reset signal to reset the dut.

        Some boards cannot reliably run `ecrst off` after `ecrst on`. Use
        `ecrst pulse` to ensure the device is released from reset.
        """
        # The ccd_cold_reset_pulse signal asserts and deasserts ecrst on its own
        self._servod_set("gsc_ecrst_pulse", "on")
        self._reinitialize_interfaces("gsc_ecrst_pulse:on")
        # After the reset, give the EC and CCD the time it needs to
        # re-initialize.
        time.sleep(self._reset_recovery_time)
        self._servod_set("gsc_ecrst_pulse", "off")
        self._reinitialize_interfaces("gsc_ecrst_pulse:off")
        time.sleep(self._reset_recovery_time)

    def _warm_reset(self):
        """Apply warm reset to the DUT.

        This asserts, then de-asserts the 'warm_reset' signal.  The
        exact affect on the hardware varies depending on the board type.

        """
        self._servod_set("warm_reset", "on")
        self._reinitialize_interfaces("warm_reset:on")
        time.sleep(self._reset_hold_time)
        self._servod_set("warm_reset", "off")
        self._reinitialize_interfaces("warm_reset:off")
        # After the reset, give the EC the time it needs to
        # re-initialize.
        time.sleep(self._reset_recovery_time)

    def _power_off(self):
        """Power off the DUT.

        The DUT is required to be off at the end of this call,
        regardless of its previous state, provided that there is working
        EC and boot firmware.  There is no requirement for working OS
        software.

        Note:  After calling this method on some boards, the DUT can
        only be powered back on using the `power_on()` method.

        """
        raise NotImplementedError()

    def _power_on(self, rec_mode):
        """Force the DUT to power on.

        Behavior is undefined unless the DUT is already powered off,
        e.g. with a call to `_power_off()`.

        At power on, recovery mode is set as specified by the `rec_mode`
        parameter.

        When booting in recovery mode, the client is responsible for
        inserting USB boot media after this method returns.  This
        method is responsible for any delays required to make the DUT
        ready for media insertion after power on.

        Args:
          rec_mode: Setting of recovery mode to be applied at power on.

        """
        raise NotImplementedError()

    def _reset_cycle(self):
        """Force a power cycle using cold reset.

        After the call, the DUT will be powered on in normal (not
        recovery) mode; the call is guaranteed to work regardless of
        the state of the DUT prior to the call.  This call must use
        cold_reset to guarantee that the EC also restarts.

        """
        self._cold_reset()

    def _reset_gsc(self):
        """Reboot GSC and reset CCD.

        Reboot GSC and reset ccd to recover from the usb reset.
        """
        self._servod_set("gsc_reboot", "on")
        self._reinitialize_interfaces("gsc_reboot")

    def _set(self, statename):
        """Set power state according to `statename`."""
        if statename == self._STATE_OFF:
            self._power_off()
        elif statename == self._STATE_ON:
            self._power_on(self.REC_OFF)
        elif statename == self._STATE_REC_MODE:
            self._power_on(self.REC_ON)
        elif statename == self._STATE_FASTBOOT:
            self._power_on_fastboot()
        elif statename == self._STATE_RESET_CYCLE:
            self._reset_cycle()
        elif statename == self._STATE_CR50_RESET:
            self._logger.warn("%r is deprecated. Change to gsc_reset", statename)
            self._reset_gsc()
        elif statename == self._STATE_GSC_RESET:
            self._reset_gsc()
        elif statename == self._STATE_WARM_RESET:
            self._warm_reset()
        elif statename == self._STATE_REC_FORCE_MRC:
            self._power_on(self.REC_ON_FORCE_MRC)
        else:
            raise ValueError(
                "Invalid power_state setting: %r. Try one of "
                "%r, %r, %r, %r, %r, %r, %r, or %r."
                % (
                    statename,
                    self._STATE_ON,
                    self._STATE_OFF,
                    self._STATE_REC_MODE,
                    self._STATE_FASTBOOT,
                    self._STATE_RESET_CYCLE,
                    self._STATE_REC_FORCE_MRC,
                    self._STATE_WARM_RESET,
                    self._STATE_GSC_RESET,
                )
            )
