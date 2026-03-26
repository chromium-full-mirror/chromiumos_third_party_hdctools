# Copyright 2018 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Servod power measurement module."""

import logging
import os
import re
import threading
import time

from measurement_tools.utils import stats_manager
from measurement_tools.utils import timelined_stats_manager
from servo.core import client


SAMPLE_TIME_KEY = "Sample_msecs"

# Default sample rate to query ec for battery power consumption
DEFAULT_VBAT_RATE = 60
# Default sample rate to query accumulator ADCs. Since these support
# accumulation and averaging, they can be queried less frequently.
# b/238674542: Make accum rate more aggressive to secure at least one sample
# for an 1-minute measurement cycle.
DEFAULT_ADC_ACCUM_RATE = 30
# Default sample rate to query ADCs for power consumption
DEFAULT_ADC_RATE = 1

# Powerstate name used when no powerstate is known. The 'default' alias is
# added to make it clear on modules that use this as a library e.g. dut_power,
# that this is the 'default'.
DEFAULT_POWERSTATE = UNKNOWN_POWERSTATE = "S?"


# List of known power states
POWERSTATES = ["S0", "S0ix", "S3", "S5", "G3"]

# Board name to use when no board name provided, or querying it fails
# First attempt to read it from the environment before defaulting to unknown
DEFAULT_BOARD = os.environ.get("BOARD", "unknown")


class PowerTrackerError(Exception):
    """Error class to invoke on PowerTracker errors."""


class NoSourceError(PowerTrackerError):
    """Specific error when no power data source was setup successfully."""


class ServodPowerTracker(threading.Thread):
    """Threaded PowerTracker using servod as power number source.

    This PowerTracker uses servod to sample all |_ctrls| at |_rate|.

    Attributes:
      title: human-readable title of the PowerTracker
    """

    # Note: the only suffixes used for us are '[avg_]rail_name[_avg]_mw'
    # Refresher when reading this
    # - ?: indicates we don't care to retrieve those match groups
    # - ?P<rail>: ensures we can access the group by name
    # - +?: ensures we do a non-greedy match so that we don't match 'avg' in the
    #       rail group
    RAIL_RE = re.compile(r"(?:avg_)?(?P<rail>[\w._]+?)(?:_avg)?_mw")

    def __init__(
        self,
        servo_client,
        ctrls,
        stop_signal,
        sample_rate,
        tag="",
        title="unnamed",
        suffix="mw",
    ):
        """Initialize ServodPowerTracker by making servod proxy & storing ctrls.

        Args:
          servo_client: ServoClient instance
          ctrls: list of servod ctrls to collect power numbers
          stop_signal: Event object to flag when to stop measuring power
          sample_rate: rate for collecting samples for |ctrls|
          tag: string to prepend to summary & raw rail file names
          title: human-readable title of the PowerTracker
          suffix: what metric is being measured (mw, ma, mv)
        """
        super().__init__()
        self._sclient = servo_client
        self._ctrls = ctrls
        self._stop_signal = stop_signal
        self._rate = sample_rate
        if not title.endswith(suffix):
            title = "%s (%s)" % (title, suffix)
        self.title = title
        self._stats = timelined_stats_manager.TimelinedStatsManager(
            smid=tag, title=title, rate=sample_rate
        )
        self._logger = logging.getLogger(type(self).__name__)
        # Flag to indicate whether to skip the first reading. This is used
        # for trackers that run averaging, and the first reading is used to reset
        # the counters.
        self._skip_first = False
        self.daemon = True
        self._sample_data = []
        self._previous_sample_data = []

    @property
    def empty(self):
        """Whether the tracker has any controls."""
        return len(self._ctrls) == 0

    def _rail_name(self, ctrl_name):
        """Strip suffix from rail to return core rail name.

        Args:
          ctrl_name: str, servod control name for a rail's data e.g. pp3300_h1_mw
        """
        return self.RAIL_RE.match(ctrl_name).group("rail")

    @property
    def rails(self):
        """Return all rail-names that this tracker uses."""
        return [self._rail_name(c) for c in self._ctrls]

    def remove_rail(self, rail):
        """Remove the servod control that would query |rail|.

        Note: if |rail| is not in this tracker, this is effectively a noop

        Args:
          rail: str, rail name to remove e.g. pp3300_h1
        """
        # Remove by just rebuilding the list of ctrls.
        self._ctrls = [c for c in self._ctrls if self._rail_name(c) != rail]

    def prepare(self, fast=False, powerstate=UNKNOWN_POWERSTATE):
        """Do any setup work right before number collection begins.

        Args:
          fast: flag to indicate if pre-run work should be "fast" (e.g. no UART)
          powerstate: powerstate to allow for conditional preps based on powerstate
        """

    def verify(self):
        """Verify by trying to query all ctrls once.

        Raises:
          PowerTrackerError: if verification failed
        """
        try:
            self._sclient.set_get_all(self._ctrls)
        except client.ServoClientError as e:
            msg = "Failed to test servod commands. Tested: %s" % str(self._ctrls)
            raise PowerTrackerError(msg) from e

    def run(self):
        """run power collection thread by querying all |_ctrls| at |_rate| rate.

        Query all |_ctrls| and take timestamp once at the start of |_rate| interval.
        """
        skip = self._skip_first
        while not self._stop_signal.is_set():
            if not skip:
                temp_sample_data = []
                sample_tuples, duration_ms = self._sample_ctrls(self._ctrls)
                for domain, sample in sample_tuples:
                    # temp_stats.add_sample(domain, sample)
                    temp_sample_data.append((domain, sample))
                self._stats.add_samples(sample_tuples)
                self.set_sample_data(temp_sample_data)
            else:
                duration_ms = 0
                self._logger.debug("ready bit not set, skipping sample round")
            self._stop_signal.wait(max(self._rate - (duration_ms / 1000), 0))
            # We only skip the first reading if requested, and no others.
            skip = False

    def set_sample_data(self, sample_data):
        """Set the value to _sample_data"""
        self._sample_data = sample_data

    def get_sample_data(self):
        """Passed the collected data which will use for the visualization

        If the _sample_data is empty, it means that we have not got the new data yet,
        reuse the previous sample data,
        otherwise, pass the new sample data and update previous sample data

        Returns:
          The return object contains the power information
        """
        if not self._sample_data:
            return self._previous_sample_data
        self._previous_sample_data = self._sample_data
        return self._sample_data

    def clean_sample_data(self):
        """Clean the _sample_data containers when the data has been passed"""
        self._sample_data = []

    def _sample_ctrls(self, ctrls):
        """Helper to query all servod ctrls, and create (name, value) tuples.

        Args:
          ctrls: list of servod ctrls to sample

        Returns:
          tuple (sample_tuples, duration_ms)
                 sample_tuples: a list of (rail-name, value) tuples
                                value is a power reading on success, NaN on failure
                 duration_ms: time it took to collect the sample, in milliseconds
        """
        start = time.time()
        rails = [self._rail_name(c) for c in ctrls]
        try:
            samples = self._sclient.set_get_all(ctrls)
        except client.ServoClientError:
            self._logger.warning(
                "Attempt to get commands: %s failed. Recording them all as NaN.",
                ", ".join(ctrls),
            )
            samples = [float("nan")] * len(ctrls)
        duration_ms = (time.time() - start) * 1000
        sample_tuples = list(zip(rails, samples))
        sample_tuples.append((SAMPLE_TIME_KEY, duration_ms))
        return (sample_tuples, duration_ms)

    def process_measurement(self, tstart=None, tend=None):
        """Process the measurement by calculating stats.

        Args:
          tstart: first timestamp to include. Seconds since epoch
          tend: last timestamp to include. Seconds since epoch

        Returns:
          StatsManager object containing info from the run
        """
        self._stats.trim_samples(tstart, tend)
        self._stats.calculate_stats()
        return self._stats

    def __str__(self):
        """Helper to print out the tracker name."""
        return self.title


class HighResServodPowerTracker(ServodPowerTracker):
    """High Resolution implementation of ServodPowerTracker.

    The difference here is that while ServodPowerTracker sleeps if it finishes
    before |_rate| is up, HighResServodPowerTracker tries to collect as many
    samples as it can during |_rate| before recording the mean of those samples
    as one data point.
    """

    def run(self):
        """run power collection thread.

        Query all |_ctrls| as much as possible during |_rate| interval before
        reporting the mean of those samples as one row of data. Timestamps are
        computed based on the last measurement added.
        """
        start_time = time.time()
        temp_stats = None
        last_row = 0
        while not self._stop_signal.is_set():
            # Discarding the duration_ms since the difference between the current
            # time and the start time are being used.
            sample_tuples, _unused = self._sample_ctrls(self._ctrls)
            if temp_stats is None:
                temp_stats = stats_manager.StatsManager()
            temp_sample_data = []

            for domain, sample in sample_tuples:
                temp_stats.add_sample(domain, sample)
                temp_sample_data.append((domain, sample))
            self.set_sample_data(temp_sample_data)

            # If the last timestamp would have been in a new row on the table
            # log the current set of measurements as the next row.
            current_row = int((time.time() - start_time) / self._rate)
            if last_row != current_row:
                last_row = current_row
                if temp_stats is not None:
                    self._record_mean_samples(temp_stats)
                    temp_stats = None
        # Record the last row of data
        if temp_stats is not None:
            self._record_mean_samples(temp_stats)

    def _record_mean_samples(self, temp_stats):
        """Converts a StatsManager object into a row of averaged measurements.

        Args:
        temp_stats: StatsManager object which may contain a collection
                    of rail measurements.
        """
        temp_stats.calculate_stats()
        temp_summary = temp_stats.get_summary()
        samples = [
            (measurement, summary["mean"])
            for measurement, summary in temp_summary.items()
        ]
        self._stats.add_samples(samples)

    def process_measurement(self, tstart=None, tend=None):
        """Process the measurement by calculating stats.

        Args:
          tstart: first timestamp to include. Seconds since epoch
          tend: last timestamp to include. Seconds since epoch

        Returns:
          StatsManager object containing info from the run
        """
        # Each data point is the mean of all samples taken during |_rate| interval,
        # and the timestamp of the data point is taken at the end of the |_rate|
        # interval. To ensure that we keep all the data points with at least half of
        # their samples within [tstart, tend], add padding = |_rate| / 2.
        # tstart: add the padding to discard data points with less than half samples
        #         within [tstart, tend].
        # tend: add the padding to avoid losing data points that have at least half
        #       of samples within [tstart, tend].
        self._stats.trim_samples(tstart, tend, self._rate / 2)
        self._stats.calculate_stats()
        return self._stats


class OnboardADCPowerTracker(HighResServodPowerTracker):
    """Off-the-shelf PowerTracker to measure onboard ADCs through servod."""

    def __init__(
        self, servo_client, stop_signal, cfilter, sample_rate=DEFAULT_ADC_RATE
    ):
        """Init by finding onboard ADC ctrls."""
        super().__init__(
            servo_client=servo_client,
            ctrls=[],
            stop_signal=stop_signal,
            sample_rate=sample_rate,
            tag="onboard",
            title="Onboard ADC",
        )
        self._ctrls = cfilter(self._sclient.get("power_rails"))
        if not self._ctrls:
            raise PowerTrackerError("No onboard ADCs found.")
        self._logger.debug(
            "Following power rail commands found: %s", ", ".join(self._ctrls)
        )
        self._ez_cfg_ctrls = cfilter(self._sclient.get("adc_ez_config_ctrls"))

    def prepare(self, fast=False, powerstate=UNKNOWN_POWERSTATE):
        """prepare onboard ADC measurement by configuring ADCs for powerstate."""
        cfg_ctrls = ["%s:on" % cfg_cmd for cfg_cmd in self._ez_cfg_ctrls]
        try:
            self._sclient.set_get_all(cfg_ctrls)
        except client.ServoClientError:
            self._logger.warning("Power rail configuration failed. Details in DEBUG.")
            self._logger.debug("Controls issued: %s", " ".join(cfg_ctrls))


class OnboardADCAccumPowerTracker(ServodPowerTracker):
    """Off-the-shelf PowerTracker to measure onboard ADCs with accumulator."""

    def __init__(
        self, servo_client, stop_signal, cfilter, sample_rate=DEFAULT_ADC_ACCUM_RATE
    ):
        """Init by finding onboard ADC accum ctrls."""
        title = "Onboard ADC (w/ accum)"
        super().__init__(
            servo_client=servo_client,
            ctrls=[],
            stop_signal=stop_signal,
            sample_rate=sample_rate,
            tag="onboard.accum",
            title=title,
        )
        self._ctrls = cfilter(self._sclient.get("avg_power_rails"))
        self._clear_ctrls = cfilter(self._sclient.get("accum_clear_ctrls"))
        if not self._ctrls or not self._clear_ctrls:
            raise PowerTrackerError("No support for accum rails detected.")
        self._logger.debug(
            "Following avg power rail commands found: %s", ", ".join(self._ctrls)
        )
        self._ez_cfg_ctrls = cfilter(self._sclient.get("adc_ez_config_ctrls"))
        # Pre-process the accumulator clearing controls so they can be issued
        # at once.
        self._clear_ctrls = ["%s:yes" % c for c in self._clear_ctrls]
        # The first reading on these has stale, old data. It needs to ignore the
        # first reading, and only start at the second reading.
        self._skip_first = True
        # Filter out the right controls

    def prepare(self, fast=False, powerstate=UNKNOWN_POWERSTATE):
        """prepare onboard ADC measurement by configuring ADCs for powerstate."""
        # Note: |ez_config| on accumulator supporting ADCs automatically
        # clears the accumulators.
        cfg_ctrls = ["%s:on" % cfg_cmd for cfg_cmd in self._ez_cfg_ctrls]
        try:
            self._sclient.set_get_all(cfg_ctrls)
        except client.ServoClientError:
            self._logger.warning("Power rail configuration failed. Details in DEBUG.")
            self._logger.debug("Controls issued: %s", " ".join(cfg_ctrls))

    def _clear_accum(self):
        """Issue controls to clear all the accumulators on the ADCs."""
        self._sclient.set_get_all(self._clear_ctrls)

    def _sample_ctrls(self, ctrls):
        """Overwrite the base implementation to clear accumulator after reading."""
        ret = super()._sample_ctrls(ctrls)
        self._clear_accum()
        return ret


class ECPowerTracker(ServodPowerTracker):
    """Off-the-shelf PowerTracker to measure power-draw as seen by the EC."""

    def __init__(
        self, servo_client, stop_signal, cfilter, sample_rate=DEFAULT_VBAT_RATE
    ):
        """Init EC power measurement by setting up ec 'vbat' servod control."""
        self._ec_cmd = "ppvar_vbat_mw"
        self._avg_ec_cmd = "avg_ppvar_vbat_mw"
        self._cfilter = cfilter
        super().__init__(
            servo_client=servo_client,
            ctrls=[self._ec_cmd],
            stop_signal=stop_signal,
            sample_rate=sample_rate,
            tag="ec",
            title="EC",
        )

    def verify(self):
        """ECPowerTracker verify that also checks if avg_ppvar is available."""
        # First verify the normal ctrl.
        super().verify()
        # Then get ambitious and check if the newer avg_ppvar_vbat_mw is also
        # available.
        self._ctrls = self._cfilter([self._avg_ec_cmd])
        try:
            super().verify()
            # This means that avg_ppvar_vbat_mw worked fine.
        except PowerTrackerError as e:
            # This means that avg_ppvar_vbat_mw is not supported.
            # Revert back to ppvar_vbat_mw for main ctrls.
            self._logger.info(str(e))
            self._logger.info(
                "%s not supported, using %r instead.", self._avg_ec_cmd, self._ec_cmd
            )
            self._ctrls = self._cfilter([self._ec_cmd])

    def prepare(self, fast=False, powerstate=UNKNOWN_POWERSTATE):
        """Reduce the time needed to enter deep-sleep after console interaction."""
        # Do not check for failure or anything, as its a nice-to-have and increases
        # accuracy, but does not impact functionality. Dsleep might also not be
        # available on some EC images.
        self._sclient.set("ec_uart_cmd", "dsleep 2")

    def run(self):
        """EC vbat 'run' to ensure the first reading does not use averaging."""
        sample_tuples, duration_ms = self._sample_ctrls([self._ec_cmd])
        # Rewrite the name to be whatever actual control is being used: avg &
        # regular. This is required so that the output is not split into two
        # domains that are really the same: regular & avg.
        adjusted_sample_tuples = []
        temp_sample_data = []
        for name, sample in sample_tuples:
            if name == self._ec_cmd:
                name = self._ctrls[0]
            adjusted_sample_tuples.append((name, sample))
            temp_sample_data.append((name, sample))
        self.set_sample_data(temp_sample_data)
        self._stats.add_samples(adjusted_sample_tuples)
        self._stop_signal.wait(max(self._rate - (duration_ms / 1000), 0))
        super().run()


class RegexFilter:
    """Filter out control names based on regex."""

    def __init__(self, rgx_to_keep, rgx_to_remove):
        """"""
        self._logger = logging.getLogger(type(self).__name__)
        self.rgx_to_keep = rgx_to_keep
        self.rgx_to_remove = rgx_to_remove

    def __call__(self, control_names):
        """Filter out |control_names|

        Args:
          control_names: a list of control names

        Note: rgx filters
          The caller should really only specify one of them, but if both are
          specified, only first the |rgx_to_remove| are removed, and then
          only those matchin the |rgx_to_keep| are kept

        Returns:
          filtered controls: a list (potentially empty) after filtering
        """
        # Only use ctrls from the main device for now
        controls = [ctrl for ctrl in control_names if "." not in ctrl]
        if self.rgx_to_remove is not None:
            controls = []
            for c in control_names:
                if re.match(self.rgx_to_remove, c):
                    self._logger.info("Filtering out control %r", c)
                else:
                    controls.append(c)
        if self.rgx_to_keep is not None:
            controls = []
            for c in control_names:
                if not re.match(self.rgx_to_keep, c):
                    self._logger.info("Filtering out control %r", c)
                else:
                    controls.append(c)
        return controls


class PowerMeasurementError(Exception):
    """Error class to invoke on PowerMeasurement errors."""


class PowerMeasurement:
    """Class to perform power measurements using servod.

    PowerMeasurement allows the user to perform synchronous and asynchronous
    power measurements using servod.
    The class performs discovery, configuration, and sampling of power commands
    exposed by servod, and allows for configuration of:
    - rates to measure
    - how to store the data

    Attributes:
      _sclient: servod proxy
      _board: name of board attached to servo
      _stats: collection of power measurement stats after run completes
      _outdir: default outdir to save data to
               After the measurement a new directory is generated
      _processing_done: bool flag indicating if measurement data is processed
      _setup_done: Event object to indicate power collection is about to start
      _stop_signal: Event object to indicate that power collection should stop
      _power_trackers: list of PowerTracker objects setup for measurement
      _fast: if True measurements will skip explicit powerstate retrieval
      _logger: PowerMeasurement logger

      Note: PowerMeasurement garbage collection, or any call to reset(), will
            result in an attempt to clean up directories that were created and
            left empty.
    """

    DEFAULT_OUTDIR_BASE = os.path.join(
        os.getenv("TMPDIR", "/tmp"), "power_measurements/"
    )

    PREMATURE_RETRIEVAL_MSG = (
        "Cannot retrieve information before data collection has finished."
    )

    def __init__(
        self,
        servo_client,
        adc_rate=DEFAULT_ADC_RATE,
        adc_accum_rate=DEFAULT_ADC_ACCUM_RATE,
        vbat_rate=DEFAULT_VBAT_RATE,
        fast=False,
        board=DEFAULT_BOARD,
        rgx_to_keep=None,
        rgx_to_remove=None,
    ):
        """Init PowerMeasurement class by attempting to create PowerTrackers.

        Args:
          host: host to reach servod instance
          port: port on host to reach servod instance
          adc_rate: sample rate for servod ADC controls
          adc_accum_rate: sample rate for servod ADC accumulator/avg power controls
          vbat_rate: sample rate for servod ec vbat command
          fast: if true, no servod control verification is done before measuring
                power, nor the powerstate queried from the EC
          board: board name to use. If this is not provided, then an attempt
                 is made to query it from the EC
          rgx_to_keep: regex, only keep rails matching this regex
          rgx_to_remove: regex, remove all rails that match this regex

        Note: rgx filters - read comment on RegexFilter class

        Raises:
          PowerMeasurementError: if no PowerTracker setup successful
          PowerMeasurementError: ADCs cannot be configured correctly
        """
        self._fast = fast
        self._logger = logging.getLogger(type(self).__name__)
        self._outdir = None
        self._sclient = servo_client
        self._board = board
        if not fast and self._board == DEFAULT_BOARD:
            try:
                board = self._sclient.get("ec_board")
                if board != "not_applicable":
                    self._board = board
            except client.ServoClientError:
                self._logger.debug(
                    "Failed to get ec_board, setting to %r.", self._board
                )
        self._processing_done = False
        self._setup_done = threading.Event()
        self._stop_signal = threading.Event()
        self._power_trackers = []
        self._stats = {}
        self._sample_data = []
        power_trackers = []
        # build out the filter
        cfilter = RegexFilter(rgx_to_keep, rgx_to_remove)
        adc_tracker = adc_accum_tracker = ec_tracker = None
        # Setup ADCs on the servo device.
        self._sclient.set("servo_adcs_enabled", "on")
        if self._sclient.get("servo_adcs_enabled") != "on":
            raise PowerMeasurementError("ADCs setup failed.")
        if adc_rate > 0:
            try:
                adc_tracker = OnboardADCPowerTracker(
                    self._sclient, self._stop_signal, cfilter, adc_rate
                )
            except PowerTrackerError:
                self._logger.warning("Onboard ADC tracker setup failed.")
        if adc_accum_rate > 0:
            try:
                adc_accum_tracker = OnboardADCAccumPowerTracker(
                    self._sclient, self._stop_signal, cfilter, adc_accum_rate
                )
            except PowerTrackerError:
                self._logger.debug(
                    "Onboard ADC accumulators not supported, or setup failed."
                )

        if vbat_rate > 0:
            try:
                ec_tracker = ECPowerTracker(
                    self._sclient, self._stop_signal, cfilter, vbat_rate
                )
            except PowerTrackerError:
                self._logger.warning("EC Power tracker setup failed.")
        # if an ADC supports accumulator controls, it also supports regular
        # controls. In those cases, we do not need two sources of the same data.
        # Therefore, we remove all controls from the |adc_tracker| that are also
        # present in the |adc_accum_tracker|. If after that, the |adc_tracker|
        # is empty, we skip it entirely.
        if adc_tracker is not None and adc_accum_tracker is not None:
            for rail in adc_accum_tracker.rails:
                adc_tracker.remove_rail(rail)
            if adc_tracker.empty:
                self._logger.info(
                    "ADC tracker has no controls that are not already "
                    "covered by the ADC accum tracker. Removing."
                )
        # After preprocessing is done, append the trackers.
        for tracker in [adc_tracker, adc_accum_tracker, ec_tracker]:
            if tracker is not None:
                if not tracker.empty:
                    power_trackers.append(tracker)
                else:
                    self._logger.info(
                        "Will not be using %r tracker (nothing to track)", tracker
                    )
        self.reset()
        for tracker in power_trackers:
            if not self._fast:
                try:
                    tracker.verify()
                except PowerTrackerError:
                    self._logger.debug(
                        "Tracker %s failed verification. Not using it.", tracker.title
                    )
                    continue
            self._power_trackers.append(tracker)
        if not self._power_trackers:
            raise NoSourceError("No power measurement source successfully setup.")

    def reset(self):
        """reset PowerMeasurement object to reuse for a new measurement.

        The same PowerMeasurement object can be used for multiple power
        collection runs on the same servod instance by calling reset() on
        it. This will wipe the previous run's data to allow for a fresh
        reading.

        Use this when running multiple tests back to back to simplify the code
        and avoid recreating the same PowerMeasurement object again.
        """
        self._stats = {}
        self._setup_done.clear()
        self._stop_signal.clear()
        self._processing_done = False

    def measure_timed_power(
        self, sample_time=60, wait=0, powerstate=UNKNOWN_POWERSTATE
    ):
        """Measure power in the main thread.

        Measure power for |sample_time| seconds before processing the results and
        returning to the caller. After this method returns, retrieving measurement
        results is safe.

        Args:
          sample_time: seconds to measure power for
          wait: seconds to wait before collecting power
          powerstate: (optional) pass the powerstate if known
        """
        setup_done = self.measure_power(wait=wait, powerstate=powerstate)
        setup_done.wait()
        time.sleep(sample_time + wait)
        self.finish_measurement()

    def measure_power(self, wait=0, powerstate=UNKNOWN_POWERSTATE):
        """Measure power in the background until caller indicates to stop.

        Spins up a background measurement thread and then returns events to manage
        the power measurement time.
        This should be used when the main thread needs to do work
        (like an autotest) while power measurements are going on.

        Args:
          wait: seconds to wait before collecting power
          powerstate: (optional) pass the powerstate if known

        Returns:
          Event - |setup_done|
          Caller can wait on |setup_done| to know when setup for measurement is done
        """
        self.reset()
        measure_t = threading.Thread(
            target=self._measure_power, kwargs={"wait": wait, "powerstate": powerstate}
        )
        measure_t.daemon = True
        measure_t.start()
        return self._setup_done

    def _measure_power(self, wait, powerstate=UNKNOWN_POWERSTATE):
        """Power measurement thread method coordinating sampling threads.

        Args:
          wait: seconds to wait before collecting power
          powerstate: (optional) pass the powerstate if known
        """
        if not self._fast and powerstate == UNKNOWN_POWERSTATE:
            try:
                ecpowerstate = self._sclient.get("ec_system_powerstate")
                if ecpowerstate != "not_applicable":
                    # Skip setting the power_state if the ec control does not
                    # provide real information.
                    powerstate = ecpowerstate
            except client.ServoClientError:
                self._logger.debug("Failed to get powerstate from EC.")
        for power_tracker in self._power_trackers:
            power_tracker.prepare(self._fast, powerstate)
        ts = time.strftime("%Y%m%d-%H%M%S", time.localtime(time.time()))
        self._outdir = os.path.join(
            self.DEFAULT_OUTDIR_BASE, self._board, "%s_%s" % (powerstate, ts)
        )
        # Signal that setting the measurement is complete
        self._setup_done.set()
        # Wait on the stop signal for |wait| seconds. Preemptible.
        self._stop_signal.wait(wait)
        if not self._stop_signal.is_set():
            for power_tracker in self._power_trackers:
                power_tracker.start()

    def finish_measurement(self):
        """Signal to stop collection to Trackers before joining their threads."""
        self._stop_signal.set()
        for tracker in self._power_trackers:
            if tracker.is_alive():
                tracker.join()

    def get_pm_status(self):
        """Pass the information if the power measurement is finished or not
        Returns:
          True:  power measurement is finished
          False: power measurement is still working
        """
        return self._stop_signal.is_set()

    def process_measurement(self, tstart=None, tend=None):
        """Trim data to [tstart, tend] before calculating stats.

        Call finish_measurement internally to ensure that data collection is fully
        wrapped up.

        Args:
          tstart: first timestamp to include. Seconds since epoch
          tend: last timestamp to include. Seconds since epoch
        """
        # In case the caller did not explicitly call finish_measurement yet.
        self.finish_measurement()
        try:
            for tracker in self._power_trackers:
                self._stats[tracker.title] = tracker.process_measurement(tstart, tend)
        finally:
            self._processing_done = True

    def save_raw_data(self, outdir=None):
        """Save raw data of the PowerMeasurement run.

        Files can be read into object by using numpy.loadtxt()

        Args:
          outdir: output directory to use instead of autogenerated one

        Returns:
          List of pathnames, where each path has the raw data for a rail on
          this run

        Raises:
          PowerMeasurementError: if called before measurement processing is done
        """
        if not self._processing_done:
            raise PowerMeasurementError(self.PREMATURE_RETRIEVAL_MSG)
        outdir = outdir if outdir else self._outdir
        outfiles = []
        for stat in self._stats.values():
            outfiles.extend(stat.save_raw_data(outdir))
        self._logger.info("Storing raw data at:\n%s", "\n".join(outfiles))
        return outfiles

    def get_raw_data(self):
        """Retrieve raw data for current run.

        Retrieve a dictionary of each StatsManager object this run used, where
        each entry is a dictionary of the rail to raw values.

        Returns:
          A dictionary of the form:
            { 'EC'  : { 'time'              : [0.01, 0.02 ... ],
                        'timeline'          : [0.0, 0.01 ...],
                        'Sample_msecs'      : [0.4, 0.2 ...],
                        'ec_ppvar_vbat_mw'  : [52.23, 87.23 ... ]}
              'Onboard ADC' : ... }
          Possible keys are: 'EC', 'Onboard ADC'

        Raises:
          PowerMeasurementError: if called before measurement processing is done
        """
        if not self._processing_done:
            raise PowerMeasurementError(self.PREMATURE_RETRIEVAL_MSG)
        return {name: stat.get_raw_data() for name, stat in self._stats.items()}

    def save_trimmed_summary(self, tag, tstart, tend, outdir=None, message=None):
        """Save a formatted summary that only contains [tstart, tend] data.

        Args:
          tag: string, identifier to tag this subset of data
          tstart: start of valid data range, seconds since epoch
          tend: end of valid data range, seconds since epoch
          outdir: output directory to use instead of autogenerated one
          message: message to attach after the summary for each summary

        Returns:
          List of pathnames, where summaries for this run are stored

        Raises:
          PowerMeasurementError: if called before measurement processing is done
        """
        if not self._processing_done:
            raise PowerMeasurementError(self.PREMATURE_RETRIEVAL_MSG)
        stats_managers = [
            s.trimmed_copy(tag=tag, tstart=tstart, tend=tend)
            for s in self._stats.values()
        ]
        # If trimming produces an 'empty' stats manager i.e. a stats manager with
        # no data in it, |trimmed_copy| will return None, so we need to filter
        # those out.
        stats_managers = [s for s in stats_managers if s is not None]
        # Lastly, we want to modify the titles. This is simply to make sure
        # that the tag can help identify the summary
        for s in stats_managers:
            s._title += "(%s)" % tag
        return self._save_summary(
            stats_managers=stats_managers, outdir=outdir, message=message
        )

    def save_summary(self, outdir=None, message=None):
        """Save summary of the PowerMeasurement run.

        Args:
          outdir: output directory to use instead of autogenerated one
          message: message to attach after the summary for each summary

        Returns:
          List of pathnames, where summaries for this run are stored

        Raises:
          PowerMeasurementError: if called before measurement processing is done
        """
        if not self._processing_done:
            raise PowerMeasurementError(self.PREMATURE_RETRIEVAL_MSG)
        return self._save_summary(
            stats_managers=self._stats.values(), outdir=outdir, message=message
        )

    def _save_summary(self, stats_managers=None, outdir=None, message=None):
        """Save summary of the PowerMeasurement run.

        Args:
          stats_managers: a list of stats managers from which to save the summaries
          outdir: output directory to use instead of autogenerated one
          message: message to attach after the summary for each summary

        Returns:
          List of pathnames, where summaries for this run are stored

        Raises:
          PowerMeasurementError: if called before measurement processing is done
        """
        if stats_managers is None:
            stats_managers = []
        outdir = outdir if outdir else self._outdir
        outfiles = [stat.save_summary(outdir) for stat in stats_managers]
        if message:
            for fname in outfiles:
                with open(fname, "a", encoding="utf-8") as f:
                    f.write("\n%s\n" % message)
        # Also, output a markdown version of each summary
        md_outfiles = [stat.save_summary_md(outdir) for stat in stats_managers]
        self._logger.info("Storing summaries at:\n%s", "\n".join(outfiles))
        self._logger.info("Storing .md summaries at:\n%s", "\n".join(md_outfiles))
        return outfiles

    def get_summary(self):
        """Retrieve summary of the PowerMeasurement run.

        Retrieve a dictionary of each StatsManager object this run used, where
        each entry is a dictionary of the rail to its statistics.

        Returns:
          A dictionary of the form:
            {'EC':          {'ppvar_vbat_mw': {'count':  1,
                                               'max':    0.0,
                                               'mean':   0.0,
                                               'min':    0.0,
                                               'stddev': 0.0},
                             'Sample_msecs':  {...},
                             'time':          {...},
                             'timeline':      {...}},
             'Onboard ADC': {...}}
          Possible keys are: 'EC', 'Onboard ADC'

        Raises:
          PowerMeasurementError: if called before measurement processing is done
        """
        if not self._processing_done:
            raise PowerMeasurementError(self.PREMATURE_RETRIEVAL_MSG)
        return {name: stat.get_summary() for name, stat in self._stats.items()}

    def get_formatted_summary(self):
        """Retrieve summary of the PowerMeasurement run.

        See StatsManager._DisplaySummary() for more details

        Returns:
          string with all available summaries concatenated

        Raises:
          PowerMeasurementError: if called before measurement processing is done
        """
        if not self._processing_done:
            raise PowerMeasurementError(self.PREMATURE_RETRIEVAL_MSG)
        summaries = [stat.summary_to_string() for stat in self._stats.values()]
        return "\n".join(summaries)

    def display_summary(self):
        """Print summary retrieved from get_formatted_summary() call."""
        print("\n%s" % self.get_formatted_summary())

    def save_summary_json(self, outdir=None):
        """Save summary of the PowerMeasurement run as JSON.

        Args:
          outdir: output directory to use instead of autogenerated one

        Returns:
          List of pathnames, where summaries for this run are stored

        Raises:
          PowerMeasurementError: if called before measurement processing is done
        """
        if not self._processing_done:
            raise PowerMeasurementError(self.PREMATURE_RETRIEVAL_MSG)
        return self._save_summary_json(
            stats_managers=self._stats.values(), outdir=outdir
        )

    def _save_summary_json(self, stats_managers=None, outdir=None):
        """Save summary of the PowerMeasurement run as JSON.

        Args:
          stats_managers: a list of stats managers from which to save the summaries
          outdir: output directory to use instead of autogenerated one

        Returns:
          List of pathnames, where summaries for this run are stored

        Raises:
          PowerMeasurementError: if called before measurement processing is done
        """
        if stats_managers is None:
            stats_managers = []
        outdir = outdir if outdir else self._outdir
        json_outfiles = [stat.save_summary_json(outdir) for stat in stats_managers]
        self._logger.info("Storing .md summaries at:\n%s", "\n".join(json_outfiles))
        return json_outfiles

    def get_sample_data(self):
        """This function can pass the latest power information

        Collect the data in each tracker and append the data into an array

        Returns:
          return the latest power information
        """
        sample_data = []

        for power_data in self._power_trackers:
            data = power_data.get_sample_data()
            if data:
                sample_data += data
        return sample_data

    def clean_sample_data(self):
        """This function will clean the current data structure which saves
        the power data.
        """
        for trackers in self._power_trackers:
            trackers.clean_sample_data()
