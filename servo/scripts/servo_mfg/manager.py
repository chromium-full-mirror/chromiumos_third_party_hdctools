# Copyright 2021 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Base manager, handling common tasks across devices and defining interface."""

import logging
import traceback

from servo_mfg import color_mode as cm
from servo_mfg import device_util
from servo_mfg import reporter
from servo_mfg import user_input


class ManagerError(Exception):
    """Manager error class."""


class Manager:
    """Class to handle one manufacteuring round for one device type."""

    def __init__(self, outdir, validation=False):
        """Initialize the manufacturing."""
        self.reporter = reporter.Reporter(self.board, outdir=outdir)
        self._logger = logging.getLogger(type(self).__name__)
        self.validation = validation
        # Flag to indicate when to wrap up continious mode.
        self._finished = False
        # Start happy.
        self.exit_code = 0
        # Flag to indicate when the session was wrapped up.
        self._wrapped_up = False

    def abort(self, error_code=0):
        """Abort the current flashing."""
        if self._wrapped_up:
            # This indicates we have already aborted this service. Skip quietly.
            return False
        self._wrapped_up = True
        self.finish()
        # In this case however, we will exit as this is due to an error.
        self.reporter.finish()
        self._logger.info("Wrapping up with code %d.", error_code)
        self.exit_code = error_code
        return False

    @staticmethod
    def add_manager_args(parser):
        """Helper to add .check."""
        parser.add_argument(
            "--check",
            default=False,
            action="store_true",
            help="validate the environment and exit.",
        )

    def check_args(self, args):
        """Check the parsed arguments, perform modifications, or raise error."""
        # The default implementation just gives a thumbs up.

    def _req_arg_missing(self, args):
        """Helper to raise standard error when required args are missing."""
        self._logger.error(cm.red_bg("Required argument missing. Cannot continue"))
        self._logger.debug("Args provided: %s", str(args))
        return self.abort(1)

    def extract_single_device_data(self, args):
        """Extract the data to program a single device from |args|."""
        raise NotImplementedError(
            "Provide implementation for single_device args extraction."
        )

    def finish(self):
        """Wrap up the current process, and exit."""
        self._finished = True

    def single_device(self, args):
        """Code to flash and program one single device."""
        # Note: this follows a standard pattern that should apply to all devices.
        # Should a new device require a special flow, please consider incorporating
        # it into the general flow, though the work can initially be unblocked and
        # tested by simply overwriting this method in the device specific subclass.
        sargs = self.extract_single_device_data(args)
        if sargs is False:
            # Required arguments are missing. Abort.
            return self.abort(1)
        report = self.reporter.new_report(**sargs)
        dtester = None
        success = True
        try:
            if args.programming:
                report.add_section(title="Programming")
                # manufacture returns whether a device has failed or not.
                success = self.manufacturer.manufacture(report, **sargs)
                report.mark(success)
            if success and args.testing:
                if not args.serialno:
                    self._logger.info("Testing requires a serial number. Skipping.")
                else:
                    self._log_phase("Testing")
                    report.add_section(title="Testing Phase %d" % self.tester_cls.PHASE)
                    dtester = self.tester_cls(report=report, serialno=args.serialno)
                    # Testing returns true when all tests have passed.
                    success = dtester.run()
                    report.mark(success)
        except Exception as e:
            for line in traceback.format_exc().splitlines():
                self._logger.debug(line)
            self._logger.error("Failed: %s", str(e))
            # If the tester was created, we have to try and turn down servod.
            if dtester:
                dtester.stop_servod()
            success = False
            # Whatever section we were in, we know it has failed. Mark it accordingly.
            report.mark(success)
        # The report is finished outside, to allow for more sections in the future
        # to be added to the same report such as testing. The manufacturer cannot
        # know if the report is finished or not, while the manager does know.
        report.finish()
        return self._output_prompt(success)

    def wait_for_disconnect(self):
        """Implement in subclass to wait for all parts to disconnect."""
        raise NotImplementedError("Please provide disconnect detection code.")

    def _log_phase(self, phase):
        """Helper to log a standard line for a new phase.

        Args:
          phase: name of the phase
        """
        self._logger.info("")
        self._logger.info("------ Device %s ------", phase)

    def _output_prompt(self, success):
        """Helper to output the result of flashing and instruct the user.

        Args:
          success: bool, whether the device passed all phases

        Returns:
          whether the user successfully disconnected the device for script to
          proceed
        """
        self._log_phase("Outcome")
        core_message = (
            "Device {0}, please disconnect all connections, and "
            "place into the {0} devices bin."
        )
        if success:
            message = core_message.format("succeeded")
            message = cm.green_bg(message)
        else:
            message = core_message.format("failed")
            message = cm.red_bg(message)
        user_input.instruct_user(message)
        try:
            self.wait_for_disconnect()
            return True
        except device_util.DeviceUtilError as e:
            self._logger.debug(str(e))
            self._logger.debug("user timed out, turning down.")
            return False

    def continious_mode(self, args):
        """Go through multiple devices until the user cancels.

        Args:
          args: argparse Namespace object for the programming
        """
        while not self._finished:
            # The args here get modified in line.
            self._log_phase("Start")
            self.prompt_data(args)
            # The data prompt stage is a natural point where the user might
            # wrap up, and call Ctrl-C to finish. Check here again to make sure
            # the user has not decided to finish this session.
            if self._finished:
                break
            if not self.single_device(args):
                self._logger.info("Users seems to have stepped away. Turning down.")
                return self.abort(0)
            self._log_phase("Finished")
            if not user_input.instruct_user(
                "Continue with the next device?", enter_to_confirm=True
            ):
                self._logger.info("User indicated they are done. Thank you.")
                return self.abort(0)
            # 2 new lines to create a bit of seperation for the next device.
            self._logger.info("")
            self._logger.info("")

    def prompt_data(self, args):
        """Helper to request data in continous mode. Needs to be overwritten.

        Note: take a look at continious mode to see how this is used. The
        expectation is that this returns a dictionary of arguments to pass into
        the single_device implementation.

        Args:
          args: resulting Namespace from arg parsing
        """
        raise NotImplementedError(
            "Provide implementation to prompt user for "
            "data to program single device."
        )

    def check_env(self):
        """Check whether the environment allows for this manager to program."""
        env_ok = self.manufacturer.check_env()
        if env_ok:
            self._logger.info(cm.green_bg("Environment OK to run"))
        else:
            self._logger.info(cm.red_bg("Environment NOT OK to run"))
        self.exit_code = int(env_ok)
