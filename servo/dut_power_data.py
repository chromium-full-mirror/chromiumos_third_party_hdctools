# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import bisect
import json
import logging
import time


# The time range for fetching the sample data
SAMPLING_DELTA_PERIOD = 10

FETCHING_DATA_SLEEP_TIME = 0.01
STREAMING_CHART_OUTPUT_TYPE = "streaming_chart"
LINE_CHART_OUTPUT_TYPE = "linechart"
# The list here can help to store the data name
# that we are not going to pass to the visualization UI
FILTER_DATA_NAME_LIST = ["Sample_msecs"]


class DataSampler:
    """The Class can help to extract the power data to json, define the format,
    and return the completed data structure

    Attributes:
      _data_sample: A DataSample which can save the power's data,
        and return to http_server
      _logger: Sample generator log
      _pm: The constructor of the power measurement,
        which can help to get the information of the dut power data
      _current_data_format: Store current data format which can help
        to compare if data format is changed
    """

    def __init__(self, pm):
        """Init DataSampler class which will keep updating the data structure that store
        the dut power data
        """
        self._data_sample = None
        self._logger = logging.getLogger(type(self).__name__)
        self._pm = pm
        self._current_data_format = []

    def get_data_sample(self):
        """Convert data into JSON format and return the json data to visualization UI"""
        if self._data_sample is None:
            return '""'
        output_type = STREAMING_CHART_OUTPUT_TYPE
        if self._pm.get_pm_status():
            output_type = LINE_CHART_OUTPUT_TYPE
        return self._data_sample.to_json(
            output_type, time.time() - SAMPLING_DELTA_PERIOD
        )

    def compare_data_sample_format(self, latest_sample_format):
        """Compare the data format

        If the data we received from the power measurement changes, we need
        to change the data format to avoid error and update the data we are
        going to pass to the visualization UI. Therefore, we need this function
        to figure out if the data format is changed.

        Args:
          latest_sample_format: The latest data format which can be compared to
            the current data format
        """
        return sorted(self._current_data_format) == sorted(latest_sample_format)

    def get_data_sample_format(self, latest_samples):
        """This function define the data sample format

        When we first get the data from power measurement, we need to define the
        data name which save each kind of data.
        For example: the data got from power measurement is
        [('ppdut5', 3.1), ('ppservo5', 4.1), ('ppchg5', 0.0)]
        Then save the ['ppdut5', 'ppservo5', 'ppcgh5'] as the data sample format

        Args:
          latest_samples: The data structure which contains the data from power
            measurement. latest_samples[0] is the data name, for ex, 'ppchg5',
            'ppdut5', we use these names to define the data sample format
        """
        data_sample_format = []
        for data_name in latest_samples:
            # Filter out the data that we do not want to show
            # data_name[0] is the label of the data, we filter out
            # the label that we do not want to show in the UI
            if not data_name[0] in FILTER_DATA_NAME_LIST:
                data_sample_format.append(data_name[0])
        return data_sample_format

    def define_data_sample_format(self, data_sample_format):
        """Pass the data sample format to the DataSample Constructor

        Args:
          data_sample_format: The data sample format we got
          which will be used to save the dut power data
        """
        self._current_data_format = data_sample_format
        data_sample_format = ["time"] + data_sample_format
        self._data_sample = DataSample(data_sample_format)

    def sample_generator(self):
        """This function provide a while loop keeps fetching the updated power data

        If the data we get from power is empty, it means that the thread of
        power measurement have not opened yet wait for this thread opens.
        If the data sample format is empty, we need to define the format first
        When we get the data from power measurement,
        we feed the data into DataSample Class and convert the data into json format

        Notes:
          The example data we get from the measure_power
          [('ppdut5', 3.1), ('ppservo5', 4.2),
           ('ppchg5', 0.0), ('Sample_msecs', 302.1)]
        """

        self._logger.info("Begin the sample generator to fetch the power data")

        while not self._pm.get_pm_status():
            # Get the power data from power management
            latest_samples = self._pm.get_sample_data()
            if latest_samples:
                data_sample_format = self.get_data_sample_format(latest_samples)
                # If the data sample format is empty, we need to find
                # how many data we currently have, and define the data sample format,
                # Or if the latest data sample format is different with the one
                # we currently use, we need to redefine the data sample format
                if not self._data_sample or not self.compare_data_sample_format(
                    data_sample_format
                ):
                    self.define_data_sample_format(data_sample_format)

                # After fetching the data, we can clean the temporary
                # data structure in power measurement
                self._pm.clean_sample_data()

                # After define the format, read the data from power measurement
                # and insert into the data structure
                temp_latest_samples = []
                for data in latest_samples:
                    # data looks like data:  ('ppdut5', 3.1)
                    # data[0] is the label of the data: 'ppdut5'
                    # data[1] is the actual value of the data: 3.1
                    if not data[0] in FILTER_DATA_NAME_LIST:
                        temp_latest_samples.append(data[1])
                self._data_sample.add_samples([time.time()] + temp_latest_samples)

            time.sleep(FETCHING_DATA_SLEEP_TIME)


class DataSample:
    """This class help to define data format,insert data and return data in json

    We use JSON format to transmit the data, JSON format is a text format
    for storing and transporting data, it is commonly used for transmitting
    the data to WEB.
    JSON defines object to properties and each property has its value

    Attributes:
      _samples: The data we save
      _meta: The data name that we will show on the visualization UI
      _logger: DataSample Logger

    The data received at html:
    matrix: Array(5)
    0: (3) [13, 14, 15]
    1: (3) [856.2, 854.7, 853.9]
    2: (3) [3.5, 2.4, 2.4]
    3: (3) [0, 0, 0
    4: (3) [184.5, 181.3, 182.2]
    length: 5
    meta:
    rowMeta: Array(5)
    0: {name: 'time'}
    1: {name: 'ppservo5'}
    2: {name: 'ppdut5'}
    3: {name: 'ppchg5'}
    4: {name: 'Sample_msecs'}

    length: 5
    type: "streaming_chart"
    """

    def __init__(self, sample_names):
        """Init DataSample class by defining the metadata format

        There are several trackers in the power measurement,
        each tracker contains the data which can help to analysis power's condition
        As the real-time visualization, keep fetching the data and
        append the data into json format.
        In our metadata format we have rowData to save all type of data,
        matrix saves the corresponding data value of each type of data,

        Args:
          sample_names are all the metadata names we get from power measurement
        """
        self._logger = logging.getLogger(type(self).__name__)
        self._samples = []

        # rowMeta contains all type of data we have
        self._meta = {"rowMeta": []}
        for name in sample_names:
            self._samples.append([])
            row_meta = {"name": name}
            self._meta["rowMeta"].append(row_meta)

    def add_samples(self, samples):
        """Insert the sample data

        Args:
          samples: The data which is going to be insert into the _samples
        """
        try:
            for sample_pos, sample_element in enumerate(samples):
                self._samples[sample_pos].append(sample_element)
        except Exception:
            if len(self._samples) != len(samples):
                self._logger.error(
                    "The number of new samples"
                    "does not match with the existing samples"
                )
            else:
                self._logger.error("Error happen while inserting the data")

            self._logger.error(
                "The power measurement is still working, "
                "press ctrl-c to show the summary table "
                "and close the visualization server"
            )

    def to_json(self, out_type, start_time=0):
        """Convert the data into json format

        Args:
          out_type: The output type will always be "streaming_chart" right now,
            this variable can help the UI present our data in different modes
          start_time: The start time we are going to fetch the data
        Returns:
          A json format. For example:
          As the example below, the first line in Matrix matched to time in meta,
          second line in Matrix matches to ppchg5 in meta...
          {"type": "streaming_chart",
           "meta": {"rowMeta": [{"name": "time"}, {"name": "ppchg5"},
                   {"name": "ppdut5"}, {"name": "ppservo5"},
                   {"name": "Sample_msecs"}]},
           "matrix": [[13.1, 14.2, 15.6],
                      [0.0, 0.0, 0.0],
                      [0.0, 0.0, 0.0],
                      [725.1, 727.3, 726.2],
                      [175.8, 180.4, 182.5]]}
        """
        end = len(self._samples[-1])
        start = bisect.bisect(self._samples[0], start_time)
        transmit = []
        for samples in self._samples:
            transmit.append(samples[start:end])
            data = {"type": out_type, "meta": self._meta, "matrix": transmit}
        return json.dumps(data)
