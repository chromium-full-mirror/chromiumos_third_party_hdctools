# Copyright 2018 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Calculates statistics for lists of data and pretty print them."""


import copy
import logging
import time

from measurement_tools.utils import stats_manager


TIME_KEY = "time"
TLINE_KEY = "timeline"


class TimelinedStatsManager(stats_manager.StatsManager):
    """StatsManager extension that automatically keeps a timeline.

    Timestamp gets recorded when the data is added.

    When calculating stats a timeline is also generated that starts at t=0

    Attributes:
      _tkey: key used for the timestamps column
      _tlkey: key used for the timeline column
    """

    # pylint: disable=W0102
    def __init__(
        self,
        title="",
        smid="",
        hide_domains=[],
        order=[],
        time_key=TIME_KEY,
        timeline_key=TLINE_KEY,
        rate=None,
    ):
        """Initialize by setting time key and setting it to hide in summaries.

        Note: for title, smid, hide_domains, and order see stats_manager.py for
        details on usage.

        Args:
          title: string used as title banner for formatted summary
          smid: StatsManager id used to prepend to output files to ensure uniqueness
          hide_domains: list of domains to hide on formatted summary
          order: domain order for formatted summary
          time_key: key used for timestamp column
          timeline_key: key used for relative timeline column (starts at 0)
          rate: rate that the data is collected by dut-power (in seconds)
        """
        self._logger = logging.getLogger(type(self).__name__)
        self._tkey = time_key
        self._tlkey = timeline_key
        super().__init__(
            title=title,
            smid=smid,
            hide_domains=hide_domains,
            order=order,
            accept_nan=True,
            rate=rate,
        )
        self._hide_domains.append(self._tkey)
        self._hide_domains.append(self._tlkey)

    def calculate_stats(self):
        """Generate relative timeline before calling StatsManager calculate_stats."""
        if self._tkey in self._data:
            # |tkey| might have been removed during trimming.
            timeline = self._data[self._tkey]
            timeline = [entry - timeline[0] for entry in timeline]
            self._data[self._tlkey] = timeline
        super().calculate_stats()

    def add_sample(self, domain, sample):
        """NotImplemented.

        In order to preserve the balanced timeline adding individual samples is
        discouraged as it might result in unintended behavior. If you find yourself
        in need of this function, please implement it/raise a bug.
        """
        raise stats_manager.StatsManagerError(
            "TimelinedStatsManager does not support add_sample. Use add_samples."
        )

    def add_samples(self, samples, timestamp=None):
        """Record a list of domains and samples.

        Record each (domain, sample) pair and the timestamp when the
        pairs were recorded.

        To avoid timeline discrepancies, this method ensures that each domain in
        |_data| is of equal size. This is accomplished by adding NaN values
        whenever there is no data-point for a domain at a given timestamp.

        Args:
          samples: a list of (domain, sample) tuples
          timestamp: timestamp the sample is taken
        """
        if timestamp is None:
            timestamp = time.time()
        samples.append((self._tkey, timestamp))
        domains_so_far = set(self._data.keys())
        domains_incoming = set([entry[0] for entry in samples])
        if len(domains_incoming) != len(samples):
            raise stats_manager.StatsManagerError("Domain appears multiple times.")
        # Add a NaN for each previous time-stamp for new domains
        new_domains = domains_incoming - domains_so_far
        nan_col = [float("NaN")] * len(self._data[self._tkey])
        for domain in new_domains:
            self._data[domain] = copy.copy(nan_col)
        # Add a NaN for each known domain that has no sample in |samples|
        known_domains_missing = domains_so_far - domains_incoming
        known_domains_missing_nans = [
            (domain, float("NaN")) for domain in known_domains_missing
        ]
        samples.extend(known_domains_missing_nans)
        for domain, sample in samples:
            super().add_sample(domain, sample)

    def functionally_empty(self):
        """Whether the stats manager is devoid of meaningful data.

        Returns:
          True
          - if the data is empty
          - if the only keys available are TIME_KEY and TLINE_KEY
          - if other keys exist, but they are empty entries
        """
        # Trimming below guarantees that a domain will only exist iff it is not
        # empty after being trimmed. It suffices for the guarantees above to check
        # that there are more keys in the data than just |TIME_KEY| and |TLINE_KEY|
        # TODO(coconutruben): this could also do the work of detecting if all
        # samples are NaN, though that requires a larger rework of that logic, and
        # potentially pulling in data interpolation into this class.

        return all(k in [TIME_KEY, TLINE_KEY] for k in self._data.keys())

    def trimmed_copy(self, tag="", tstart=None, tend=None, offset=0):
        """Return a (trimmed) copy of this stats manager.

        If |tstart| and |tend| are provided, it will behave like |trim_samples()|
        below, and return trimmed to [tstart + offset, tend + offset]

        |tag| usage note: the |smid| of the stats manager is usually its source e.g.
        'onboard' etc. The trimmed copies are often useful if one larger
        measurement contains sub-measurements. In those cases, providing a tag can
        help identify the correct summary file easier, by appending the tag to the
        smid like |smid_[tag]|

        Args:
          tag: a string to expand the |smid| of this stats manager's copy with.
          tstart: first timestamp to include. Seconds since epoch
          tend: last timestamp to include. Seconds since epoch
          offset: add offset to tstart and tend to manipulate which data points to
                   trim and which to keep. Seconds since epoch

        Returns:
          a copy of the stats manager, trimmed, or None if trimming produces empty
          stats manager
        """
        # trimmed stats manager. We want a deep-copy so that we carry all the data
        # and don't accidentally trim data from the original stats manager.
        # The logger inside the stats manager cannot be deep copied. This works
        # around that.
        old_logger = self._logger
        self._logger = None
        trimmed_sm = copy.deepcopy(self)
        trimmed_sm._logger = logging.getLogger(type(self).__name__)
        self._logger = old_logger
        # Restore the logger, and make sure that |trimmed_sm| also has a logger.
        trimmed_sm.trim_samples(tstart, tend, offset)
        if trimmed_sm.functionally_empty():
            # Trimming resulted in an empty stats manager. Just return None.
            return None
        if tag:
            trimmed_sm._smid += "_%s" % tag
        # Lastly, before returning, let's recalculate the stats to have the right
        # values for the trimmed data. This overwrites any previous 'stats' (e.g.
        # 'mean' values for a domain).
        trimmed_sm.calculate_stats()
        return trimmed_sm

    def trim_samples(self, tstart=None, tend=None, offset=0):
        """Trim raw data to [tstart + offset, tend + offset].

        Args:
          tstart: first timestamp to include. Seconds since epoch
          tend: last timestamp to include. Seconds since epoch
          offset: add offset to tstart and tend to manipulate which data points to
                   trim and which to keep. Seconds since epoch
        """
        if tstart is None and tend is None:
            # Avoid doing any work if there will be no trimming.
            return

        timeline = self._data[self._tkey]
        if tstart is None:
            tstart = timeline[0]
        tstart += offset
        if tend is None:
            tend = timeline[-1]
        tend += offset

        indices_to_keep = [i for i, t in enumerate(timeline) if tstart <= t <= tend]

        # pylint: disable=W0212
        domains_to_remove = set()
        for domain, samples in self._data.items():
            trimmed_samples = [samples[i] for i in indices_to_keep]
            if trimmed_samples:
                self._data[domain] = trimmed_samples
            else:
                self._logger.warning(
                    "Trimming to start ts: %.2f end ts: %.2f offset: %d"
                    " has caused domain %r to become empty. Removing it "
                    "from the TimelinedStatsManager.",
                    tstart,
                    tend,
                    offset,
                    domain,
                )
                domains_to_remove.add(domain)
        for domain in domains_to_remove:
            del self._data[domain]
