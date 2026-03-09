#!/usr/bin/env python3
# Copyright 2018 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Servod power measurement utility."""


import argparse
import logging
import os
import shutil
import signal
import sys
import tempfile
import threading

from measurement_tools import dut_power_data
from measurement_tools import http_server
from measurement_tools import measure_power
from measurement_tools import servo_parsing
from servo.core import client


class ProgressPrinter(threading.Thread):
    """Print a marker every few seconds to indicate progress.

    Public Attributes:
      stop: Event object to signal end to printing.
    """

    # Default progress marker.
    PROGRESS_MARKER = "."
    # Default wait marker.
    WAIT_MARKER = "-"
    # Default rate to print markers.
    PROGRESS_UPDATE_RATE = 1.0

    def __init__(
        self,
        marker=PROGRESS_MARKER,
        rate=PROGRESS_UPDATE_RATE,
        stop_signal=None,
        max_duration=float("inf"),
    ):
        """Initialize constants & prepare thread to run."""
        super().__init__()
        self._marker = marker
        self._rate = rate
        self._remaining_markers = max_duration / rate
        if not stop_signal:
            stop_signal = threading.Event()
        self.stop = stop_signal

    def run(self):
        """Print |_marker|s.

        Every |_rate| seconds until |stop| is set or we've printed the maximum
        markers if the max_duration field was set.
        """
        while not self.stop.is_set() and self._remaining_markers >= 1.0:
            sys.stdout.write(self._marker)
            self._remaining_markers -= 1.0
            sys.stdout.flush()
            self.stop.wait(self._rate)


class DutPower:
    """Dut-power class to execute dut-power cmdline."""

    def _add_mutually_exclusive_action(self, name, parser, default=True, action="save"):
        """Add both '--do-something' and '--no-do-something' pair to parser.

        This adds a mutually exclusive switch for a boolean action into a parser.
        Adds two flags:
        --%{action}-%{name}
        --no-%{action}-%{name}

        Args:
          name: object on which to perform the action
          parser: parser to attach mutually exclusive group to
          default: default value for boolean switch
          action: action to perform on name
        """

        saver = parser.add_mutually_exclusive_group()
        argname = "--%s-%s" % (action, name)
        noargname = "--no-%s-%s" % (action, name)
        dest = "%s_%s" % (action, name.replace("-", "_"))
        arghelp = "%s %s" % (action, name)
        saver.add_argument(
            argname, default=default, dest=dest, action="store_true", help=arghelp
        )
        noarghelp = "don't %s %s" % (action, name)
        saver.add_argument(
            noargname,
            default=argparse.SUPPRESS,
            dest=dest,
            action="store_false",
            help=noarghelp,
        )

    def _build_parser(self):
        """Create a parser to parse the cmdline dut-power command.

        Returns:
          a parser that parses dut-power cmdline.
        """
        description = "Measure power using servod."
        # BaseServodParser provides port, host, debug arguments
        parser = servo_parsing.ServodClientParser(description=description)
        # overwriting/providing measurement information so the servo device
        # does not need to query for it.
        parser.add_argument(
            "--powerstate",
            default=measure_power.DEFAULT_POWERSTATE,
            choices=measure_power.POWERSTATES,
            help="powerstate being measured (determines data dst)",
        )
        parser.add_argument(
            "-b",
            "--board",
            default=measure_power.DEFAULT_BOARD,
            help="board being measured (determines data dst)",
        )
        # power measurement logistics
        parser.add_argument(
            "-f",
            "--fast",
            default=False,
            action="store_true",
            help="if fast no verification cmds are done",
        )
        parser.add_argument(
            "-w",
            "--wait",
            default=0,
            type=float,
            help="time (sec) to wait before measuring power",
        )
        parser.add_argument(
            "-t",
            "--time",
            default=60,
            type=float,
            help="time (sec) to measure power for",
        )
        # This is the filter group - to either remove or only keep depending on regex
        fg = parser.add_mutually_exclusive_group()
        fg.add_argument(
            "--filter-out",
            default=None,
            type=str,
            help="filter out rails names that match this regex",
        )
        fg.add_argument(
            "--filter",
            default=None,
            type=str,
            help="only measure rail names that match this regex",
        )
        adcg = parser.add_mutually_exclusive_group()
        # TODO(coconutruben): remove --ina-rate as legacy name once all dependencies
        # are removed, and people have had time to switch scripts/docs/workflows
        adcg.add_argument(
            "--ina-rate",
            default=measure_power.DEFAULT_ADC_RATE,
            dest="adc_rate",
            type=float,
            help="rate (sec) to query the "
            "ADCs, if <= 0 then ADCs will not be queried",
        )
        adcg.add_argument(
            "--adc-rate",
            default=measure_power.DEFAULT_ADC_RATE,
            dest="adc_rate",
            type=float,
            help="rate (sec) to query the "
            "ADCs, if <= 0 then ADCs will not be queried",
        )
        parser.add_argument(
            "--adc-accum-rate",
            default=measure_power.DEFAULT_ADC_ACCUM_RATE,
            type=float,
            help="rate (sec) to query the ADCs accumulators for avg "
            "power numbers (if applicable), if <= 0 then ADC "
            "accumulators will not be queried",
        )
        parser.add_argument(
            "--vbat-rate",
            default=measure_power.DEFAULT_VBAT_RATE,
            type=float,
            help="rate (sec) to query the ec vbat command, if <= 0 "
            "then ec vbat will not be queried",
        )
        # output and logging logic
        parser.add_argument(
            "--no-output",
            default=False,
            action="store_true",
            help="do not output anything into stdout",
        )
        parser.add_argument(
            "-o", "--outdir", default=None, help="directory to save data into"
        )
        parser.add_argument(
            "-m",
            "--message",
            default=None,
            help="message to append to each summary file stored",
        )
        self._add_mutually_exclusive_action("raw-data", parser, default=False)
        self._add_mutually_exclusive_action("summary", parser)
        self._add_mutually_exclusive_action("json", parser, default=False)
        # NOTE: if logging gets too verbose, turn default off
        self._add_mutually_exclusive_action("logs", parser)
        parser.add_argument(
            "--save-all",
            default=False,
            action="store_true",
            help="Equivalent to --save-summary --save-logs "
            "--save-raw-data. Overwrites any of those if specified.",
        )
        # Start the visualization server
        parser.add_argument(
            "--visualization",
            default=False,
            action="store_true",
            help="Visualization the power measurement results on a local server.",
        )
        # Specify the http server port for passing the information to html
        parser.add_argument(
            "--visualization-port",
            default=9998,
            type=int,
            help="A port number between 0 and 9998 which is used for"
            "the server to serve the visualized power measurement results."
            "Choose 0 to get a random port number.",
        )
        return parser

    def _parse_cmdline(self, parser, cmdline):
        """Parse the cmdline using a parser.

        Args:
          parser: a parser that can parse a cmdline sys.argv[1:]
          cmdline: a cmdline generated from sys.argv[1:]

        Returns:
          Args parsed by the parser from the cmdline
        """
        args = parser.parse_args(cmdline)
        # Save all logic
        if args.save_all:
            args.save_logs = True
            args.save_raw_data = True
            args.save_summary = True
            args.save_json = True
        return args

    def _setup_logging(self, args):
        """Set up logging of dut-power.

        Args:
          args: args parsed from the dut-power cmdline.
        """
        pm_logger = logging.getLogger("")
        pm_logger.setLevel(logging.INFO)
        pm_logger.handlers.clear()
        if not args.port:
            args.port = client.DEFAULT_PORT
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setLevel(logging.INFO)
        if args.debug:
            pm_logger.setLevel(logging.DEBUG)
            stdout_handler.setLevel(logging.DEBUG)
        if not args.no_output:
            pm_logger.addHandler(stdout_handler)
        if args.save_logs:
            # Default mode is 'w+b', but the messages passed are strings. Overwrite
            # default mode to be 'w+'
            tmplogfile = tempfile.NamedTemporaryFile(mode="w+")
            logfilehandler = logging.StreamHandler(tmplogfile)
            logfilehandler.setLevel(logging.DEBUG)
            pm_logger.addHandler(logfilehandler)
        if args.adc_accum_rate:
            # We can't set the accumulator time too long since we will lose the
            # samples. Ideally we'd send a shutdown event early and wait for each
            # driver to finish but the transactions take a very long time to
            # complete and dut-power has no knowledge of the drivers and limits.
            # As a work around, we'll artificially reduce the time.
            # Benchmarks with ServoMicro and a single PAC1954 show it requires
            # 10ms for each rail's accumulator due to Servod and the devices not
            # optimizing and batching transactions. The max read time should be
            # under 1 second but GPIO-I2C setups may take longer.
            max_adc_accum_rate = max(0, args.time - 2)
            args.adc_accum_rate = min(args.adc_accum_rate, max_adc_accum_rate)
        self.pm_logger = pm_logger
        self.tmplogfile = tmplogfile

    def _setup_visualization(self, args, pm):
        """Set up visualization.

        Args:
          args: args parsed from dut-power cmdline.
          pm: PowerMeasurement object that measures power and stores measurement data.
        """
        server_port = args.visualization_port
        self.power_data = dut_power_data.DataSampler(pm)
        self.http_server_handler = http_server.HttpRequestHandler(self.power_data)
        if self.http_server_handler.is_port_used(server_port):
            self.pm_logger.error(
                "port: %d is already in use. USE --visualization-port \
                      argument to change another port.",
                server_port,
            )
            sys.exit(1)

        file_path = self.http_server_handler.get_visualization_html_exist()

        # If the path does not exist, we would tell
        # the user how to build the visualization html
        if not file_path:
            self.pm_logger.error("The html file does not exist")
            self.pm_logger.error(
                "If the path above does not exist, "
                "please follow these steps to build the visualization html"
            )
            self.pm_logger.error(
                "cd ~/chromiumos/src/platform2/parallax/\n"
                "run: sudo emerge net-libs/nodejs\n"
                "run: npm install\n"
                "run: npm run build -- release\n"
            )
            sys.exit(1)

        try:
            self.visualization_server = http_server.ThreadedTCPServer(
                ("localhost", server_port), self.http_server_handler
            )
            if server_port == 0:
                _unused, server_port = self.visualization_server.server_address
        except Exception:
            self.pm_logger.error(
                "Failed to start http server. You may try to switch to"
                "another port by Use --visualization-port"
            )
            sys.exit(1)
        self.pm_logger.info("Try to use port: %d for visualization", server_port)
        self.pm_logger.info("Real-time visualization is available on: %s", file_path)
        self.pm_logger.info(
            "In the html page, switch the localhost number to %d "
            "and press toggle stream to start",
            server_port,
        )

        self.pm_logger.info("press ctrl-c to stop the visualization server.")

        visualization_server_thread = threading.Thread(
            target=self.visualization_server.serve_forever, daemon=True
        )
        visualization_server_thread.start()

    def _measure_power(self, args, pm):
        """Measure power.

        Args:
          args: args parsed from dut-power cmdline.
          pm: PowerMeasurement object that measures power and stores measurement data.
        """
        # pylint: disable=undefined-variable
        # Event.wait() is used as a preemptible way to sleep and control the
        # ProgressPrinters while handling the SIGTERM/SIGINT signals
        sleep_waiting = threading.Event()
        sleep_sampling = threading.Event()
        setup_done = pm.measure_power(wait=args.wait, powerstate=args.powerstate)

        def handler(unused_signum, _unused, pm=pm, sw=sleep_waiting, ss=sleep_sampling):
            sw.set()
            ss.set()
            pm.finish_measurement()
            if args.visualization:
                self.visualization_server.server_close()
                self.visualization_server.shutdown()

        # Ensure that SIGTERM and SIGNINT gracefully stop the measurement
        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)

        if args.visualization:
            # Start to prepare the data which will pass to the visualization UI
            threading.Thread(
                target=self.power_data.sample_generator, daemon=True
            ).start()
        # Wait until measurement is setup
        setup_done.wait()
        if not args.no_output:
            waiting_printer = ProgressPrinter(
                marker=ProgressPrinter.WAIT_MARKER,
                stop_signal=sleep_waiting,
                max_duration=args.wait,
            )
            # Start printing progress once power collection has started
            waiting_printer.start()
        # Sleep for the wait time and stop printing the wait symbol.
        sleep_waiting.wait(args.wait)
        sleep_waiting.set()
        if not args.no_output:
            sampling_printer = ProgressPrinter(
                stop_signal=sleep_sampling, max_duration=args.time
            )
            # Start printing progress once power collection has started
            sampling_printer.start()
        # Sleep for measurement time and wait time. Will wake on SIGINT & SIGTERM
        if args.visualization:
            sleep_sampling.wait()
        else:
            sleep_sampling.wait(args.time)
        # To ensure the ProgressPrinter also stops printing.
        sleep_sampling.set()

    def _save_results(self, args, pm):
        """Save power measurement results.

        Args:
          args: args parsed from dut-power cmdline.
          pm: PowerMeasurement object that measures power and stores measurement data.
        """
        if args.save_summary:
            pm.save_summary(args.outdir, args.message)
        if args.save_raw_data:
            pm.save_raw_data(args.outdir)
        if args.save_json:
            pm.save_summary_json(args.outdir)
        if args.save_logs:
            # pylint: disable=protected-access
            outdir = pm._outdir
            if args.outdir and os.path.isdir(args.outdir):
                outdir = args.outdir
            logfile = os.path.join(outdir, "logs.txt")
            self.pm_logger.info("Storing logs at:\n%s", logfile)
            shutil.move(self.tmplogfile.name, logfile)
        if args.visualization:
            self.http_server_handler.save_visualization_html(pm._outdir)

    # pylint: disable=dangerous-default-value
    def main(self, cmdline):
        """Main function for dut-power.

        Args:
          cmdline: dut-power cmdline.
        """
        parser = self._build_parser()
        # Add double-dashes in help message to unify docker and standalone versions
        parser.prog = parser.prog + " --"
        args = self._parse_cmdline(parser, cmdline)
        self._setup_logging(args)

        try:
            servo_client = client.ServoClient(host=args.host, port=args.port)
            pm = measure_power.PowerMeasurement(
                servo_client=servo_client,
                adc_rate=args.adc_rate,
                adc_accum_rate=args.adc_accum_rate,
                vbat_rate=args.vbat_rate,
                fast=args.fast,
                board=args.board,
                rgx_to_keep=args.filter,
                rgx_to_remove=args.filter_out,
            )
        except measure_power.NoSourceError as e:
            self.pm_logger.info(e)
            sys.exit(1)

        if args.visualization:
            self._setup_visualization(args, pm)

        self._measure_power(args, pm)

        # Indicate that measurement should stop, as process_measurement sets
        # stop_signal internally as well
        pm.process_measurement()
        pm.display_summary()
        self._save_results(args, pm)


def main(cmdline=sys.argv[1:]):
    if len(cmdline) > 0 and cmdline[0] == "--":
        cmdline = cmdline[1:]
    dut_power = DutPower()
    dut_power.main(cmdline)


if __name__ == "__main__":
    main(sys.argv[1:])
